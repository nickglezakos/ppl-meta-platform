#!/bin/bash

# PPL Meta Platform - Nginx Local Development Setup Script
# Starts nginx with LAN-ready HTTPS and auto-generated local certs.

set -euo pipefail

echo "🌐 PPL Meta Platform - Nginx Local Development Setup"
echo "=================================================="

if ! command -v nginx >/dev/null 2>&1; then
    echo "❌ Nginx is not installed."
    echo "Please install nginx first:"
    echo "  macOS: brew install nginx"
    echo "  Ubuntu: sudo apt update && sudo apt install nginx"
    echo "  CentOS/RHEL: sudo yum install nginx"
    exit 1
fi

echo "✅ Nginx is installed: $(nginx -v 2>&1)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NGINX_CONFIG="$REPO_ROOT/docs/deployment/nginx/nginx-local-dev.conf"
CERT_SCRIPT="$REPO_ROOT/scripts/generate-nginx-local-certs.sh"
CERT_META_FILE="/tmp/ppl-meta-local-dev-meta.env"

if [[ ! -f "$NGINX_CONFIG" ]]; then
    echo "❌ Nginx configuration file not found: $NGINX_CONFIG"
    exit 1
fi

if [[ ! -x "$CERT_SCRIPT" ]]; then
    chmod +x "$CERT_SCRIPT"
fi

echo "🔐 Generating local HTTPS cert for current LAN IP..."
"$CERT_SCRIPT" >/dev/null

if [[ -f "$CERT_META_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CERT_META_FILE"
else
    echo "❌ Certificate metadata not found: $CERT_META_FILE"
    exit 1
fi

echo "✅ Nginx configuration found: $NGINX_CONFIG"
echo "✅ HTTPS certificate mode: ${CERT_MODE}"

echo "🧪 Testing nginx configuration..."
if sudo nginx -t -c "$NGINX_CONFIG"; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    exit 1
fi

if pgrep nginx >/dev/null 2>&1; then
    echo "⚠️  Nginx is already running. Stopping existing processes..."
    nginx -s quit >/dev/null 2>&1 || true
    if command -v brew >/dev/null 2>&1 && brew list nginx >/dev/null 2>&1; then
        brew services stop nginx >/dev/null 2>&1 || true
    fi
    sudo nginx -s quit 2>/dev/null || sudo pkill nginx || true
    sleep 2
fi

echo "🔍 Checking if Python services are running..."
services_running=0

if curl -s http://localhost:8001/api/v1/health >/dev/null 2>&1; then
    echo "✅ Node Service (8001) is running"
    ((services_running++)) || true
else
    echo "❌ Node Service (8001) is not running"
fi

if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Media Service (8000) is running"
    ((services_running++)) || true
else
    echo "❌ Media Service (8000) is not running"
fi

if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    echo "✅ Gateway Service (8080) is running"
    ((services_running++)) || true
else
    echo "❌ Gateway Service (8080) is not running"
fi

if curl -s http://localhost:8002/health >/dev/null 2>&1; then
    echo "✅ Orchestrator Service (8002) is running"
    ((services_running++)) || true
else
    echo "❌ Orchestrator Service (8002) is not running"
fi

if [[ "$services_running" -eq 0 ]]; then
    echo "❌ No services are running. Please start the Python services first."
    echo "You can use VS Code task: '🚀 Start All Local Python Services'"
    exit 1
elif [[ "$services_running" -lt 4 ]]; then
    echo "⚠️  Only $services_running out of 4 services are running."
    echo "Nginx will still start, but some routes may not work."
fi

echo "🚀 Starting nginx with local development configuration..."
if sudo nginx -c "$NGINX_CONFIG"; then
    :
else
    echo "❌ Failed to start nginx"
    exit 1
fi

if curl -s http://localhost/health >/dev/null 2>&1; then
    echo "✅ Nginx started successfully!"
    echo ""
    echo "🌐 Your services are now available at:"
    echo "   Main Entry Point (HTTP):  http://localhost"
    echo "   Main Entry Point (HTTPS): https://localhost"
    echo "   LAN HTTPS (current IP):   https://${LAN_IP}"
    echo ""
    echo "🏥 Health Checks:"
    echo "   HTTP:  http://localhost/health"
    echo "   HTTPS: https://localhost/health"
    echo ""
    echo "📋 To stop nginx: sudo nginx -s quit"
    echo "🔄 To reload config: sudo nginx -s reload"
    echo ""
    if [[ "$CERT_MODE" == "mkcert" ]]; then
        echo "📱 iPad trust setup (recommended once):"
        echo "   1) Install mkcert root CA on iPad"
        echo "      - Find it on Mac: mkcert -CAROOT"
        echo "      - Transfer rootCA.pem to iPad and install profile"
        echo "   2) Enable full trust on iPad"
        echo "      Settings > General > About > Certificate Trust Settings"
    else
        echo "⚠️  OpenSSL self-signed cert was used."
        echo "   iPad may show certificate warnings and secure-context features can remain restricted."
        echo "   Install mkcert for trusted local HTTPS: brew install mkcert nss"
    fi
else
    echo "❌ Nginx started but /health is not reachable"
    exit 1
fi
