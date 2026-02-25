#!/bin/bash
# PPL Meta Signage - Remote Configuration Script
# Simple bash wrapper for configuring signage devices remotely

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEVICE_PORT=8009

# Help function
show_help() {
    cat << EOF
PPL Meta Signage - Remote Configuration Tool

Usage: $0 [OPTIONS]

OPTIONS:
    -d, --device-ip IP          IP address of the signage device (required)
    -b, --backend-ip IP         Backend platform IP address
    -p, --discovery-port PORT   Discovery service port (default: 8006)
    --check                     Check device health
    --get                       Get current configuration
    -h, --help                  Show this help message

EXAMPLES:
    # Check device health
    $0 --device-ip 192.168.1.100 --check

    # Get current configuration
    $0 --device-ip 192.168.1.100 --get

    # Configure device
    $0 --device-ip 192.168.1.100 --backend-ip 192.168.1.50

    # Configure with custom discovery port
    $0 --device-ip 192.168.1.100 --backend-ip 192.168.1.50 --discovery-port 8006

EOF
}

# Parse arguments
DEVICE_IP=""
BACKEND_IP=""
DISCOVERY_PORT=8006
CHECK_HEALTH=false
GET_CONFIG=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--device-ip)
            DEVICE_IP="$2"
            shift 2
            ;;
        -b|--backend-ip)
            BACKEND_IP="$2"
            shift 2
            ;;
        -p|--discovery-port)
            DISCOVERY_PORT="$2"
            shift 2
            ;;
        --check)
            CHECK_HEALTH=true
            shift
            ;;
        --get)
            GET_CONFIG=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$DEVICE_IP" ]; then
    echo -e "${RED}Error: Device IP address is required${NC}"
    show_help
    exit 1
fi

BASE_URL="http://${DEVICE_IP}:${DEVICE_PORT}"

# Function to check health
check_health() {
    echo -e "${BLUE}🔌 Connecting to signage device at ${DEVICE_IP}:${DEVICE_PORT}${NC}"
    echo

    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✅ Device is healthy${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ Device health check failed (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to get configuration
get_config() {
    echo -e "${BLUE}📋 Getting current configuration from ${DEVICE_IP}${NC}"
    echo

    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/api/v1/config" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✅ Configuration retrieved successfully${NC}"
        echo
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ Failed to get configuration (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Function to set configuration
set_config() {
    local backend_ip=$1
    local discovery_port=$2

    echo -e "${BLUE}🔧 Configuring signage device${NC}"
    echo -e "   Device IP: ${DEVICE_IP}"
    echo -e "   Backend IP: ${backend_ip}"
    echo -e "   Discovery Port: ${discovery_port}"
    echo

    payload=$(cat <<EOF
{
    "backend_ip": "${backend_ip}",
    "discovery_port": ${discovery_port}
}
EOF
)

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "${BASE_URL}/api/v1/config" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✅ Configuration updated successfully!${NC}"
        echo
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        echo
        echo -e "${YELLOW}⚠️  Please restart the signage application for changes to take effect.${NC}"
        return 0
    else
        echo -e "${RED}❌ Configuration failed (HTTP $http_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Execute requested action
if [ "$CHECK_HEALTH" = true ]; then
    check_health
    exit $?
fi

if [ "$GET_CONFIG" = true ]; then
    get_config
    exit $?
fi

if [ -n "$BACKEND_IP" ]; then
    set_config "$BACKEND_IP" "$DISCOVERY_PORT"
    exit $?
fi

# No action specified
echo -e "${RED}Error: No action specified${NC}"
show_help
exit 1
