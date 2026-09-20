#!/usr/bin/env bash
# Install required systemd unit + timer to re-register EyeNet discovery services.
# Usage (as root or with sudo):
#   INSTALL_DIR=/home/user/eyenet-platform bash install-discovery-reregister-timer.sh
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-}"
if [[ -z "$INSTALL_DIR" ]]; then
  if [[ -d "$HOME/eyenet-platform" ]]; then
    INSTALL_DIR="$HOME/eyenet-platform"
  elif [[ -d /opt/eyenet-platform ]]; then
    INSTALL_DIR=/opt/eyenet-platform
  else
    echo "Set INSTALL_DIR to the EyeNet compose directory" >&2
    exit 1
  fi
fi

SCRIPT="$INSTALL_DIR/reregister-discovery-services.sh"
if [[ ! -f "$SCRIPT" ]]; then
  # Prefer shared bundle next to this script's sibling copy
  HERE="$(cd "$(dirname "$0")" && pwd)"
  if [[ -f "$HERE/../windows-installer/reregister-discovery-services.sh" ]]; then
    cp "$HERE/../windows-installer/reregister-discovery-services.sh" "$SCRIPT"
  elif [[ -f "$HERE/reregister-discovery-services.sh" ]]; then
    cp "$HERE/reregister-discovery-services.sh" "$SCRIPT"
  else
    echo "Missing $SCRIPT" >&2
    exit 1
  fi
fi
chmod +x "$SCRIPT"

UNIT_DIR=/etc/systemd/system
SERVICE=eyenet-discovery-reregister.service
TIMER=eyenet-discovery-reregister.timer

cat >"$UNIT_DIR/$SERVICE" <<EOF
[Unit]
Description=EyeNet discovery service re-register
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$INSTALL_DIR
ExecStart=/bin/bash $SCRIPT
Nice=10
EOF

cat >"$UNIT_DIR/$TIMER" <<EOF
[Unit]
Description=Periodic EyeNet discovery re-register (required)

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
AccuracySec=1min
Persistent=true
Unit=$SERVICE

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now "$TIMER"
systemctl start "$SERVICE" || true
echo "Installed and started $TIMER (boot+2m, every 10m)"
systemctl list-timers "$TIMER" --no-pager || true
