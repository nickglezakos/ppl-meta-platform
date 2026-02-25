#!/bin/bash
# PPL Meta Signage - Diagnostic Tool
# Run this script to collect diagnostic information when the signage app hangs

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}PPL Meta Signage - Diagnostics${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if running as pi user
if [ "$(whoami)" != "pi" ]; then
    echo -e "${YELLOW}⚠️  Running as $(whoami), some checks may fail${NC}"
    echo ""
fi

# 1. Check configuration
echo -e "${BLUE}1. Configuration Status${NC}"
echo "-------------------"
if [ -f "$HOME/.local/share/signage_simple_player/shared_preferences.json" ]; then
    echo -e "${GREEN}✓ Configuration file exists${NC}"
    echo "Location: $HOME/.local/share/signage_simple_player/shared_preferences.json"
    echo ""
    echo "Content:"
    cat "$HOME/.local/share/signage_simple_player/shared_preferences.json" | python3 -m json.tool 2>/dev/null || cat "$HOME/.local/share/signage_simple_player/shared_preferences.json"
else
    echo -e "${RED}✗ No configuration file found${NC}"
    echo "Run: ./setup_console.py"
fi
echo ""

# 2. Network connectivity
echo -e "${BLUE}2. Network Connectivity${NC}"
echo "-------------------"

# Get backend IP from config if exists
BACKEND_IP=""
if [ -f "$HOME/.local/share/signage_simple_player/shared_preferences.json" ]; then
    BACKEND_IP=$(python3 -c "import json; f=open('$HOME/.local/share/signage_simple_player/shared_preferences.json'); d=json.load(f); print(d.get('flutter.backend_ip', ''))" 2>/dev/null || echo "")
fi

if [ -n "$BACKEND_IP" ]; then
    echo "Backend IP: $BACKEND_IP"
    echo ""
    
    # Ping test
    echo "Testing ping to backend..."
    if ping -c 3 -W 2 "$BACKEND_IP" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is reachable via ping${NC}"
    else
        echo -e "${RED}✗ Cannot ping backend${NC}"
    fi
    echo ""
    
    # Discovery service test
    echo "Testing Discovery Service (port 8006)..."
    if curl -s --connect-timeout 5 "http://$BACKEND_IP:8006/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Discovery service is responding${NC}"
        curl -s "http://$BACKEND_IP:8006/health" | python3 -m json.tool 2>/dev/null || echo ""
    else
        echo -e "${RED}✗ Discovery service not responding${NC}"
    fi
    echo ""
    
    # Media service test
    echo "Testing Media Service (port 8000)..."
    if curl -s --connect-timeout 5 "http://$BACKEND_IP:8000/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Media service is responding${NC}"
    else
        echo -e "${RED}✗ Media service not responding${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No backend IP configured${NC}"
fi
echo ""

# 3. Process status
echo -e "${BLUE}3. Process Status${NC}"
echo "-------------------"
if pgrep -f "signage_simple_player" > /dev/null; then
    echo -e "${GREEN}✓ Signage application is running${NC}"
    echo ""
    echo "Process details:"
    ps aux | grep signage_simple_player | grep -v grep
    echo ""
    echo "Memory usage:"
    ps aux | grep signage_simple_player | grep -v grep | awk '{print "  RSS: " $6/1024 " MB, VSZ: " $5/1024 " MB"}'
else
    echo -e "${RED}✗ Signage application is NOT running${NC}"
fi
echo ""

# 4. System resources
echo -e "${BLUE}4. System Resources${NC}"
echo "-------------------"
echo "Memory:"
free -h
echo ""
echo "CPU Load:"
uptime
echo ""
echo "Disk Space:"
df -h | grep -E '(Filesystem|/dev/root|/dev/mmcblk)'
echo ""

# 5. Display environment
echo -e "${BLUE}5. Display Environment${NC}"
echo "-------------------"
echo "DISPLAY variable: ${DISPLAY:-not set}"
echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-not set}"
echo ""
if command -v xrandr &> /dev/null && [ -n "$DISPLAY" ]; then
    echo "Connected displays:"
    xrandr --query | grep " connected"
