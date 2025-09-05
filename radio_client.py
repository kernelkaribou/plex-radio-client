#!/usr/bin/env python3

"""
Plex Radio Client - A radio client for interacting with a Plex Media Server
Supports physical buttons via GPIO, I2C LCD display, and audio streaming
"""

import os
import time
import json
import signal
import sys
import subprocess
import threading
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List

# Third-party imports
import requests
from signal import pause

# Local imports
from display_manager import (
    DisplayManager, I2CLCDDisplay, RadioScreen, 
    VolumeScreen, ChannelScreen, ErrorScreen, GoodbyeScreen, create_display_manager
)
from config_manager import config

# Hardcoded constants (not customizable via config)
DEFAULT_STARTUP_VOLUME = 15  # Safe startup volume
GPIO_BOUNCE_TIME = 0.01      # Button debounce time in seconds
PERSISTENCE_FILE = 'last_channel.txt'  # Channel persistence file
LCD_I2C_ADDRESS = 0x27       # I2C address for LCD display
LCD_WIDTH = 16               # Display width in characters
LCD_HEIGHT = 2               # Display height in lines

# Simple logging control
QUIET_MODE = config.get('logging.quiet_mode', True)

def log_info(message):
    """Always show important messages"""
    print(f"[INFO] {message}")

def log_debug(message):
    """Only show debug messages if not in quiet mode"""
    if not QUIET_MODE:
        print(f"[DEBUG] {message}")

def log_state(message):
    """Always show state changes"""
    print(f"{message}")

# Initialize GPIO buttons only if hardware is available
radio_power_btn = None
volume_down_btn = None
volume_up_btn = None
channel_down_btn = None
channel_up_btn = None

def init_gpio_buttons():
    """Initialize GPIO buttons if hardware is available."""
    global radio_power_btn, volume_down_btn, volume_up_btn, channel_down_btn, channel_up_btn
    
    # Check if we should initialize hardware
    hardware_enabled = config.is_enabled('hardware.enabled')
    
    if not hardware_enabled:
        print("Hardware mode disabled in configuration")
        return False
    
    try:
        from gpiozero import Button
        
        # Get GPIO pin configuration from config
        gpio_config = config.get_section('gpio')
        
        # Define each button and the GPIO pin it's connected to (using hardcoded bounce time)
        radio_power_btn = Button(gpio_config.get('power_pin', 25), bounce_time=GPIO_BOUNCE_TIME)
        volume_down_btn = Button(gpio_config.get('volume_down_pin', 24), bounce_time=GPIO_BOUNCE_TIME)
        volume_up_btn = Button(gpio_config.get('volume_up_pin', 23), bounce_time=GPIO_BOUNCE_TIME)
        channel_down_btn = Button(gpio_config.get('channel_down_pin', 15), bounce_time=GPIO_BOUNCE_TIME)
        channel_up_btn = Button(gpio_config.get('channel_up_pin', 14), bounce_time=GPIO_BOUNCE_TIME)
        
        print("GPIO buttons initialized successfully")
        log_info("GPIO buttons initialized successfully")
        return True
        
    except Exception as e:
        print(f"GPIO initialization failed: {e}")
        print("Running without physical button support")
        return False


