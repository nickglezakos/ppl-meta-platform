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

# Prefer an already-provided display (e.g. compose DISPLAY=:0 on a real screen).
# Only fall back to Xvfb when no usable display is set.
XVFB_PID=""
if [ -z "${DISPLAY:-}" ]; then
    echo "🖥️ No DISPLAY set — starting virtual display server (:99)..."
    Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
    XVFB_PID=$!
    sleep 1
    export DISPLAY=:99
else
    echo "🖥️ Using host display: $DISPLAY"
fi

# On a real display, kiosk-maximize the Flutter window once it appears
# (Android is always edge-to-edge; Linux defaults to a floating window).
# Operators can later press F11 in-app to toggle fullscreen, or Esc/Q to quit.
if [ -n "${DISPLAY:-}" ] && [ "${DISPLAY}" != ":99" ] && command -v wmctrl >/dev/null 2>&1; then
    (
        for _ in 1 2 3 4 5 6 7 8 9 10 12 15 20; do
            sleep 1
            if wmctrl -lx 2>/dev/null | grep -qi signage_simple_player; then
                wmctrl -xr signage_simple_player.signage_simple_player -b add,fullscreen 2>/dev/null \
                    || wmctrl -r signage_simple_player -b add,fullscreen 2>/dev/null \
                    || true
                break
            fi
        done
    ) &
fi

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
if [ -n "$XVFB_PID" ]; then
    kill "$XVFB_PID" 2>/dev/null || true
fi