else
    echo -e "${YELLOW}⚠️  Cannot query display info (xrandr not available or DISPLAY not set)${NC}"
fi
echo ""

# 6. Application logs
echo -e "${BLUE}6. Recent Application Logs${NC}"
echo "-------------------"

# Check systemd logs if service exists
if systemctl list-units --full -all | grep -q "ppl-meta-signage.service"; then
    echo "Systemd service logs (last 50 lines):"
    sudo journalctl -u ppl-meta-signage -n 50 --no-pager
else
    echo -e "${YELLOW}⚠️  Systemd service not configured${NC}"
fi
echo ""

# Check for Flutter logs in common locations
if [ -d "$HOME/.local/share/signage_simple_player" ]; then
    echo "Application data directory:"
    ls -lah "$HOME/.local/share/signage_simple_player/"
fi
echo ""

# 7. Network ports
echo -e "${BLUE}7. Network Ports${NC}"
echo "-------------------"
echo "Checking if HTTP server port (8009) is open..."
if lsof -i :8009 &> /dev/null; then
    echo -e "${GREEN}✓ Port 8009 is in use (HTTP server running)${NC}"
    lsof -i :8009
else
    echo -e "${YELLOW}⚠️  Port 8009 is not in use (HTTP server may not have started)${NC}"
fi
echo ""

# 8. Flutter/Graphics libraries
echo -e "${BLUE}8. Dependencies Check${NC}"
echo "-------------------"

# Check for required libraries
echo "Checking graphics libraries..."
if ldconfig -p | grep -q libEGL; then
    echo -e "${GREEN}✓ libEGL found${NC}"
else
    echo -e "${RED}✗ libEGL not found${NC}"
fi

if ldconfig -p | grep -q libGLESv2; then
    echo -e "${GREEN}✓ libGLESv2 found${NC}"
else
    echo -e "${RED}✗ libGLESv2 not found${NC}"
fi
echo ""

# 9. Crash reports
echo -e "${BLUE}9. Crash/Error Logs${NC}"
echo "-------------------"
if [ -f "$HOME/.local/share/signage_simple_player/crash_reports.log" ]; then
    echo "Recent crash reports:"
    tail -n 50 "$HOME/.local/share/signage_simple_player/crash_reports.log"
else
    echo "No crash reports found"
fi
echo ""

# 10. Summary and recommendations
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Summary & Recommendations${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Configuration check
if [ ! -f "$HOME/.local/share/signage_simple_player/shared_preferences.json" ]; then
    echo -e "${RED}❌ ISSUE: No configuration found${NC}"
    echo "   Solution: Run ./setup_console.py"
    echo ""
fi

# Backend connectivity
if [ -n "$BACKEND_IP" ]; then
    if ! curl -s --connect-timeout 5 "http://$BACKEND_IP:8006/health" > /dev/null 2>&1; then
        echo -e "${RED}❌ ISSUE: Cannot connect to backend services${NC}"
        echo "   Solution: Check if backend services are running on $BACKEND_IP"
        echo "   - Discovery service should be on port 8006"
        echo "   - Media service should be on port 8000"
        echo ""
    fi
fi

# Memory check
AVAILABLE_MEM=$(free | grep Mem | awk '{print int($7/1024)}')
if [ "$AVAILABLE_MEM" -lt 100 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Low memory (${AVAILABLE_MEM}MB available)${NC}"
    echo "   Solution: Restart the device or close other applications"
    echo ""
fi

# Process check
if ! pgrep -f "signage_simple_player" > /dev/null; then
    echo -e "${YELLOW}⚠️  Application is not running${NC}"
    echo "   This could be normal if you're troubleshooting after a crash"
    echo ""
fi

echo -e "${GREEN}Diagnostics complete${NC}"
echo ""
echo "To save this output to a file:"
echo "  ./diagnose.sh > diagnostics_$(date +%Y%m%d_%H%M%S).txt"
