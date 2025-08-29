"""
Example configuration and usage of the Plex Radio Player display system.

This file demonstrates how to create custom display configurations
and integrate them with the radio player.
"""

from display_manager import (
    DisplayManager, DisplayScreen, DisplayDriver,
    I2CLCDDriver, MockDisplayDriver,
    RadioDefaultScreen, VolumeScreen, ChannelScreen
)
import time


# Example 1: Custom OLED Display Driver
class OLEDDisplayDriver(DisplayDriver):
    """Example driver for OLED displays using Adafruit SSD1306."""
    
    def __init__(self):
        try:
            # Example imports for OLED (would need actual library)
            # import board
            # import digitalio
            # from adafruit_ssd1306 import SSD1306_I2C
            
            # self.oled = SSD1306_I2C(128, 32, board.I2C())
            self.width = 21  # Characters for 128px width
            self.height = 4   # Lines for 32px height
            print("OLED Display Driver initialized (mock)")
        except ImportError:
            raise ImportError("OLED display libraries not found")
    
    def clear(self):
        print("OLED: Display cleared")
        # self.oled.fill(0)
        # self.oled.show()
    
    def display_text(self, text: str, line: int):
        print(f"OLED Line {line}: '{text}'")
        # Implementation would draw text to OLED buffer
        # self.oled.text(text, 0, (line-1) * 8, 1)
        # self.oled.show()
    
    def get_dimensions(self) -> tuple:
        return (self.width, self.height)


# Example 2: Custom Screen with Weather Information
class WeatherScreen(DisplayScreen):
    """Custom screen that shows weather information."""
    
    def __init__(self, display_duration: float = 5.0):
        super().__init__("weather")
        self.display_duration = display_duration
        self.start_time = None
    
    def render(self, driver: DisplayDriver, context: dict) -> bool:
        if self.start_time is None:
            self.start_time = time.time()
        
        width, height = driver.get_dimensions()
        
        # Mock weather data (in real implementation, fetch from API)
        temperature = context.get('temperature', '22°C')
        condition = context.get('weather_condition', 'Sunny')
        
        line1_content = f"Weather: {condition}"[:width].center(width)
        line2_content = f"Temp: {temperature}"[:width].center(width)
        
        driver.display_text(line1_content.ljust(width), 1)
        driver.display_text(line2_content.ljust(width), 2)
        
        return (time.time() - self.start_time) < self.display_duration


# Example 3: Multi-line Radio Screen for larger displays
class ExtendedRadioScreen(DisplayScreen):
    """Extended radio screen for displays with more than 2 lines."""
    
    def __init__(self):
        super().__init__("extended_radio")
    
    def render(self, driver: DisplayDriver, context: dict) -> bool:
        width, height = driver.get_dimensions()
        
        if context.get('is_playing', False):
            channel_name = context.get('channel_name', 'Radio')
            current_song = context.get('current_song', 'Loading...')
            
            # Split song into artist and title if formatted as "Artist - Title"
            if ' - ' in current_song:
                artist, title = current_song.split(' - ', 1)
            else:
                artist, title = '', current_song
            
            lines = [
                f"🎵 {channel_name}"[:width].center(width),
                title[:width].center(width),
                artist[:width].center(width) if artist else "",
                time.strftime("%H:%M:%S").center(width) if height > 3 else ""
            ]
        else:
            lines = [
                "Radio Player".center(width),
                "OFF".center(width),
                time.strftime("%H:%M:%S").center(width),
                time.strftime("%Y-%m-%d").center(width) if height > 3 else ""
            ]
        
        # Display lines up to display height
        for i, line in enumerate(lines[:height], 1):
            if line:  # Only display non-empty lines
                driver.display_text(line.ljust(width), i)
        
        return True


# Example 4: Configuration Factory
class DisplayConfigFactory:
    """Factory for creating different display configurations."""
    
    @staticmethod
    def create_standard_lcd():
        """Create standard 16x2 LCD configuration."""
        driver = I2CLCDDriver()
        return DisplayManager(driver)
    
    @staticmethod
    def create_mock_display():
        """Create mock display for testing."""
        driver = MockDisplayDriver(16, 2)
        return DisplayManager(driver)
    
    @staticmethod
    def create_oled_display():
        """Create OLED display configuration."""
        driver = OLEDDisplayDriver()
        manager = DisplayManager(driver)
        # Use extended screen for OLED
        manager.set_default_screen(ExtendedRadioScreen())
        return manager
    
    @staticmethod
    def create_large_lcd():
        """Create configuration for larger LCD (20x4)."""
        driver = MockDisplayDriver(20, 4)  # Simulate 20x4 display
        manager = DisplayManager(driver)
        manager.set_default_screen(ExtendedRadioScreen())
        return manager


# Example 5: Custom Display Manager with Multiple Screens
class AdvancedDisplayManager(DisplayManager):
    """Extended display manager with additional features."""
    
    def __init__(self, driver: DisplayDriver):
        super().__init__(driver)
        self.screen_rotation_enabled = False
        self.screen_rotation_interval = 10  # seconds
        self.last_screen_change = time.time()
        self.rotation_screens = []
    
    def enable_screen_rotation(self, screens: list, interval: float = 10):
        """Enable automatic rotation between multiple screens."""
        self.screen_rotation_enabled = True
        self.rotation_screens = screens
        self.screen_rotation_interval = interval
        self.last_screen_change = time.time()
    
    def disable_screen_rotation(self):
        """Disable automatic screen rotation."""
        self.screen_rotation_enabled = False
    
    def update_display(self):
        """Enhanced update with screen rotation support."""
        # Handle screen rotation if enabled and no manual screen is active
        if (self.screen_rotation_enabled and 
            not self.current_screen and 
            self.rotation_screens and
            time.time() - self.last_screen_change > self.screen_rotation_interval):
            
            # Rotate to next screen
            current_index = getattr(self, '_rotation_index', 0)
            next_index = (current_index + 1) % len(self.rotation_screens)
            self._rotation_index = next_index
            
            next_screen = self.rotation_screens[next_index]
            self.show_screen(next_screen, clear_first=True)
            self.last_screen_change = time.time()
        
        super().update_display()


# Example usage function
def demo_configurations():
    """Demonstrate different display configurations."""
    
    print("=== Display Configuration Demo ===")
    
    # Test different configurations
    configs = [
        ("Standard LCD", DisplayConfigFactory.create_standard_lcd()),
        ("Mock Display", DisplayConfigFactory.create_mock_display()),
        ("Large LCD", DisplayConfigFactory.create_large_lcd()),
    ]
    
    for name, display_manager in configs:
        print(f"\n--- Testing {name} ---")
        
        # Update context
        display_manager.update_context(
            is_playing=True,
            channel_name="Classic Rock FM",
            current_song="Led Zeppelin - Stairway to Heaven"
        )
        
        # Update display a few times
        for i in range(3):
            display_manager.update_display()
            time.sleep(0.1)
        
        # Test volume screen
        volume_screen = VolumeScreen()
        display_manager.show_screen(volume_screen)
        display_manager.update_context(volume_text="75%")
        display_manager.update_display()
        time.sleep(0.5)
        
        # Let volume screen expire
        time.sleep(2.5)
        display_manager.update_display()
        
        print(f"{name} demo completed")


if __name__ == "__main__":
    demo_configurations()
