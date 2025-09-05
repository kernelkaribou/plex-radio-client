# Plex Radio Player - I2C LCD Display

## Overview

The Plex Radio Player Client serves as a hardware client for [Plex Radio](https://github.com/cbattlegear/plex-radio). It requires a 16x2 I2C LCD display and five physical buttons to function.

**Hardware Requirements:**
- 16x2 I2C LCD Display (REQUIRED)
- Raspberry Pi or compatible GPIO system
- I2C interface enabled
- GPIO pins for buttons (configurable)

The application consists of:

1. **Radio Core** (`radio_client.py`) - Handles audio playbook, API communication, and button interactions
2. **Display Manager** (`display_manager.py`) - Manages the I2C LCD display

## Quick Start

### Running as a Service (Recommended)

For automatic startup on boot and crash recovery, install as a systemd service:

```bash
# Install and start the service
cd service
./install-service.sh

# Use the service manager for control
./radio-service.sh start    # Start service
./radio-service.sh stop     # Stop service
./radio-service.sh status   # Check status
./radio-service.sh logs     # View logs
```

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Enable I2C on Raspberry Pi:**
   ```bash
   sudo raspi-config
   # Interface Options -> I2C -> Enable
   ```

3. **Configuration:**
   Copy `example_radio_server_config.yaml` to `radio_server_config.yaml`, provide the plex-server-api URL and GPIO pin configurations

4. **Run the application:**
   ```bash
   python3 radio_client.py
   ```

## Features

### Display Modes
- **Radio ON:** Shows channel name and current song with marquee scrolling
- **Radio OFF:** Shows live clock (24-hour format) and date (MM/DD/YYYY)
- **Volume Control:** Temporary screen showing current volume level
- **Channel Change:** Temporary screen showing channel name
- **Error Messages:** Clear error display for troubleshooting

### Controls
- **Power Button:** Toggle radio on/off
- **Volume Buttons:** Adjust system volume by 5% increments
- **Channel Buttons:** Navigate through available channels
- **Channel Persistence:** Remembers last selected channel

## Dependencies

The application requires only these essential packages:

- `gpiozero` - GPIO button support
- `i2c-lcd` - I2C LCD display driver
- `requests` - API communication
- `PyYAML` - Configuration file parsing

## File Structure

```
plex-radio-player/
├── radio_client.py      # Main application
├── display_manager.py   # Display manager
├── clear_screen.py      # LCD clear utility
├── example_radio_server_config.yaml          # Configuration file
├── last_channel.txt     # Channel persistence
├── requirements.txt     # Dependencies
├── service/             # Service management files
│   ├── install-service.sh     # Service installation script
│   ├── radio-service.sh       # Service management utility
└── README.md            # This documentation
```

## Troubleshooting

### I2C LCD Display Issues

1. **Display corrupted or frozen**:
   ```bash
   python3 clear_screen.py
   ```

2. **I2C LCD not detected**:
   - Ensure I2C is enabled: `sudo raspi-config`
   - Check device permissions: `ls -la /dev/i2c-*`
   - Verify LCD is connected and powered
   - Test I2C detection: `i2cdetect -y 1`

3. **Permission denied on /dev/i2c-1**:
   - Add user to i2c group: `sudo usermod -a -G i2c $USER`
   - Logout and login again

4. **Application fails to start**:
   - This is expected behavior if no I2C LCD is detected
   - The application requires hardware I2C LCD to operate
   - Check that `i2c-lcd` Python module is installed

### Common Issues

1. **Import Error for i2c_lcd**:
   ```bash
   pip install i2c-lcd
   ```

2. **GPIO button not responding**:
   - Check GPIO pin configuration in `config.yaml`
   - Verify physical wiring matches configured pins
   - Ensure GPIO permissions are correct

3. **ffplay not found**:
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

4. **API connectivity issues**:
   - Verify API URL is correct in `config.yaml`
   - Ensure Plex Radio server is running and accessible
   - Check network connectivity

## Getting Help

For hardware-related issues:
1. Test I2C connectivity with `i2cdetect -y 1`
2. Use the screen clear utility to reset display: `python3 clear_screen.py`
3. Check system logs for I2C/GPIO errors

For API connectivity issues:
1. Verify the Plex Radio server is running
2. Test API endpoint manually: `curl http://your-server:5000/channels`
3. Check firewall settings


## Note

I absolutely used AI to write this because I am shameless and just wanted to listen to my tunes.