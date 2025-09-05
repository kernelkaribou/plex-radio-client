#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Plex Radio Player as a systemd service...${NC}"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}Don't run this script as root. It will use sudo when needed.${NC}" 
   exit 1
fi

# Get the current directory and parent directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}Virtual environment created at $VENV_DIR${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

echo -e "${YELLOW}Installing dependencies in virtual environment...${NC}"
# Upgrade pip and install wheel first to avoid deprecation warnings
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools

# Install dependencies with modern pip options
"$VENV_DIR/bin/pip" install --use-pep517 -r "$PROJECT_DIR/requirements.txt"

# Install additional GPIO libraries for Raspberry Pi
echo -e "${YELLOW}Installing GPIO libraries for Raspberry Pi...${NC}"
"$VENV_DIR/bin/pip" install RPi.GPIO lgpio

echo -e "${YELLOW}Setting up configuration file...${NC}"
CONFIG_FILE="$PROJECT_DIR/radio_server_config.yaml"
EXAMPLE_CONFIG="$PROJECT_DIR/example_radio_server_config.yaml"

if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}Configuration file already exists: $CONFIG_FILE${NC}"
else
    if [ -f "$EXAMPLE_CONFIG" ]; then
        cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
        echo -e "${GREEN}Created configuration file from example: $CONFIG_FILE${NC}"
        echo -e "${YELLOW}Please edit $CONFIG_FILE to configure your API URL and GPIO pins${NC}"
    else
        echo -e "${YELLOW}Warning: Example configuration file not found at $EXAMPLE_CONFIG${NC}"
        echo -e "${YELLOW}You will need to create $CONFIG_FILE manually${NC}"
    fi
fi

echo -e "${YELLOW}Setting up I2C permissions...${NC}"
sudo usermod -a -G i2c $USER

echo -e "${YELLOW}Generating dynamic systemd service file...${NC}"
# Get current user and project directory
CURRENT_USER=$(whoami)
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

# Generate the service file with dynamic paths
cat > /tmp/plex-radio-player.service << EOF
[Unit]
Description=Plex Radio Player Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
SupplementaryGroups=gpio spi i2c audio video render
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/.venv/bin:/home/$CURRENT_USER/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u $CURRENT_USER)
Environment=PULSE_SERVER=unix:/run/user/$(id -u $CURRENT_USER)/pulse/native
Environment=HOME=/home/$CURRENT_USER
ExecStartPre=/bin/sleep 10
ExecStart=$VENV_PYTHON $PROJECT_DIR/radio_client.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
ReadWritePaths=$PROJECT_DIR
ReadWritePaths=/dev/gpiomem
ReadWritePaths=/dev/mem
ReadWritePaths=/sys/class/gpio
ReadWritePaths=/sys/devices
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

echo -e "${YELLOW}Installing systemd service...${NC}"
sudo cp /tmp/plex-radio-player.service /etc/systemd/system/
rm /tmp/plex-radio-player.service
sudo systemctl daemon-reload

echo -e "${YELLOW}Enabling service to start on boot...${NC}"
sudo systemctl enable plex-radio-player.service

echo -e "${GREEN}Installation complete!${NC}"
echo
echo -e "${YELLOW}Service installed with the following configuration:${NC}"
echo "  User: $CURRENT_USER"
echo "  Project Directory: $PROJECT_DIR"
echo "  Virtual Environment: $PROJECT_DIR/.venv"
echo "  Python Executable: $VENV_PYTHON"
echo "  Service File: /etc/systemd/system/plex-radio-player.service"
echo "  Config File: $PROJECT_DIR/radio_server_config.yaml"
echo
echo -e "${YELLOW}Available commands:${NC}"
echo "  Start service:    sudo systemctl start plex-radio-player"
echo "  Stop service:     sudo systemctl stop plex-radio-player"
echo "  Restart service:  sudo systemctl restart plex-radio-player"
echo "  Check status:     sudo systemctl status plex-radio-player"
echo "  View logs:        sudo journalctl -u plex-radio-player -f"
echo "  Disable service:  sudo systemctl disable plex-radio-player"
echo
echo -e "${YELLOW}Note:${NC} You may need to logout and login again for I2C group membership to take effect."
echo -e "${YELLOW}Note:${NC} The service will start automatically on next boot."
echo -e "${YELLOW}Note:${NC} Dependencies are installed in a virtual environment to avoid system conflicts."
echo -e "${YELLOW}Note:${NC} GPIO libraries (RPi.GPIO, lgpio) are installed for Raspberry Pi compatibility."
echo -e "${YELLOW}Note:${NC} Please review and edit radio_server_config.yaml to configure your API URL and GPIO pins."
echo
echo -e "${GREEN}To start the service now, run: sudo systemctl start plex-radio-player${NC}"
