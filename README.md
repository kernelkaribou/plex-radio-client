# Plex Radio Player - I2C LCD Display

## Overview

The Plex Radio Player Client serves as a hardware client for [Plex Radio](https://github.com/cbattlegear/plex-radio). It requires a 16x2 I2C LCD display and will fail to start without one.

**Hardware Requirements:**
- 16x2 I2C LCD Display (REQUIRED)
- Raspberry Pi or compatible GPIO system
- I2C interface enabled
- GPIO pins for buttons (configurable)

The application is comprised of two components:

1. **Radio Core** (`radio_client.py`) - Handles audio playback, API communication, and button interactions
2. **Display Manager** (`display_manager.py`) - Manages the I2C LCD display with fail-safe operation

## Architecture

### Display System
- **I2C LCD Only** - Exclusively supports 16x2 I2C LCD displays
- **Fail-Safe Design** - Application exits if I2C LCD is not available
- **No Mock/Fallback** - Requires actual hardware for operation

#### Display Screens
- `RadioScreen` - Shows channel name and current song with marquee scrolling
- `VolumeScreen` - Temporary screen for volume changes
- `ChannelScreen` - Temporary screen for channel changes
- `ErrorScreen` - Shows error messages
- Custom screens can be created by extending `DisplayScreen`

#### DisplayManager
- Coordinates between drivers and screens
- Manages screen transitions and context updates
- Handles temporary vs. permanent screens

## Quick Start

### Docker (Recommended)

The easiest way to run the Plex Radio Player is using Docker:

#### Quick Start with Pre-built Images

```bash
# Pull the latest image from GitHub Container Registry
docker pull ghcr.io/kernelkaribou/plex-radio-client:latest

# Run with basic settings (for Raspberry Pi with hardware)
docker run -d \
  --name plex-radio-client \
  --privileged \
  --network host \
  --restart unless-stopped \
  -v $(pwd)/last_channel.txt:/app/last_channel.txt \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse:rw \
  -e PLEX_RADIO_API_URL=http://localhost:5000 \
  ghcr.io/kernelkaribou/plex-radio-client:latest
```

#### Docker Compose (Recommended for Development)

```bash
# Clone the repository for docker-compose.yml
git clone https://github.com/kernelkaribou/plex-radio-client.git
cd plex-radio-client

# Set your user ID for proper permissions
export UID=$(id -u)
export GID=$(id -g)

# Start the service
docker-compose up -d
```

#### Configuration

**Environment Variables:**
- `PLEX_RADIO_API_URL`: URL of the Plex Radio API server (default: `http://localhost:5000`)
- `HARDWARE_MODE`: Set to `false` to disable GPIO/I2C hardware access (default: `true`)
- `GPIO_POWER_PIN`: GPIO pin for power button (default: `25`)
- `GPIO_VOLUME_UP_PIN`: GPIO pin for volume up button (default: `23`)
- `GPIO_VOLUME_DOWN_PIN`: GPIO pin for volume down button (default: `24`)
- `GPIO_CHANNEL_UP_PIN`: GPIO pin for channel up button (default: `14`)
- `GPIO_CHANNEL_DOWN_PIN`: GPIO pin for channel down button (default: `15`)
- `RADIO_QUIET`: Set to `true` for minimal logging (state changes only), `false` for debug output (default: `false`)
- `PULSE_SERVER`: PulseAudio server address if needed

**Volume Mounts:**
- `/app/last_channel.txt`: Persists the last selected channel
- `/run/user/1000/pulse`: PulseAudio socket for audio output
- `/dev/i2c-1` and `/dev/gpiomem`: Hardware device access for Raspberry Pi

#### Testing Without Hardware

For development/testing without physical hardware:

```bash
docker run -it \
  --name plex-radio-test \
  -e HARDWARE_MODE=false \
  -e PLEX_RADIO_API_URL=http://host.docker.internal:5000 \
  ghcr.io/kernelkaribou/plex-radio-client:latest
```

#### Custom GPIO Pin Configuration

```bash
docker run -d \
  --name plex-radio-client \
  --privileged \
  --network host \
  -e PLEX_RADIO_API_URL=http://localhost:5000 \
  -e GPIO_POWER_PIN=26 \
  -e GPIO_VOLUME_UP_PIN=19 \
  -e GPIO_VOLUME_DOWN_PIN=13 \
  -e GPIO_CHANNEL_UP_PIN=6 \
  -e GPIO_CHANNEL_DOWN_PIN=5 \
  ghcr.io/kernelkaribou/plex-radio-client:latest
```

#### Multi-Architecture Support

The container supports multiple architectures:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM 64-bit, Raspberry Pi 4/5)
- `linux/arm/v7` (ARM 32-bit, Raspberry Pi 2/3)

