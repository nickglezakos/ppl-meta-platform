#!/bin/bash
# PPL Meta Platform — Start Nginx proxy if not already running
# Usage: bash scripts/start-nginx-if-needed.sh
# Delegates full setup (certs, config test, nginx start) to setup-nginx-local.sh

set -euo pipefail

# Check if nginx is already running
if pgrep -x nginx >/dev/null 2>&1; then
    echo "🌐 Nginx already running — skipping startup"
    exit 0
fi

echo "🌐 Nginx not running — starting via setup-nginx-local.sh..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/setup-nginx-local.sh"