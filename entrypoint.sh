#!/bin/bash
# Startup script for Plex Radio Player container

set -e

echo "Starting Plex Radio Player..."

# Check if running on actual hardware vs in a container
if [ -e /dev/gpiomem ] && [ -e /dev/i2c-1 ]; then
    echo "Hardware detected - GPIO and I2C devices available"
    # Don't override HARDWARE_MODE if user explicitly set it
    if [ -z "$HARDWARE_MODE" ]; then
        export HARDWARE_MODE=true
    fi
else
    echo "No hardware detected - running in mock mode"
    # Don't override HARDWARE_MODE if user explicitly set it to true for testing
    if [ -z "$HARDWARE_MODE" ]; then
        export HARDWARE_MODE=false
    fi
fi

# Initialize PulseAudio if needed
if [ -n "$PULSE_SERVER" ]; then
    echo "Using PulseAudio server: $PULSE_SERVER"
    export PULSE_RUNTIME_PATH="/run/user/1000/pulse"
fi

# Set default API URL if not provided
if [ -z "$PLEX_RADIO_API_URL" ]; then
    export PLEX_RADIO_API_URL="http://localhost:5000"
fi
echo "Using API URL: $PLEX_RADIO_API_URL"

# Show GPIO pin configuration if hardware mode is enabled
if [ "${HARDWARE_MODE:-true}" = "true" ]; then
    echo "GPIO Pin Configuration:"
    echo "  Power Button: ${GPIO_POWER_PIN:-25}"
    echo "  Volume Up: ${GPIO_VOLUME_UP_PIN:-23}"
    echo "  Volume Down: ${GPIO_VOLUME_DOWN_PIN:-24}"
    echo "  Channel Up: ${GPIO_CHANNEL_UP_PIN:-14}"
    echo "  Channel Down: ${GPIO_CHANNEL_DOWN_PIN:-15}"
fi

# Check if ffplay is available
if ! command -v ffplay &> /dev/null; then
    echo "ERROR: ffplay not found. Please ensure ffmpeg is installed."
    exit 1
fi

echo "Configuration complete. Starting radio client..."

# Execute the main application
exec python radio_client.py "$@"