class PlexRadioClient:
    """Core radio client handling playback, channels, and API communication."""
    
    def __init__(self, api_base_url=None, display_manager=None):
        # Get API URL from config if not provided
        if api_base_url is None:
            api_base_url = config.get('api.base_url', 'http://localhost:5000')
        
        self.api_base_url = api_base_url
        self.current_process = None
        
        # Use hardcoded persistence file path
        self.persistence_file = PERSISTENCE_FILE
        
        # Initialize display manager
        if display_manager is None:
            self.display = create_display_manager()
        else:
            self.display = display_manager
        
        # State tracking
        self.is_playing = False
        self.last_song_title = None
        self.channel_has_changed = False
        self.shutdown_requested = False  # Flag to stop background threads
        
        # Channel data
        self.channels = []
        self.current_channel = 0
        self._load_last_channel()
    
    # --- Persistence methods ---
    def _load_last_channel(self):
        """Loads the last used channel index from a local file."""
        try:
            with open(self.persistence_file, 'r') as f:
                channel = int(f.read().strip())
                self.current_channel = channel
                print(f"Loaded last used channel: {self.current_channel}")
                log_debug(f"Loaded last used channel: {self.current_channel}")
        except (FileNotFoundError, ValueError):
            print("Last channel file not found or invalid. Defaulting to channel 0.")
            self.current_channel = 0
    
    def _save_last_channel(self):
        """Saves the current channel index to a local file."""
        try:
            with open(self.persistence_file, 'w') as f:
                f.write(str(self.current_channel))
        except IOError as e:
            print(f"Error saving last channel: {e}")
    
    # --- Helper methods for playback ---
    def check_ffplay_available(self):
        """Checks if ffplay executable is in the system's PATH."""
        return shutil.which('ffplay') is not None
    
    def stop_current_playback(self):
        """Terminates the currently running ffplay process."""
        if self.current_process:
            print("Stopping current playback...")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.current_process = None
    
    # --- API methods ---
    def get_channels(self):
        """Get a list of available radio channels from the API."""
        try:
            url = f"{self.api_base_url}/channels"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            print(f"Loaded {len(data.get('data', []))} channels.")
            log_info(f"Loaded {len(data.get('data', []))} channels from API")
            return data.get("data") if data.get("status") == "success" else []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching channels: {e}")
            # Return None to indicate connection failure (different from empty list)
            return None
    
    def get_current_song(self, channel_index=0):
        """Get current song information for a specific channel."""
        try:
            url = f"{self.api_base_url}/current-song/{channel_index}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("data") if data.get("status") == "success" else None
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Error fetching song data: {e}")
            return None
    
    # --- Core playback function ---
    def play_song(self, song_info):
        """Play a song using a non-blocking ffplay subprocess."""
        if not song_info or not song_info.get("media_link"):
            print("No song or media link provided.")
            return False
        
        self.stop_current_playback()
        media_url = song_info["media_link"]
        cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', media_url]
        
        if song_info.get("start_time"):
            cmd.extend(['-ss', str(song_info["start_time"])])
        
        print(f"Playing: {song_info.get('title')} by {song_info.get('artist')}")
        log_state(f"Now Playing: {song_info.get('title')} by {song_info.get('artist')}")
        self.current_process = subprocess.Popen(cmd)
        return True
    
    # --- Main control functions ---
    def toggle_power(self):
        """Toggles radio playback on or off."""
        if self.is_playing:
            # --- TURNING RADIO OFF ---
            print("Powering OFF radio...")
            log_state("Radio turned OFF")
            self.is_playing = False
            self.stop_current_playback()
            self.last_song_title = None
            self.display.clear_display()
        else:
            # --- TURNING RADIO ON ---
            print("Powering ON radio...")
            log_state("Radio turned ON")
            
            # Set volume to safe startup level (hardcoded)
            print(f"Setting volume to {DEFAULT_STARTUP_VOLUME}% for safe startup...")
            set_volume(DEFAULT_STARTUP_VOLUME)
            
            # Clear any persistent error screens first
            self.display.clear_display()
            
            if not self.channels:
                channels_result = self.get_channels()
                
                # Check if it's a connection failure (None) vs empty list ([])
                if channels_result is None:
                    print("Cannot start: Server connection failed.")
                    error_screen = ErrorScreen("Server Not Found")
                    self.display.show_screen(error_screen)
                    return
                elif not channels_result:
                    print("Cannot start: No channels available.")
                    error_screen = ErrorScreen("No Channels")
                    self.display.show_screen(error_screen)
                    return
                else:
                    self.channels = channels_result
            
            self.is_playing = True
            self.channel_has_changed = True  # Signal playback thread to start playing
            self.display.clear_display()
    
    def change_channel(self, direction):
        """Changes channel, stops current audio, saves it, and signals playback to update."""
        if not self.is_playing or not self.channels:
            return
        
        # Stop current audio immediately when changing channels
        self.stop_current_playback()
        self.last_song_title = None
        
        num_channels = len(self.channels)
        self.current_channel = (self.current_channel + direction) % num_channels
        self._save_last_channel()  # Save the new channel immediately
        self.channel_has_changed = True
        
        channel_name = self.channels[self.current_channel].get('name', f"Channel {self.current_channel}")
        print(f"Switched to channel: {channel_name}")
        log_state(f"Switched to channel: {channel_name}")
        
        # Show channel change screen
        channel_screen = ChannelScreen()
        self.display.show_screen(channel_screen)
        self.display.update_context(channel_text=channel_name)
    
    def get_current_channel_name(self):
        """Get the name of the current channel."""
        if self.channels and 0 <= self.current_channel < len(self.channels):
            return self.channels[self.current_channel].get('name', 'Radio')
        return 'Radio'


def get_current_volume():
    """Gets the current system volume using pactl."""
    try:
        # Get default sink name
        info_result = subprocess.run(['pactl', 'info'], capture_output=True, text=True)
        default_sink_name = [line.split(':')[1].strip() for line in info_result.stdout.splitlines() if "Default Sink:" in line][0]
        
        # Get volume from the default sink
        sinks_result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
        for sink_info in sinks_result.stdout.split('Sink #'):
            if default_sink_name in sink_info:
                for line in sink_info.splitlines():
                    if 'Volume:' in line:
                        # Extract percentage from a line like "Volume: front-left: 65536 / 100% / 0.00 dB"
                        return line.split('/')[1].strip()
    except Exception as e:
        print(f"Error getting volume: {e}")
    return "N/A"


