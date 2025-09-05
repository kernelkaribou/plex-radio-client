#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="plex-radio-player"

show_usage() {
    echo -e "${GREEN}Plex Radio Player Service Manager${NC}"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo -e "  ${BLUE}start${NC}     Start the radio service"
    echo -e "  ${BLUE}stop${NC}      Stop the radio service" 
    echo -e "  ${BLUE}restart${NC}   Restart the radio service"
    echo -e "  ${BLUE}status${NC}    Show service status"
    echo -e "  ${BLUE}logs${NC}      Show live logs"
    echo -e "  ${BLUE}enable${NC}    Enable service to start on boot"
    echo -e "  ${BLUE}disable${NC}   Disable service from starting on boot"
    echo -e "  ${BLUE}config${NC}    Show current service configuration"
    echo -e "  ${BLUE}install${NC}   Install the service"
    echo
}

case "$1" in
    start)
        echo -e "${YELLOW}Starting Plex Radio Player service...${NC}"
        sudo systemctl start $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    stop)
        echo -e "${YELLOW}Stopping Plex Radio Player service...${NC}"
        sudo systemctl stop $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    restart)
        echo -e "${YELLOW}Restarting Plex Radio Player service...${NC}"
        sudo systemctl restart $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    status)
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    logs)
        echo -e "${YELLOW}Showing live logs (Ctrl+C to exit)...${NC}"
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    enable)
        echo -e "${YELLOW}Enabling service to start on boot...${NC}"
        sudo systemctl enable $SERVICE_NAME
        echo -e "${GREEN}Service will now start automatically on boot${NC}"
        ;;
    disable)
        echo -e "${YELLOW}Disabling service from starting on boot...${NC}"
        sudo systemctl disable $SERVICE_NAME
        echo -e "${GREEN}Service will no longer start automatically on boot${NC}"
        ;;
    install)
        echo -e "${YELLOW}Running installation script...${NC}"
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        "$SCRIPT_DIR/install-service.sh"
        ;;
    config)
        echo -e "${GREEN}Plex Radio Player Service Configuration${NC}"
        echo
        SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
        if [ -f "$SERVICE_FILE" ]; then
            echo -e "${YELLOW}Current installed service file:${NC}"
            echo "Location: $SERVICE_FILE"
            echo
            cat "$SERVICE_FILE"
        else
            echo -e "${YELLOW}Service not yet installed.${NC}"
            echo "Run './radio-service.sh install' to install the service."
        fi
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
