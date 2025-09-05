# Docker Usage for Plex Radio Player

This document explains how to run the Plex Radio Player using Docker.

## Quick Start

### Pull from GitHub Container Registry

```bash
docker pull ghcr.io/kernelkaribou/plex-radio-client:latest
```

### Run with Docker

```bash
docker run -d \
  --name plex-radio-client \
  --privileged \
  --network host \
  -v $(pwd)/last_channel.txt:/app/last_channel.txt \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse:rw \
  -e PLEX_RADIO_API_URL=http://localhost:5000 \
  ghcr.io/kernelkaribou/plex-radio-client:latest
```

### Run with Docker Compose

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

## Configuration

### Environment Variables

- `PLEX_RADIO_API_URL`: URL of the Plex Radio API server (default: `http://localhost:5000`)
- `HARDWARE_MODE`: Set to `false` to disable GPIO/I2C hardware access for testing
- `PULSE_SERVER`: PulseAudio server address if needed

### Volume Mounts

- `/app/last_channel.txt`: Persists the last selected channel
- `/run/user/1000/pulse`: PulseAudio socket for audio output
- `/dev/i2c-1` and `/dev/gpiomem`: Hardware device access for Raspberry Pi

### Required Privileges

The container needs `--privileged` mode or specific device access for:
- GPIO pins (buttons)
- I2C bus (LCD display)
- Audio devices

## Hardware Requirements

### Raspberry Pi Setup

The container is designed to run on Raspberry Pi with:
- GPIO buttons connected to pins 14, 15, 23, 24, 25
- I2C LCD display on bus 1
- PulseAudio for volume control

### Testing Without Hardware

For development/testing without physical hardware:

```bash
docker run -it \
  --name plex-radio-test \
  -e HARDWARE_MODE=false \
  -e PLEX_RADIO_API_URL=http://host.docker.internal:5000 \
  ghcr.io/kernelkaribou/plex-radio-client:latest
```

## Building Locally

```bash
# Clone the repository
git clone https://github.com/kernelkaribou/plex-radio-client.git
cd plex-radio-client

# Build the image
docker build -t plex-radio-client:local .

# Run the locally built image
docker run -d --name plex-radio-client --privileged --network host plex-radio-client:local
```

## Multi-Architecture Support

The GitHub Actions workflow builds images for:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM 64-bit, Raspberry Pi 4/5)
- `linux/arm/v7` (ARM 32-bit, Raspberry Pi 2/3)

Docker will automatically pull the correct architecture for your system.

## Troubleshooting

### Audio Issues

```bash
# Check PulseAudio is running on host
systemctl --user status pulseaudio

# Test audio in container
docker exec -it plex-radio-client ffplay -f lavfi -i "sine=frequency=1000:duration=2"
```

### GPIO/I2C Issues

```bash
# Check I2C devices on host
ls -la /dev/i2c*

# Check GPIO access
ls -la /dev/gpiomem

# Run container with debug
docker run -it --privileged --network host --entrypoint bash plex-radio-client
```

### Container Logs

```bash
# View container logs
docker logs plex-radio-client

# Follow logs in real-time
docker logs -f plex-radio-client
```

### Health Check

The container includes a health check that verifies API connectivity:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' plex-radio-client
```

## Development

### Local Development with Docker

```bash
# Mount source code for live development
docker run -it \
  --name plex-radio-dev \
  --privileged \
  --network host \
  -v $(pwd):/app \
  -w /app \
  python:3.11-slim \
  bash

# Inside container, install dependencies and run
pip install -r requirements.txt
python radio_client.py
```

### Debugging

```bash
# Run container interactively
docker run -it --privileged --network host --entrypoint bash plex-radio-client

# Check system dependencies
which ffplay
pactl info
i2cdetect -y 1
```

## Security Considerations

- The container runs as a non-root user (UID 1000) where possible
- Privileged mode is required for hardware access on Raspberry Pi
- Consider using `--device` flags instead of `--privileged` for production deployments
- Network host mode is used for simplicity but could be restricted with proper port mapping