def set_volume(volume_percent):
    """Sets the system volume to a specific percentage."""
    subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f"{volume_percent}%"], 
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def adjust_volume(direction, radio_client):
    """Adjusts the system volume by 5% up or down."""
    # # Prevent volume changes when radio is off
    # if not radio_client.is_playing:
    #     print("Volume adjustment ignored - radio is off")
    #     return
    
    subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f"{'+' if direction > 0 else '-'}5%"], 
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Log volume change
    volume_change = "Volume UP" if direction > 0 else "Volume DOWN"
    log_state(f"{volume_change} - Current: {get_current_volume()}")
    
    # Show volume screen
    volume_screen = VolumeScreen()
    radio_client.display.show_screen(volume_screen)
    radio_client.display.update_context(volume_text=get_current_volume())


# --- Background Threads ---
def manage_display(radio_client):
    """Manages the LCD display updates with enhanced stability."""
    while not radio_client.shutdown_requested:
        try:
            # Update display context with current radio state
            radio_client.display.update_context(
                is_playing=radio_client.is_playing,
                channel_name=radio_client.get_current_channel_name(),
                current_song=radio_client.last_song_title or "Loading..."
            )
            
            # Update the display
            radio_client.display.update_display()
            
        except Exception as e:
            print(f"Display management error: {e}")
            # Continue operation even if display has issues
            time.sleep(1)
        
        # Reduced update frequency to prevent LCD corruption
        time.sleep(0.1)  # Changed from 0.05 to 0.1 seconds


def manage_playback(radio_client):
    """Manages the continuous playback of songs from the current channel."""
    while not radio_client.shutdown_requested:
        if radio_client.is_playing:
            # Check if the current song has finished playing (ffplay process exited)
            if radio_client.current_process and radio_client.current_process.poll() is not None:
                print("Song finished playing.")
                radio_client.last_song_title = None  # Force a refresh to get the next song
            
            # Get current song information from the API
            song_info = radio_client.get_current_song(radio_client.current_channel)
            
            if song_info:
                # Format: artist - title
                current_title = f"{song_info.get('artist')} - {song_info.get('title')}"
                # If the song has changed or the channel was just changed, play the new song
                if current_title != radio_client.last_song_title or radio_client.channel_has_changed:
                    radio_client.play_song(song_info)
                    radio_client.last_song_title = current_title
                    radio_client.channel_has_changed = False  # Reset the flag
            time.sleep(10)  # Poll for new song every 10 seconds
        else:
            time.sleep(1)  # When not playing, check less frequently


# --- Main Execution ---
if __name__ == "__main__":
    plex_radio = None
    try:
        print("Radio starting... Press Ctrl+C to exit.")
        
        # Initialize GPIO buttons if hardware is available
        gpio_available = init_gpio_buttons()
        
        # Initialize the radio client (API URL will be read from config)
        plex_radio = PlexRadioClient()
        
        # Check for ffplay dependency
        if not plex_radio.check_ffplay_available():
            print("FATAL: ffplay not found. Please install ffmpeg.")
            error_screen = ErrorScreen("ffplay missing", persistent=True)
            plex_radio.display.show_screen(error_screen)
            time.sleep(5)  # Show error for 5 seconds before exiting
            exit()
        
        # Assign button actions only if GPIO is available
        if gpio_available and all([radio_power_btn, volume_down_btn, volume_up_btn, channel_down_btn, channel_up_btn]):
            radio_power_btn.when_pressed = plex_radio.toggle_power
            volume_down_btn.when_pressed = lambda: adjust_volume(-1, plex_radio)
            volume_up_btn.when_pressed = lambda: adjust_volume(1, plex_radio)
            channel_down_btn.when_pressed = lambda: plex_radio.change_channel(-1)
            channel_up_btn.when_pressed = lambda: plex_radio.change_channel(1)
            print("Button handlers assigned")
        else:
            print("Running without button support - use API or keyboard controls")
        
        # Start background threads for display and playback management
        display_thread = threading.Thread(target=manage_display, args=(plex_radio,), daemon=True)
        playback_thread = threading.Thread(target=manage_playback, args=(plex_radio,), daemon=True)
        display_thread.start()
        playback_thread.start()
        
        # Keep the main thread alive
        if gpio_available:
            # Wait for button presses or KeyboardInterrupt
            pause()
        else:
            # Without GPIO, just wait for KeyboardInterrupt
            print("No GPIO buttons available. Use Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        
    except KeyboardInterrupt:
        print("\nExiting script.")
    
    finally:
        if plex_radio:
            # Signal background threads to stop
            print("Stopping background threads...")
            plex_radio.shutdown_requested = True
            
            # Give threads a moment to stop
            time.sleep(0.5)
            
            plex_radio.stop_current_playback()
            
            # Show goodbye message using the display manager
            goodbye_screen = GoodbyeScreen(duration=1.5)
            plex_radio.display.show_screen(goodbye_screen)
            
            # Keep updating display to show goodbye message
            start_time = time.time()
            while time.time() - start_time < 1.5:
                plex_radio.display.update_display()
                time.sleep(0.05)
            
            # Now clear the display - threads are stopped so nothing will overwrite it
            print("Clearing display...")
            plex_radio.display.clear_display()
            time.sleep(0.2)
        
        print("Shutdown complete.")