Docker will automatically pull the correct architecture for your system.

### Local Python Installation

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
├── .github/workflows/
│   └── docker-build.yml         # GitHub Actions workflow
├── radio_client.py              # Radio core
├── display_manager.py           # Display system library
├── display_config_examples.py   # Configuration examples
├── last_channel.txt             # Persistence file
├── requirements.txt             # Dependencies
├── Dockerfile                   # Container build instructions
├── docker-compose.yml           # Docker Compose configuration
├── entrypoint.sh               # Container startup script
├── Makefile                    # Build automation
├── DOCKER.md                   # Docker usage guide
└── README.md                   # This documentation
```

## Dependencies

The display manager uses the same dependencies as the original system:
- `i2c_lcd` for I2C LCD displays (when using I2CLCDDriver)
- Standard library modules for core functionality

Additional dependencies for custom drivers (optional):
- `adafruit-circuitpython-ssd1306` for OLED displays
- Other display-specific libraries as needed

## Troubleshooting

### I2C LCD Display Issues

1. **Display corrupted or frozen**:
   ```bash
   # Clear the display directly
   python3 clear_screen.py
   
   # Or from Docker container
   docker exec plex-radio-client python3 clear_screen.py
   ```

2. **I2C LCD not detected**:
   - Ensure I2C is enabled on your system
   - Check device permissions: `ls -la /dev/i2c-*`
   - Verify LCD is connected and powered
   - Test I2C detection: `i2cdetect -y 1`

3. **Permission denied on /dev/i2c-1**:
   - Add user to i2c group: `sudo usermod -a -G i2c $USER`
   - Or run with sudo (not recommended for production)

4. **Application fails to start**:
   - This is expected behavior if no I2C LCD is detected
   - The application requires hardware I2C LCD to operate
   - Check that `i2c-lcd` Python module is installed

### Screen Clear Utility

The `clear_screen.py` script provides a quick way to reset the I2C LCD display:

```bash
# Direct usage
python3 clear_screen.py

# Docker container usage  
docker exec plex-radio-client python3 clear_screen.py

# Make executable for convenience
chmod +x clear_screen.py
./clear_screen.py
```

This utility:
- Clears the entire display
- Shows a brief "Screen Cleared" message
- Performs a final clear
- Exits with proper error codes

### Common Issues

1. **Import Error for i2c_lcd**:
   ```bash
   pip install i2c-lcd
   ```

2. **GPIO button not responding**:
   - Check GPIO pin configuration in environment variables
   - Verify physical wiring matches configured pins
   - Ensure GPIO permissions are correct

### Getting Help

For hardware-related issues:
1. Test I2C connectivity with `i2cdetect`
2. Use the screen clear utility to reset display
3. Check system logs for I2C/GPIO errors

For API connectivity issues:
1. Verify PLEX_RADIO_API_URL is correct
2. Ensure Plex Radio server is running and accessible
2. Check ffplay installation
3. Verify GPIO button connections


## NOTE

I absolutely used AI to write this whole thing and while initially conflicted I dont care as much as I am listening to my tunes faster.