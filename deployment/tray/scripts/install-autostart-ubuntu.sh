#!/usr/bin/env bash
# Install EyeNet tray autostart (.desktop) for the current user.
set -euo pipefail

TRAY_BIN="${1:?usage: $0 /path/to/eyenet-tray /path/to/tray.json}"
CONFIG="${2:?usage: $0 /path/to/eyenet-tray /path/to/tray.json}"

mkdir -p "$HOME/.config/autostart"
DESKTOP="$HOME/.config/autostart/eyenet-tray.desktop"
cat >"$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=EyeNet Tray
Comment=EyeNet platform status and control
Exec=${TRAY_BIN} ${CONFIG}
Icon=applications-system
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF
chmod 644 "$DESKTOP"
echo "Autostart: $DESKTOP"

if command -v gtk-launch >/dev/null 2>&1 || true; then
  nohup "$TRAY_BIN" "$CONFIG" >/dev/null 2>&1 &
  echo "Launched EyeNet tray (pid $!)"
fi
