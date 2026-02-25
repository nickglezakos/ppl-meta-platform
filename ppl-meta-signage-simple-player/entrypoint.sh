#!/bin/bash
set -e

# Create config directory if it doesn't exist
mkdir -p /root/.local/share/signage_simple_player

# Ensure proper permissions
chmod 700 /root/.local/share/signage_simple_player

# Log startup
echo "🚀 Starting PPL Meta Signage Player..."
echo "📁 Config directory: /root/.local/share/signage_simple_player"

# Check if configuration exists
if [ -f "/root/.local/share/signage_simple_player/shared_preferences.json" ]; then
    echo "✅ Configuration file found"
else
    echo "⚠️  No configuration file found - will show setup screen"
fi

# Start Xvfb (virtual display) in background for headless operation
echo "🖥️ Starting virtual display server..."
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
XVFB_PID=$!
sleep 1

# Export display for the Flutter app
export DISPLAY=:99

# Detect architecture and run appropriate binary
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
    echo "🔧 Running ARM64 build"
    /app/build/linux/arm64/release/bundle/signage_simple_player "$@"
else
    echo "🔧 Running x64 build"
    /app/build/linux/x64/release/bundle/signage_simple_player "$@"
fi

# Kill Xvfb when app exits
kill $XVFB_PID 2>/dev/null || true
