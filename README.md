# Plex Radio Player - Modular Display System

## Overview

The Plex Radio Player Client is used for serving as a client for [Plex Radio](https://github.com/cbattlegear/plex-radio). It is comprised of two components.

1. **Radio Core** (`radio_client.py`) - Handles audio playback, API communication, and button interactions
2. **Display Manager** (`display_manager.py`) - Provides a configurable display system that works with different screen types

## Architecture

### Display Manager Components

#### DisplayDriver (Abstract Base Class)
- `I2CLCDDriver` - For 1602 I2C LCD displays (16x2)
- `MockDisplayDriver` - For testing without hardware
- Custom drivers can be created by extending `DisplayDriver`

#### DisplayScreen Classes
- `RadioDefaultScreen` - Shows channel name and current song with marquee scrolling
- `VolumeScreen` - Temporary screen for volume changes
- `ChannelScreen` - Temporary screen for channel changes
- `ErrorScreen` - Shows error messages
- Custom screens can be created by extending `DisplayScreen`

#### DisplayManager
- Coordinates between drivers and screens
- Manages screen transitions and context updates
- Handles temporary vs. permanent screens

## Quick Start

### Using the Refactored System

```python
from radio_client import PlexRadioClient
from display_manager import create_i2c_display_manager

# Create radio client with I2C LCD display
plex_radio = PlexRadioClient()

# The radio client will automatically use I2C LCD display
# Run the main script:
# python radio_client.py
```

### Creating Custom Display Configurations

```python
from display_manager import DisplayManager, MockDisplayDriver
from radio_client import PlexRadioClient

# Create custom display configuration
driver = MockDisplayDriver(20, 4)  # 20x4 character display
display_manager = DisplayManager(driver)

# Create radio client with custom display
plex_radio = PlexRadioClient(display_manager=display_manager)
```

## Creating Custom Display Drivers

To support a new display type, extend the `DisplayDriver` class:

```python
from display_manager import DisplayDriver

class MyDisplayDriver(DisplayDriver):
    def __init__(self):
        # Initialize your display hardware
        self.width = 16
        self.height = 2
    
    def clear(self):
        # Clear the display
        pass
    
    def display_text(self, text: str, line: int):
        # Display text on the specified line (1-indexed)
        pass
    
    def get_dimensions(self) -> tuple:
        return (self.width, self.height)
```

## Creating Custom Screens

To create a new screen type, extend the `DisplayScreen` class:

```python
from display_manager import DisplayScreen

class WeatherScreen(DisplayScreen):
    def __init__(self):
        super().__init__("weather")
    
    def render(self, driver, context):
        # Get display dimensions
        width, height = driver.get_dimensions()
        
        # Get data from context
        temperature = context.get('temperature', 'N/A')
        
        # Display content
        driver.display_text(f"Temp: {temperature}".center(width), 1)
        driver.display_text("Weather".center(width), 2)
        
        # Return True to continue displaying, False to revert to default
        return True
```

## Integration Examples

### Example 1: OLED Display
```python
from display_manager import DisplayDriver, DisplayManager
import board
from adafruit_ssd1306 import SSD1306_I2C

class OLEDDriver(DisplayDriver):
    def __init__(self):
        self.oled = SSD1306_I2C(128, 32, board.I2C())
        self.width = 21  # Characters that fit in 128px
        self.height = 4  # Lines that fit in 32px
    
    def clear(self):
        self.oled.fill(0)
        self.oled.show()
    
    def display_text(self, text: str, line: int):
        y = (line - 1) * 8
        self.oled.text(text, 0, y, 1)
        self.oled.show()
    
    def get_dimensions(self):
        return (self.width, self.height)

# Use with radio client
display_manager = DisplayManager(OLEDDriver())
plex_radio = PlexRadioClient(display_manager=display_manager)
```

### Example 2: Custom Screen with Multiple Information
```python
class InfoScreen(DisplayScreen):
    def __init__(self):
        super().__init__("info")
        self.start_time = time.time()
    
    def render(self, driver, context):
        width, height = driver.get_dimensions()
        
        # Show multiple pieces of information
        lines = [
            f"Channel: {context.get('channel_name', 'N/A')}",
            f"Song: {context.get('current_song', 'N/A')}",
            f"Volume: {context.get('last_volume', 'N/A')}",
            f"Time: {time.strftime('%H:%M:%S')}"
        ]
        
        for i, line in enumerate(lines[:height], 1):
            driver.display_text(line[:width].ljust(width), i)
        
        # Display for 5 seconds, then revert to default
        return (time.time() - self.start_time) < 5
```

### Example 3: Automatic Screen Rotation
```python
from display_config_examples import AdvancedDisplayManager, WeatherScreen

# Create advanced display manager
display_manager = AdvancedDisplayManager(I2CLCDDriver())

# Enable rotation between multiple screens
rotation_screens = [
    WeatherScreen(),
    InfoScreen(),
    RadioDefaultScreen()
]
display_manager.enable_screen_rotation(rotation_screens, interval=8)

# Use with radio client
plex_radio = PlexRadioClient(display_manager=display_manager)
```

## File Structure

```
plex-radio-player/
├── radio_client.py              # radio core
├── display_manager.py           # Display system library
├── display_config_examples.py   # Configuration examples
├── last_channel.txt             # Persistence file
├── requirements.txt             # Dependencies
└── README.md           # This documentation
```

## Dependencies

The display manager uses the same dependencies as the original system:
- `i2c_lcd` for I2C LCD displays (when using I2CLCDDriver)
- Standard library modules for core functionality

Additional dependencies for custom drivers (optional):
- `adafruit-circuitpython-ssd1306` for OLED displays
- Other display-specific libraries as needed

## Troubleshooting

### Common Issues

1. **Import Error for i2c_lcd**:
   - Ensure the `i2c_lcd` module is available
   - Use `MockDisplayDriver` for testing without hardware

2. **Display not updating**:
   - Check that `update_display()` is being called regularly
   - Verify display driver implementation

3. **Custom screens not working**:
   - Ensure `render()` method returns `True` or `False` appropriately
   - Check that context data is being provided correctly

### Getting Help

For display-related issues:
1. Test with `MockDisplayDriver` first
2. Check the examples in `display_config_examples.py`
3. Verify your custom driver implements all required methods

For radio functionality issues:
1. Test API connectivity separately
2. Check ffplay installation
3. Verify GPIO button connections


## NOTE

I absolutely used AI to write this whole thing and while initially conflicted I dont care as much as I am listening to my tunes faster.