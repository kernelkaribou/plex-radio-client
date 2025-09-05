#!/bin/bash
# Startup script for Plex Radio Player container

set -e

echo "Starting Plex Radio Player..."

# Check if running on actual hardware vs in a container
if [ -e /dev/gpiomem ] && [ -e /dev/i2c-1 ]; then
    echo "Hardware detected - GPIO and I2C devices available"
    export HARDWARE_MODE=true
else
    echo "No hardware detected - running in mock mode"
    export HARDWARE_MODE=false
fi

# Initialize PulseAudio if needed
if [ -n "$PULSE_SERVER" ]; then
    echo "Using PulseAudio server: $PULSE_SERVER"
    export PULSE_RUNTIME_PATH="/run/user/1000/pulse"
fi

# Set default API URL if not provided
if [ -z "$PLEX_RADIO_API_URL" ]; then
    export PLEX_RADIO_API_URL="http://localhost:5000"
    echo "Using default API URL: $PLEX_RADIO_API_URL"
fi

# Check if ffplay is available
if ! command -v ffplay &> /dev/null; then
    echo "ERROR: ffplay not found. Please ensure ffmpeg is installed."
    exit 1
fi

echo "Configuration complete. Starting radio client..."

# Execute the main application
exec python radio_client.py "$@"
