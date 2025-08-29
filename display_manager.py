"""
Display Manager Library for Plex Radio Player

This library provides a configurable display system that can work with different
types of displays (LCD, OLED, etc.) and different screen configurations.
"""

import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, Callable


class DisplayDriver(ABC):
    """Abstract base class for display drivers."""
    
    @abstractmethod
    def clear(self):
        """Clear the display."""
        pass
    
    @abstractmethod
    def display_text(self, text: str, line: int):
        """Display text on a specific line."""
        pass
    
    @abstractmethod
    def get_dimensions(self) -> tuple:
        """Return (width, height) of the display."""
        pass


class I2CLCDDriver(DisplayDriver):
    """Driver for I2C LCD displays with enhanced stability and error handling."""
    
    def __init__(self):
        try:
            from i2c_lcd import lcd
            self.lcd = lcd()
            self.width = 16
            self.height = 2
            # Add thread lock for display operations
            self._display_lock = threading.Lock()
            # Track display state to prevent corruption
            self._current_lines = [""] * self.height
            # Add timing control
            self._last_operation_time = 0
            self._min_delay_between_operations = 0.01  # 10ms minimum delay
        except ImportError:
            raise ImportError("i2c_lcd module not found. Please install the required LCD library.")
    
    def _safe_delay(self):
        """Ensure minimum delay between LCD operations."""
        current_time = time.time()
        time_since_last = current_time - self._last_operation_time
        if time_since_last < self._min_delay_between_operations:
            time.sleep(self._min_delay_between_operations - time_since_last)
        self._last_operation_time = time.time()
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text to prevent LCD corruption from invalid characters."""
        if text is None:
            return ""
        
        # Convert to string and handle encoding
        try:
            text = str(text)
        except:
            return ""
        
        if not text:
            return ""
        
        # Replace problematic characters
        replacements = {
            '\x00': ' ',  # Null character
            '\t': ' ',    # Tab
            '\n': ' ',    # Newline
            '\r': ' ',    # Carriage return
            '\f': ' ',    # Form feed
            '\v': ' ',    # Vertical tab
            '\b': ' ',    # Backspace
        }
        
        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)
        
        # Keep only safe printable characters
        sanitized = ''
        for char in text:
            try:
                # Check if character is safe for LCD display
                ord_val = ord(char)
                if (32 <= ord_val <= 126):  # Standard ASCII printable
                    sanitized += char
                elif ord_val == 32:  # Space
                    sanitized += char
                else:
                    sanitized += ' '  # Replace problematic chars with space
            except:
                sanitized += ' '
        
        return sanitized
    
    def clear(self):
        """Clear the LCD display safely."""
        with self._display_lock:
            try:
                self._safe_delay()
                self.lcd.lcd_clear()
                self._safe_delay()
                # Reset internal state
                self._current_lines = [""] * self.height
                # Additional delay after clear to ensure it completes
                time.sleep(0.05)
            except Exception as e:
                print(f"LCD clear error: {e}")
                # Try to recover by reinitializing
                time.sleep(0.1)
    
    def display_text(self, text: str, line: int):
        """Display text on the specified line safely."""
        with self._display_lock:
            try:
                # Validate line number
                if not (1 <= line <= self.height):
                    print(f"Invalid line number: {line}")
                    return
                
                # Sanitize and truncate text
                clean_text = self._sanitize_text(text)
                clean_text = clean_text[:self.width]  # Truncate to display width
                clean_text = clean_text.ljust(self.width)  # Pad to full width
                
                # Only update if text has actually changed
                line_index = line - 1
                if line_index < len(self._current_lines) and self._current_lines[line_index] == clean_text:
                    return
                
                self._safe_delay()
                self.lcd.lcd_display_string(clean_text, line)
                self._safe_delay()
                
                # Update internal state
                if line_index < len(self._current_lines):
                    self._current_lines[line_index] = clean_text
                    
            except Exception as e:
                print(f"LCD display error on line {line}: {e}")
                # Try to clear the problematic line
                try:
                    self._safe_delay()
                    self.lcd.lcd_display_string(" " * self.width, line)
                    self._safe_delay()
                except:
                    pass
    
    def get_dimensions(self) -> tuple:
        """Return (width, height) of the display."""
        return (self.width, self.height)


class MockDisplayDriver(DisplayDriver):
    """Mock driver for testing without actual hardware."""
    
    def __init__(self, width: int = 16, height: int = 2):
        self.width = width
        self.height = height
        self.lines = [""] * height
        print(f"Mock Display initialized: {width}x{height}")
    
    def clear(self):
        """Clear the mock display."""
        self.lines = [""] * self.height
        print("Display cleared")
    
    def display_text(self, text: str, line: int):
        """Display text on the specified line."""
        if 1 <= line <= self.height:
            self.lines[line - 1] = text
            print(f"Line {line}: '{text}'")
    
    def get_dimensions(self) -> tuple:
        """Return (width, height) of the display."""
        return (self.width, self.height)


class DisplayScreen:
    """Base class for different display screens."""
    
    def __init__(self, name: str):
        self.name = name
    
    def render(self, driver: DisplayDriver, context: Dict[str, Any]) -> bool:
        """
        Render the screen with the given context.
        Returns True if the screen should continue to be displayed.
        """
        raise NotImplementedError("Subclasses must implement render method")


class RadioDefaultScreen(DisplayScreen):
    """Default radio display showing channel name and current song with marquee scrolling."""
    
    def __init__(self):
        super().__init__("radio_default")
        # Marquee scrolling state for song text
        self.marquee_scroll_offset = 0
        self.last_displayed_song = ""
        self.scroll_state_timer = time.time()
        self.scroll_phase = 'initial_delay'
        # Marquee scrolling state for "Radio Off" text
        self.off_marquee_scroll_offset = 0
        self.off_last_displayed_text = ""
        self.off_scroll_state_timer = time.time()
        self.off_scroll_phase = 'initial_delay'
        # Timing controls
        self.scroll_speed = 0.4
        self.pre_scroll_delay = 2
        self.post_scroll_delay = 2
    
    def render(self, driver: DisplayDriver, context: Dict[str, Any]) -> bool:
        width, height = driver.get_dimensions()
        
        is_playing = context.get('is_playing', False)
        
        if is_playing:
            # Line 1: Channel name
            channel_name = context.get('channel_name', 'Radio')
            # Ensure channel name is clean and properly formatted
            channel_name = str(channel_name).strip()[:width]
            line1_content = channel_name.center(width)
            
            # Line 2: Current song with marquee scrolling
            current_song = context.get('current_song', 'Loading...')
            # Clean the song text
            current_song = str(current_song).strip() if current_song else 'Loading...'
            line2_content = self._handle_marquee_text(current_song, width)
            
        else:
            # Radio is off - show clock and scrolling "Radio Off" status
            line1_content = datetime.now().strftime('%H:%M:%S').center(width)
            # Create a longer "Radio Off" message for marquee effect by repeating it
            off_message = "Radio Off  -  Radio Off  -  Radio Off  -  "
            line2_content = self._handle_marquee_off_text(off_message, width)
        
        # Ensure content is properly padded and clean
        line1_content = line1_content.ljust(width)[:width]
        line2_content = line2_content.ljust(width)[:width]
        
        # Only update if content has changed (more robust comparison)
        if context.get('force_update', False) or context.get('last_line1', '') != line1_content:
            driver.display_text(line1_content, 1)
            context['last_line1'] = line1_content
        
        if context.get('force_update', False) or context.get('last_line2', '') != line2_content:
            driver.display_text(line2_content, 2)
            context['last_line2'] = line2_content
        
        return True  # Continue displaying this screen
    
    def _handle_marquee_text(self, text: str, width: int) -> str:
        """Handle marquee scrolling for text longer than display width."""
        current_time = time.time()
        
        # Reset marquee state if song has changed
        if text != self.last_displayed_song:
            self.marquee_scroll_offset = 0
            self.scroll_state_timer = current_time
            self.scroll_phase = 'initial_delay'
            self.last_displayed_song = text
        
        if len(text) <= width:
            return text.center(width)
        
        # Marquee scrolling for long text
        text_length = len(text)
        max_scroll_value = text_length - width
        
        if self.scroll_phase == 'initial_delay':
            content = text[:width]
            if (current_time - self.scroll_state_timer) >= self.pre_scroll_delay:
                self.scroll_phase = 'scrolling'
                self.scroll_state_timer = current_time
                self.marquee_scroll_offset = 0
        
        elif self.scroll_phase == 'scrolling':
            if (current_time - self.scroll_state_timer) >= self.scroll_speed:
                self.marquee_scroll_offset += 1
                self.scroll_state_timer = current_time
            
            if self.marquee_scroll_offset >= max_scroll_value:
                self.scroll_phase = 'final_delay'
                self.scroll_state_timer = current_time
                self.marquee_scroll_offset = max_scroll_value
            
            start_index = self.marquee_scroll_offset
            end_index = start_index + width
            content = text[start_index:end_index]
        
        elif self.scroll_phase == 'final_delay':
            content = text[max(0, text_length - width):text_length]
            if (current_time - self.scroll_state_timer) >= self.post_scroll_delay:
                self.scroll_phase = 'initial_delay'
                self.scroll_state_timer = current_time
                self.marquee_scroll_offset = 0
        
        return content

    def _handle_marquee_off_text(self, text: str, width: int) -> str:
        """Handle marquee scrolling for Radio Off text to prevent static display."""
        current_time = time.time()
        
        # Reset marquee state if text has changed
        if text != self.off_last_displayed_text:
            self.off_marquee_scroll_offset = 0
            self.off_scroll_state_timer = current_time
            self.off_scroll_phase = 'initial_delay'
            self.off_last_displayed_text = text
        
        if len(text) <= width:
            return text.center(width)
        
        # Marquee scrolling for long text
        text_length = len(text)
        max_scroll_value = text_length - width
        
        if self.off_scroll_phase == 'initial_delay':
            content = text[:width]
            if (current_time - self.off_scroll_state_timer) >= self.pre_scroll_delay:
                self.off_scroll_phase = 'scrolling'
                self.off_scroll_state_timer = current_time
                self.off_marquee_scroll_offset = 0
        
        elif self.off_scroll_phase == 'scrolling':
            if (current_time - self.off_scroll_state_timer) >= self.scroll_speed:
                self.off_marquee_scroll_offset += 1
                self.off_scroll_state_timer = current_time
            
            if self.off_marquee_scroll_offset >= max_scroll_value:
                self.off_scroll_phase = 'final_delay'
                self.off_scroll_state_timer = current_time
                self.off_marquee_scroll_offset = max_scroll_value
            
            start_index = self.off_marquee_scroll_offset
            end_index = start_index + width
            content = text[start_index:end_index]
        
        elif self.off_scroll_phase == 'final_delay':
            content = text[max(0, text_length - width):text_length]
            if (current_time - self.off_scroll_state_timer) >= self.post_scroll_delay:
                self.off_scroll_phase = 'initial_delay'
                self.off_scroll_state_timer = current_time
                self.off_marquee_scroll_offset = 0
        
        return content


class VolumeScreen(DisplayScreen):
    """Screen for displaying volume information with enhanced stability."""
    
    def __init__(self, display_duration: float = 2.0):
        super().__init__("volume")
        self.display_duration = display_duration
        self.start_time = None
    
    def render(self, driver: DisplayDriver, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        width, height = driver.get_dimensions()
        
        line1_content = "Volume".center(width).ljust(width)[:width]
        volume_text = str(context.get('volume_text', 'N/A')).strip()
        line2_content = volume_text.center(width).ljust(width)[:width]
        
        driver.display_text(line1_content, 1)
        driver.display_text(line2_content, 2)
        
        # Return False if display duration has expired
        return (time.time() - self.start_time) < self.display_duration


class ChannelScreen(DisplayScreen):
    """Screen for displaying channel change information with enhanced stability."""
    
    def __init__(self, display_duration: float = 2.0):
        super().__init__("channel")
        self.display_duration = display_duration
        self.start_time = None
    
    def render(self, driver: DisplayDriver, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        width, height = driver.get_dimensions()
        
        line1_content = "Channel".center(width).ljust(width)[:width]
        channel_text = str(context.get('channel_text', 'Unknown')).strip()
        line2_content = channel_text[:width].center(width).ljust(width)[:width]
        
        driver.display_text(line1_content, 1)
        driver.display_text(line2_content, 2)
        
        # Return False if display duration has expired
        return (time.time() - self.start_time) < self.display_duration


class DisplayManager:
    """Main display manager that coordinates screens and drivers with enhanced stability."""
    
    def __init__(self, driver: DisplayDriver):
        self.driver = driver
        self.current_screen = None
        self.default_screen = RadioDefaultScreen()
        self.context = {}
        self.running = False
        
        # Enhanced state tracking
        self.context['last_line1'] = ""
        self.context['last_line2'] = ""
        
        # Add thread safety
        self._update_lock = threading.Lock()
        
        # Screen transition control
        self._screen_transition_in_progress = False
        self._last_screen_change_time = 0
        self._min_screen_change_interval = 0.1  # Prevent rapid screen changes
    
    def set_default_screen(self, screen: DisplayScreen):
        """Set the default screen to use when no temporary screen is active."""
        with self._update_lock:
            self.default_screen = screen
    
    def show_screen(self, screen: DisplayScreen, clear_first: bool = True):
        """Show a specific screen safely, preventing rapid transitions."""
        with self._update_lock:
            current_time = time.time()
            
            # Prevent rapid screen changes that can cause corruption
            if current_time - self._last_screen_change_time < self._min_screen_change_interval:
                time.sleep(self._min_screen_change_interval)
            
            self._screen_transition_in_progress = True
            
            if clear_first:
                self.driver.clear()
                self.context['force_update'] = True
                # More generous delay after clear
                time.sleep(0.02)
            
            self.current_screen = screen
            
            # Reset the screen's state
            if hasattr(screen, 'start_time'):
                screen.start_time = None
            
            # Reset context tracking to force full redraw
            self.context['last_line1'] = ""
            self.context['last_line2'] = ""
            
            self._last_screen_change_time = current_time
            self._screen_transition_in_progress = False
    
    def update_context(self, **kwargs):
        """Update the display context with new data."""
        with self._update_lock:
            # Sanitize context data
            for key, value in kwargs.items():
                if isinstance(value, str):
                    # Clean up string values
                    kwargs[key] = str(value).strip()
            
            self.context.update(kwargs)
    
    def update_display(self):
        """Update the display based on current context and screen."""
        # Skip updates during screen transitions
        if self._screen_transition_in_progress:
            return
        
        with self._update_lock:
            try:
                # Determine which screen to use
                screen_to_render = self.current_screen if self.current_screen else self.default_screen
                
                # Reset force_update flag
                force_update = self.context.get('force_update', False)
                if force_update:
                    self.context['force_update'] = False
                
                # Render the screen
                continue_display = screen_to_render.render(self.driver, self.context)
                
                # If the current screen indicates it should stop, revert to default
                if self.current_screen and not continue_display:
                    self.current_screen = None
                    self.driver.clear()
                    self.context['force_update'] = True
                    self.context['last_line1'] = ""
                    self.context['last_line2'] = ""
                    time.sleep(0.02)  # Delay after clear
                    
            except Exception as e:
                print(f"Display update error: {e}")
                # Try to recover by clearing and resetting
                try:
                    self.driver.clear()
                    time.sleep(0.05)
                    self.context['last_line1'] = ""
                    self.context['last_line2'] = ""
                    self.context['force_update'] = True
                except:
                    pass
    
    def clear_display(self):
        """Clear the display and reset context safely."""
        with self._update_lock:
            self._screen_transition_in_progress = True
            try:
                self.driver.clear()
                self.current_screen = None
                self.context['last_line1'] = ""
                self.context['last_line2'] = ""
                self.context['force_update'] = True
                time.sleep(0.02)  # Ensure clear completes
            finally:
                self._screen_transition_in_progress = False


# Convenience functions for common display operations
def create_i2c_display_manager() -> DisplayManager:
    """Create a display manager with I2C LCD driver."""
    driver = I2CLCDDriver()
    return DisplayManager(driver)


def create_mock_display_manager(width: int = 16, height: int = 2) -> DisplayManager:
    """Create a display manager with mock driver for testing."""
    driver = MockDisplayDriver(width, height)
    return DisplayManager(driver)


# Example custom screen
class ErrorScreen(DisplayScreen):
    """Screen for displaying error messages."""
    
    def __init__(self, error_message: str, display_duration: float = 3.0, persistent: bool = False):
        super().__init__("error")
        self.error_message = error_message
        self.display_duration = display_duration
        self.persistent = persistent  # If True, screen stays until manually cleared
        self.start_time = None
    
    def render(self, driver: DisplayDriver, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        width, height = driver.get_dimensions()
        
        line1_content = "Error:".center(width)
        line2_content = self.error_message[:width].center(width)
        
        driver.display_text(line1_content.ljust(width), 1)
        driver.display_text(line2_content.ljust(width), 2)
        
        # If persistent, stay on screen indefinitely
        if self.persistent:
            return True
        
        return (time.time() - self.start_time) < self.display_duration


class GoodbyeScreen(DisplayScreen):
    """Screen for displaying goodbye message."""
    
    def __init__(self, display_duration: float = 2.0):
        super().__init__("goodbye")
        self.display_duration = display_duration
        self.start_time = None
    
    def render(self, driver: DisplayDriver, context: Dict[str, Any]) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        width, height = driver.get_dimensions()
        
        line1_content = "Goodbye!".center(width)
        line2_content = "".center(width)  # Empty second line
        
        driver.display_text(line1_content.ljust(width), 1)
        driver.display_text(line2_content.ljust(width), 2)
        
        return (time.time() - self.start_time) < self.display_duration
