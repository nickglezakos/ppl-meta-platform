#!/bin/bash

# PPL Meta Platform - Nginx Local Development Setup Script
# This script helps set up nginx for local development

set -e

echo "🌐 PPL Meta Platform - Nginx Local Development Setup"
echo "=================================================="

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx is not installed."
    echo "Please install nginx first:"
    echo "  macOS: brew install nginx"
    echo "  Ubuntu: sudo apt update && sudo apt install nginx"
    echo "  CentOS/RHEL: sudo yum install nginx"
    exit 1
fi

echo "✅ Nginx is installed: $(nginx -v 2>&1)"

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NGINX_CONFIG="$REPO_ROOT/docs/deployment/nginx/nginx-local-dev.conf"

# Check if config file exists
if [[ ! -f "$NGINX_CONFIG" ]]; then
    echo "❌ Nginx configuration file not found: $NGINX_CONFIG"
    exit 1
fi

echo "✅ Nginx configuration found: $NGINX_CONFIG"

use_brew_service=0
if [[ "$(uname -s)" == "Darwin" ]] && command -v brew &> /dev/null; then
    if brew list nginx &> /dev/null; then
        use_brew_service=1
        echo "✅ Homebrew nginx detected - will use 'brew services' to keep it alive across reboots"
    fi
fi

# Test the configuration
echo "🧪 Testing nginx configuration..."
if [[ $use_brew_service -eq 1 ]]; then
    nginx -t -c "$NGINX_CONFIG"
else
    sudo nginx -t -c "$NGINX_CONFIG"
fi
if [[ $? -eq 0 ]]; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    exit 1
fi

# Check if any nginx processes are running
if pgrep nginx > /dev/null; then
    echo "⚠️  Nginx is already running. Stopping existing processes..."
    nginx -s quit >/dev/null 2>&1 || true
    if [[ $use_brew_service -eq 1 ]]; then
        brew services stop nginx >/dev/null 2>&1 || true
    else
        sudo nginx -s quit 2>/dev/null || sudo pkill nginx
    fi
    sleep 2
fi

# Check if the services are running
echo "🔍 Checking if Python services are running..."

services_running=0

if curl -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "✅ Node Service (8001) is running"
    ((services_running++))
else
    echo "❌ Node Service (8001) is not running"
fi

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Media Service (8000) is running"
    ((services_running++))
else
    echo "❌ Media Service (8000) is not running"
fi

if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Gateway Service (8080) is running"
    ((services_running++))
else
    echo "❌ Gateway Service (8080) is not running"
fi

if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Orchestrator Service (8002) is running"
    ((services_running++))
else
    echo "❌ Orchestrator Service (8002) is not running"
fi

if [[ $services_running -eq 0 ]]; then
    echo "❌ No services are running. Please start the Python services first."
    echo "You can use VS Code task: '🚀 Start All Local Python Services'"
    exit 1
elif [[ $services_running -lt 4 ]]; then
    echo "⚠️  Only $services_running out of 4 services are running."
    echo "Nginx will still start, but some routes may not work."
fi

# Start nginx
echo "🚀 Starting nginx with local development configuration..."
if [[ $use_brew_service -eq 1 ]]; then
    BREW_PREFIX="$(brew --prefix)"
    mkdir -p "$BREW_PREFIX/etc/nginx/servers"
    cp "$NGINX_CONFIG" "$BREW_PREFIX/etc/nginx/nginx.conf"
    if brew services start nginx; then
        sleep 2
    else
        echo "⚠️  Failed to start nginx via brew services; falling back to direct nginx start"
        if nginx -c "$NGINX_CONFIG"; then
            use_brew_service=0
        else
            echo "❌ Failed to start nginx via direct nginx start after brew services failure"
            exit 1
        fi
    fi
elif sudo nginx -c "$NGINX_CONFIG"; then
    :
else
    echo "❌ Failed to start nginx"
    exit 1
fi

if curl -s http://localhost/health > /dev/null 2>&1; then
    echo "✅ Nginx started successfully!"
    echo ""
    echo "🌐 Your services are now available at:"
    echo "   Main Entry Point: http://localhost"
    echo "   API Gateway:      http://localhost/api/"
    echo "   User Management:  http://localhost/api/v1/users/"
    echo "   Authentication:   http://localhost/api/v1/auth/"
    echo "   Media Service:    http://localhost/api/v1/media/"
    echo "   Orchestrator:     http://localhost/api/v1/orchestrate/"
    echo ""
    echo "🏥 Health Checks:"
    echo "   All Services:     http://localhost/health"
    echo "   Node Service:     http://localhost/health/node"
    echo "   Media Service:    http://localhost/health/media"
    echo "   Gateway Service:  http://localhost/health/gateway"
    echo "   Orchestrator:     http://localhost/health/orchestrator"
    echo ""
    if [[ $use_brew_service -eq 1 ]]; then
        echo "📋 To stop nginx: brew services stop nginx"
        echo "🔄 To reload config: nginx -s reload"
        echo "♻️  Auto-start on login/reboot is enabled through Homebrew services"
    else
        echo "📋 To stop nginx: sudo nginx -s quit"
        echo "🔄 To reload config: sudo nginx -s reload"
    fi
else
    echo "❌ Nginx started but /health is not reachable"
    exit 1
fi
