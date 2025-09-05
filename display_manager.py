"""
I2C LCD Display Manager for Plex Radio Player

This library provides a simplified display system that ONLY supports 16x2 I2C LCD displays.
The application will fail to start if no I2C LCD display is detected.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any


class I2CLCDDisplay:
    """16x2 I2C LCD Display Driver - fails if hardware not available."""
    
    def __init__(self):
        """Initialize I2C LCD display. Raises exception if hardware not available."""
        try:
            from i2c_lcd import lcd
            self.lcd = lcd()
        except ImportError:
            raise ImportError("i2c_lcd module not found. Please install the required LCD library.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize I2C LCD display: {e}")
        
        # Fixed dimensions for 16x2 display
        self.width = 16
        self.height = 2
        
        # Thread lock for display operations
        self._display_lock = threading.Lock()
        
        # Track current display state
        self._current_lines = ["", ""]
        
        # Timing control for LCD operations
        self._last_operation_time = 0
        self._min_delay_between_operations = 0.015  # 15ms minimum delay
        
        print("I2C LCD initialized: 16x2")
    
    def _safe_delay(self):
        """Ensure minimum delay between LCD operations to prevent corruption."""
        current_time = time.time()
        time_since_last = current_time - self._last_operation_time
        if time_since_last < self._min_delay_between_operations:
            time.sleep(self._min_delay_between_operations - time_since_last)
        self._last_operation_time = time.time()
    
    def _sanitize_text(self, text: str) -> str:
        """Clean text for LCD display - remove problematic characters."""
        if text is None:
            return ""
        
        text = str(text)
        if not text:
            return ""
        
        # Replace control characters with spaces
        for char in '\x00\t\n\r\f\v\b':
            text = text.replace(char, ' ')
        
        # Keep only printable ASCII characters
        sanitized = ''.join(char if 32 <= ord(char) <= 126 else ' ' for char in text)
        
        return sanitized
    
    def clear(self):
        """Clear the LCD display."""
        with self._display_lock:
            try:
                self._safe_delay()
                self.lcd.lcd_clear()
                self._safe_delay()
                self._current_lines = ["", ""]
                time.sleep(0.05)  # Extra delay after clear
            except Exception as e:
                raise RuntimeError(f"LCD clear failed: {e}")
    
    def display_text(self, text: str, line: int):
        """Display text on specified line (1 or 2)."""
        if line not in [1, 2]:
            raise ValueError(f"Invalid line number: {line}. Must be 1 or 2.")
        
        with self._display_lock:
            try:
                # Clean and format text
                clean_text = self._sanitize_text(text)
                clean_text = clean_text[:self.width]  # Truncate
                clean_text = clean_text.ljust(self.width)  # Pad to full width
                
                # Only update if text has changed
                line_index = line - 1
                if self._current_lines[line_index] == clean_text:
                    return
                
                self._safe_delay()
                self.lcd.lcd_display_string(clean_text, line)
                self._safe_delay()
                
                self._current_lines[line_index] = clean_text
                
            except Exception as e:
                raise RuntimeError(f"LCD display failed on line {line}: {e}")
    
    def get_dimensions(self) -> tuple:
        """Return (width, height) of the display."""
        return (self.width, self.height)


class DisplayScreen:
    """Base class for different display screens."""
    
    def __init__(self, name: str):
        self.name = name
    
    def render(self, display: I2CLCDDisplay, context: Dict[str, Any]) -> bool:
        """
        Render the screen with the given context.
        Returns True if the screen should continue to be displayed.
        """
        raise NotImplementedError("Subclasses must implement render method")


class RadioScreen(DisplayScreen):
    """Main radio display showing channel and current song."""
    
    def __init__(self):
        super().__init__("radio")
        # Marquee scrolling state
        self.scroll_offset = 0
        self.last_song = ""
        self.scroll_timer = time.time()
        self.scroll_phase = 'initial_delay'  # initial_delay -> scrolling -> final_delay
        
        # Timing settings
        self.scroll_speed = 0.3  # seconds between scroll steps
        self.initial_delay = 2.0  # seconds to show beginning before scrolling
        self.final_delay = 2.0    # seconds to show end before reset
    
    def render(self, display: I2CLCDDisplay, context: Dict[str, Any]) -> bool:
        is_playing = context.get('is_playing', False)
        
        if is_playing:
            # Line 1: Channel name
            channel_name = context.get('channel_name', 'Radio')
            line1 = str(channel_name)[:16].center(16)
            
            # Line 2: Current song with marquee
            current_song = context.get('current_song', 'Loading...')
            line2 = self._handle_marquee(current_song)
        else:
            # Radio off - show clock and "Radio Off"
            line1 = datetime.now().strftime('%H:%M:%S').center(16)
            line2 = "Radio Off".center(16)
        
        # Update display
        display.display_text(line1, 1)
        display.display_text(line2, 2)
        
        return True  # Continue displaying
    
    def _handle_marquee(self, text: str) -> str:
        """Handle marquee scrolling for long text."""
        text = str(text)
        current_time = time.time()
        
        # Reset if song changed
        if text != self.last_song:
            self.scroll_offset = 0
            self.scroll_timer = current_time
            self.scroll_phase = 'initial_delay'
            self.last_song = text
        
        # If text fits, center it
        if len(text) <= 16:
            return text.center(16)
        
        # Marquee scrolling logic
        if self.scroll_phase == 'initial_delay':
            display_text = text[:16]
            if (current_time - self.scroll_timer) >= self.initial_delay:
                self.scroll_phase = 'scrolling'
                self.scroll_timer = current_time
        
        elif self.scroll_phase == 'scrolling':
            if (current_time - self.scroll_timer) >= self.scroll_speed:
                self.scroll_offset += 1
                self.scroll_timer = current_time
            
            max_offset = len(text) - 16
            if self.scroll_offset >= max_offset:
                self.scroll_phase = 'final_delay'
                self.scroll_timer = current_time
                self.scroll_offset = max_offset
            
            display_text = text[self.scroll_offset:self.scroll_offset + 16]
        
        elif self.scroll_phase == 'final_delay':
            display_text = text[-16:]
            if (current_time - self.scroll_timer) >= self.final_delay:
                self.scroll_phase = 'initial_delay'
                self.scroll_timer = current_time
                self.scroll_offset = 0
        
        return display_text


class VolumeScreen(DisplayScreen):
    """Volume display screen."""
    
    def __init__(self, duration: float = 2.0):
        super().__init__("volume")
        self.duration = duration
        self.start_time = None
    
    def render(self, display: I2CLCDDisplay, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        line1 = "Volume".center(16)
        volume = context.get('volume_text', 'N/A')
        line2 = str(volume).center(16)
        
        display.display_text(line1, 1)
        display.display_text(line2, 2)
        
        return (time.time() - self.start_time) < self.duration


class ChannelScreen(DisplayScreen):
    """Channel change display screen."""
    
    def __init__(self, duration: float = 2.0):
        super().__init__("channel")
        self.duration = duration
        self.start_time = None
    
    def render(self, display: I2CLCDDisplay, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        line1 = "Channel".center(16)
        channel = context.get('channel_text', 'Unknown')
        line2 = str(channel)[:16].center(16)
        
        display.display_text(line1, 1)
        display.display_text(line2, 2)
        
        return (time.time() - self.start_time) < self.duration


class ErrorScreen(DisplayScreen):
    """Error message display screen."""
    
    def __init__(self, error_message: str, duration: float = 3.0, persistent: bool = False):
        super().__init__("error")
        self.error_message = error_message
        self.duration = duration
        self.persistent = persistent
        self.start_time = None
    
    def render(self, display: I2CLCDDisplay, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        line1 = "Error:".center(16)
        line2 = str(self.error_message)[:16].center(16)
        
        display.display_text(line1, 1)
        display.display_text(line2, 2)
        
        # If persistent, stay on screen indefinitely
        if self.persistent:
            return True
        
        return (time.time() - self.start_time) < self.duration


class GoodbyeScreen(DisplayScreen):
    """Goodbye message display screen."""
    
    def __init__(self, duration: float = 2.0):
        super().__init__("goodbye")
        self.duration = duration
        self.start_time = None
    
    def render(self, display: I2CLCDDisplay, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        line1 = "Goodbye!".center(16)
        line2 = "".center(16)  # Empty second line
        
        display.display_text(line1, 1)
        display.display_text(line2, 2)
        
        return (time.time() - self.start_time) < self.duration


class DisplayManager:
    """Manages the I2C LCD display and screen transitions."""
    
    def __init__(self):
        """Initialize display manager. Fails if I2C LCD not available."""
        self.display = I2CLCDDisplay()
        self.current_screen = None
        self.default_screen = RadioScreen()
        self.context = {}
        
        # Thread safety
        self._update_lock = threading.Lock()
        
        print("Display Manager initialized with I2C LCD")
    
    def show_screen(self, screen: DisplayScreen, clear_first: bool = True):
        """Show a specific screen."""
        with self._update_lock:
            if clear_first:
                self.display.clear()
                time.sleep(0.05)  # Delay after clear
            
            self.current_screen = screen
            
            # Reset screen state
            if hasattr(screen, 'start_time'):
                screen.start_time = None
    
    def update_context(self, **kwargs):
        """Update display context."""
        with self._update_lock:
            self.context.update(kwargs)
    
    def update_display(self):
        """Update the display with current context."""
        with self._update_lock:
            try:
                screen = self.current_screen if self.current_screen else self.default_screen
                continue_display = screen.render(self.display, self.context)
                
                # Return to default screen if current screen is done
                if self.current_screen and not continue_display:
                    self.current_screen = None
                    self.display.clear()
                    time.sleep(0.05)
                    
            except Exception as e:
                print(f"Display update error: {e}")
                # Try to recover
                try:
                    self.display.clear()
                    time.sleep(0.1)
                except:
                    pass
    
    def clear_display(self):
        """Clear the display."""
        with self._update_lock:
            self.display.clear()
            self.current_screen = None


def create_display_manager() -> DisplayManager:
    """Create display manager with I2C LCD. Fails if hardware not available."""
    return DisplayManager()


# Legacy compatibility - remove mock support
def create_i2c_display_manager() -> DisplayManager:
    """Create I2C display manager. Fails if hardware not available."""
    return create_display_manager()
