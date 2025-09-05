# Container Deployment Guide

This guide explains how your Plex Radio Player has been containerized and how to use it.

## 🎉 What Was Completed

Your repository has been successfully containerized with:

### ✅ Docker Support
- **Dockerfile**: Optimized for Python 3.11 with all system dependencies
- **Multi-architecture builds**: Supports AMD64, ARM64, and ARMv7 (Raspberry Pi)
- **Security**: Runs as non-root user with minimal privileges
- **Hardware detection**: Automatically handles GPIO/I2C availability

### ✅ GitHub Actions CI/CD
- **Automated builds**: Triggers on push to main/master/docker_build branches
- **Container Registry**: Images published to `ghcr.io/kernelkaribou/plex-radio-client`
- **Multi-platform**: Builds for multiple architectures simultaneously
- **Caching**: Optimized build times with layer caching

### ✅ Development Tools
- **docker-compose.yml**: Easy local development setup
- **Makefile**: Common operations (build, run, test, clean)
- **entrypoint.sh**: Smart initialization script
- **.dockerignore**: Optimized build context

### ✅ Documentation
- **DOCKER.md**: Comprehensive Docker usage guide
- **Updated README.md**: Quick start with Docker instructions
- **Code comments**: Detailed inline documentation

## 🚀 How to Use

### For End Users

#### Option 1: Use Pre-built Images (Recommended)
```bash
# Pull the latest image
docker pull ghcr.io/kernelkaribou/plex-radio-client:latest

# Run on Raspberry Pi with hardware
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

#### Option 2: Use Docker Compose
```bash
git clone https://github.com/kernelkaribou/plex-radio-client.git
cd plex-radio-client
export UID=$(id -u) && export GID=$(id -g)
docker-compose up -d
```

### For Development

#### Quick Build and Test
```bash
# Clone and enter directory
cd plex-radio-player

# Build locally
make build

# Test without hardware
make run-dev

# View logs
make logs

# Clean up
make clean
```

#### Manual Docker Commands
```bash
# Build
docker build -t plex-radio-client .

# Run for testing (no hardware required)
docker run --rm -e HARDWARE_MODE=false plex-radio-client

# Run on Raspberry Pi
docker run -d --privileged --network host plex-radio-client
```

## 🔧 Configuration

### Environment Variables
- `PLEX_RADIO_API_URL`: API server URL (default: http://localhost:5000)
- `HARDWARE_MODE`: Enable/disable GPIO hardware (default: true)
- `GPIO_POWER_PIN`: GPIO pin for power button (default: 25)
- `GPIO_VOLUME_UP_PIN`: GPIO pin for volume up button (default: 23)
- `GPIO_VOLUME_DOWN_PIN`: GPIO pin for volume down button (default: 24)
- `GPIO_CHANNEL_UP_PIN`: GPIO pin for channel up button (default: 14)
- `GPIO_CHANNEL_DOWN_PIN`: GPIO pin for channel down button (default: 15)
- `PULSE_SERVER`: PulseAudio server if needed

### Volume Mounts
- `/app/last_channel.txt`: Persist channel selection
- `/run/user/1000/pulse`: Audio output via PulseAudio
- `/dev/i2c-1`, `/dev/gpiomem`: Hardware device access

## 📦 GitHub Container Registry

Your images are automatically published to:
**`ghcr.io/kernelkaribou/plex-radio-client`**

Available tags:
- `latest`: Latest build from main branch
- `docker_build`: Latest build from docker_build branch
- `v1.0.0`: Tagged releases (when you create Git tags)

## 🔄 Automated Workflows

The GitHub Actions workflow (`/.github/workflows/docker-build.yml`) will:

1. **Trigger on**:
   - Push to `main`, `master`, or `docker_build` branches  
   - New Git tags starting with `v*`
   - Pull requests (build only, no publish)

2. **Build process**:
   - Multi-architecture builds (AMD64, ARM64, ARMv7)
   - Automated tagging based on branch/tag
   - Layer caching for faster builds
   - Security scanning (built-in GitHub features)

3. **Publishing**:
   - Images pushed to GitHub Container Registry
   - Public access (or configure as needed)
   - Automatic cleanup of old images

## 🛠️ Hardware Support

### Raspberry Pi (Full Hardware Mode)
- GPIO buttons (pins 14, 15, 23, 24, 25)
- I2C LCD display (bus 1)
- PulseAudio for volume control
- Requires `--privileged` mode

### Docker Desktop / Other Systems (Mock Mode)  
- Automatically detects missing hardware
- Uses mock display driver for testing
- No GPIO button support (graceful fallback)
- Standard audio output

## 🚨 Troubleshooting

### Build Issues
```bash
# Check build logs
docker build --no-cache -t test .

# Test import without running main
docker run --rm test python -c "import radio_client"
```

### Runtime Issues
```bash
# Check container logs
docker logs plex-radio-client

# Test with debug mode
docker run -it --entrypoint bash plex-radio-client

# Health check
docker inspect --format='{{.State.Health.Status}}' plex-radio-client
```

### GitHub Actions Issues
- Check the Actions tab in your GitHub repository
- Verify GITHUB_TOKEN permissions (should be automatic)
- Check if Container Registry is enabled in repository settings

## 📚 Next Steps

1. **Create a release**: Push a git tag like `v1.0.0` to trigger a versioned build
2. **Customize configuration**: Modify docker-compose.yml for your environment  
3. **Add monitoring**: Consider adding health checks or log aggregation
4. **Documentation**: Update DOCKER.md with your specific use cases

## 🎯 Summary

Your Plex Radio Player is now:
- ✅ **Containerized** and ready for any Docker environment
- ✅ **Automated** with CI/CD pipeline for continuous builds  
- ✅ **Published** to GitHub Container Registry
- ✅ **Multi-platform** supporting various architectures
- ✅ **Production-ready** with security best practices

Users can now run your radio player with a single `docker pull` and `docker run` command!
