#!/usr/bin/env python3
"""
Simplified Plex Radio Client
Hardware I2C LCD 16x2 required - no fallbacks
Minimal dependencies and logging
"""
import os
import time
import json
import subprocess
import threading
import yaml
from signal import pause

import requests
from gpiozero import Button
from display_manager import DisplayManager

# Constants
DEFAULT_VOLUME = 15
GPIO_BOUNCE = 0.01
PERSISTENCE_FILE = 'last_channel.txt'

def load_config():
    """Load simple configuration."""
    try:
        with open('radio_server_config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Config error: {e}")
        return {
            'api': {'base_url': 'http://localhost:5000'},
            'gpio': {'power_pin': 25, 'volume_up_pin': 23, 'volume_down_pin': 24, 
                    'channel_up_pin': 14, 'channel_down_pin': 15}
        }

def get_volume():
    """Get current system volume."""
    try:
        result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Extract percentage from output like "Volume: front-left: 32768 /  50% /"
            for part in result.stdout.split():
                if part.endswith('%'):
                    return part
    except:
        pass
    return "N/A"

def set_volume(percent):
    """Set system volume."""
    subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f"{percent}%"], 
                   capture_output=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def adjust_volume(direction):
    """Adjust volume by 5% up or down."""
    change = "+5%" if direction > 0 else "-5%"
    subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', change], 
                   capture_output=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class RadioClient:
    """Simple radio client."""
    
    def __init__(self, config):
        self.api_url = config['api']['base_url']
        self.display = DisplayManager()
        self.current_process = None
        self.is_playing = False
        self.channels = []
        self.current_channel = 0
        self.last_song = None
        self.shutdown = False
        
        self.load_last_channel()
        
        # Initialize GPIO buttons
        gpio = config['gpio']
        self.power_btn = Button(gpio['power_pin'], bounce_time=GPIO_BOUNCE)
        self.vol_up_btn = Button(gpio['volume_up_pin'], bounce_time=GPIO_BOUNCE)
        self.vol_down_btn = Button(gpio['volume_down_pin'], bounce_time=GPIO_BOUNCE)
        self.ch_up_btn = Button(gpio['channel_up_pin'], bounce_time=GPIO_BOUNCE)
        self.ch_down_btn = Button(gpio['channel_down_pin'], bounce_time=GPIO_BOUNCE)
        
        # Assign button handlers
        self.power_btn.when_pressed = self.toggle_power
        self.vol_up_btn.when_pressed = lambda: self.volume_button(1)
        self.vol_down_btn.when_pressed = lambda: self.volume_button(-1)
        self.ch_up_btn.when_pressed = lambda: self.change_channel(1)
        self.ch_down_btn.when_pressed = lambda: self.change_channel(-1)
        
        print("Radio client initialized")
    
    def load_last_channel(self):
        """Load last used channel."""
        try:
            with open(PERSISTENCE_FILE, 'r') as f:
                self.current_channel = int(f.read().strip())
        except:
            self.current_channel = 0
    
    def save_last_channel(self):
        """Save current channel."""
        try:
            with open(PERSISTENCE_FILE, 'w') as f:
                f.write(str(self.current_channel))
        except:
            pass
    
    def get_channels(self):
        """Get channels from API."""
        try:
            response = requests.get(f"{self.api_url}/channels", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("data", []) if data.get("status") == "success" else []
        except Exception as e:
            print(f"API error: {e}")
            return None
    
    def get_current_song(self):
        """Get current song for active channel."""
        try:
            response = requests.get(f"{self.api_url}/current-song/{self.current_channel}", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("data") if data.get("status") == "success" else None
        except:
            return None
    
    def stop_playback(self):
        """Stop current audio."""
        if self.current_process:
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=2)
            except:
                self.current_process.kill()
            self.current_process = None
    
    def play_song(self, song_info):
        """Play a song with ffplay."""
        if not song_info or not song_info.get("media_link"):
            return False
        
        self.stop_playback()
        
        cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', song_info["media_link"]]
        if song_info.get("start_time"):
            cmd.extend(['-ss', str(song_info["start_time"])])
        
        try:
            self.current_process = subprocess.Popen(cmd)
            return True
        except:
            return False
    
    def toggle_power(self):
        """Toggle radio on/off."""
        if self.is_playing:
            print("Radio OFF")
            self.is_playing = False
            self.stop_playback()
            self.last_song = None
            # Show clock immediately when turning off
            self.display.show_radio("", "", False)
        else:
            print("Radio ON")
            set_volume(DEFAULT_VOLUME)
            
            if not self.channels:
                channels = self.get_channels()
                if channels is None:
                    self.display.show_error("Server Error")
                    return
                elif not channels:
                    self.display.show_error("No Channels")
                    return
                else:
                    self.channels = channels
            
            self.is_playing = True
    
    def change_channel(self, direction):
        """Change channel."""
        if not self.is_playing or not self.channels:
            return
        
        self.stop_playback()
        self.last_song = None
        
        self.current_channel = (self.current_channel + direction) % len(self.channels)
        self.save_last_channel()
        
        channel_name = self.channels[self.current_channel].get('name', f"Ch {self.current_channel}")
        print(f"Channel: {channel_name}")
        self.display.show_channel(channel_name)
    
    def volume_button(self, direction):
        """Handle volume button press."""
        adjust_volume(direction)
        volume = get_volume()
        print(f"Volume: {volume}")
        self.display.show_volume(volume)
    
    def get_channel_name(self):
        """Get current channel name."""
        if self.channels and 0 <= self.current_channel < len(self.channels):
            return self.channels[self.current_channel].get('name', 'Radio')
        return 'Radio'
    
    def display_loop(self):
        """Display update loop."""
        while not self.shutdown:
            try:
                if self.display.is_temp_screen_expired():
                    # Return to main radio screen (or clock when off)
                    self.display.show_radio(
                        self.get_channel_name(),
                        self.last_song or "Loading...",
                        self.is_playing
                    )
                
                # Update main screen (radio or clock)
                elif self.display.current_screen == "radio":
                    self.display.show_radio(
                        self.get_channel_name(),
                        self.last_song or "Loading...",
                        self.is_playing
                    )
                
                # Update every 500ms for scrolling text, or every second for clock
                sleep_time = 0.5 if self.is_playing else 1.0
                time.sleep(sleep_time)
            except:
                time.sleep(1)
    
    def playback_loop(self):
        """Playback management loop."""
        while not self.shutdown:
            if self.is_playing:
                # Check if current song finished
                if self.current_process and self.current_process.poll() is not None:
                    self.last_song = None
                
                # Get and play current song
                song_info = self.get_current_song()
                if song_info:
                    current_song = f"{song_info.get('artist', 'Unknown')} - {song_info.get('title', 'Unknown')}"
                    if current_song != self.last_song:
                        if self.play_song(song_info):
                            self.last_song = current_song
                            print(f"Playing: {current_song}")
                
                time.sleep(10)  # Check every 10 seconds
            else:
                time.sleep(1)

def main():
    config = load_config()
    radio = RadioClient(config)
    
    # Check ffplay
    if not subprocess.run(['which', 'ffplay'], capture_output=True).returncode == 0:
        print("FATAL: ffplay not found")
        radio.display.show_error("ffplay missing")
        time.sleep(3)
        return
    
    try:
        # Start background threads
        display_thread = threading.Thread(target=radio.display_loop, daemon=True)
        playback_thread = threading.Thread(target=radio.playback_loop, daemon=True)
        
        display_thread.start()
        playback_thread.start()
        
        # Show initial clock display since radio starts in off state
        radio.display.show_radio("", "", False)
        
        print("Radio started - Press Ctrl+C to exit")
        pause()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        radio.shutdown = True
        radio.stop_playback()
        radio.display.show_goodbye()
        time.sleep(1)
        radio.display.clear()
        print("Goodbye!")

if __name__ == "__main__":
    main()
