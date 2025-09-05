#!/usr/bin/env python3
"""
Simple I2C LCD Display Manager - 16x2 displays only
Hardware is required - no mock support
"""
import time
import threading
from datetime import datetime

# Hardware constants
I2C_ADDRESS = 0x27
LCD_WIDTH = 16
LCD_HEIGHT = 2

class LCD:
    """Simple I2C LCD wrapper for 16x2 displays."""
    
    def __init__(self):
        try:
            from i2c_lcd import lcd
            self.lcd = lcd(I2C_ADDRESS)
            self.lock = threading.Lock()
            print("I2C LCD initialized")
        except Exception as e:
            print(f"FATAL: I2C LCD initialization failed: {e}")
            raise SystemExit("I2C LCD required - exiting")
    
    def clear(self):
        with self.lock:
            self.lcd.lcd_clear()
            time.sleep(0.05)
    
    def write(self, line1="", line2=""):
        """Write to both lines at once."""
        with self.lock:
            # Truncate and pad to 16 characters
            line1 = str(line1)[:16].ljust(16)
            line2 = str(line2)[:16].ljust(16)
            
            self.lcd.lcd_display_string(line1, 1)
            time.sleep(0.01)
            self.lcd.lcd_display_string(line2, 2)
            time.sleep(0.01)


class DisplayManager:
    """Manages LCD display with simple screen types."""
    
    def __init__(self):
        self.lcd = LCD()
        self.current_screen = "radio"
        self.screen_start = 0
        self.scroll_pos = 0
        self.last_song = ""
    
    def show_radio(self, channel_name="Radio", song="Loading...", is_playing=True):
        """Show main radio screen with scrolling song, or clock when off."""
        self.current_screen = "radio"
        
        if is_playing:
            # Line 1: Channel name (centered)
            line1 = str(channel_name)[:16].center(16)
            
            # Line 2: Song with scrolling if needed
            song = str(song)
            if len(song) <= 16:
                line2 = song.center(16)
            else:
                # Simple scrolling
                if song != self.last_song:
                    self.scroll_pos = 0
                    self.last_song = song
                
                if self.scroll_pos + 16 <= len(song):
                    line2 = song[self.scroll_pos:self.scroll_pos + 16]
                    self.scroll_pos += 1
                else:
                    self.scroll_pos = 0
                    line2 = song[:16]
        else:
            # Radio off - show time and date
            now = datetime.now()
            line1 = now.strftime('%H:%M:%S').center(16)  # 24-hour time
            line2 = now.strftime('%m/%d/%Y').center(16)  # MM/DD/YYYY date
        
        self.lcd.write(line1, line2)
    
    def show_volume(self, volume):
        """Show volume screen temporarily."""
        self.current_screen = "volume"
        self.screen_start = time.time()
        self.lcd.write("Volume", str(volume).center(16))
    
    def show_channel(self, channel_name):
        """Show channel change screen temporarily."""
        self.current_screen = "channel"
        self.screen_start = time.time()
        self.lcd.write("Channel", str(channel_name)[:16].center(16))
    
    def show_error(self, error):
        """Show error screen."""
        self.current_screen = "error"
        self.screen_start = time.time()
        self.lcd.write("Error:", str(error)[:16].center(16))
    
    def show_goodbye(self):
        """Show goodbye message."""
        self.lcd.write("Goodbye!", "")
    
    def is_temp_screen_expired(self):
        """Check if temporary screen should revert to main."""
        if self.current_screen in ["volume", "channel", "error"]:
            return time.time() - self.screen_start > 2.0
        return False
    
    def clear(self):
        self.lcd.clear()
