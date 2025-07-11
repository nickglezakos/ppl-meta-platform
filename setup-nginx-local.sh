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
NGINX_CONFIG="$SCRIPT_DIR/nginx-local-dev.conf"

# Check if config file exists
if [[ ! -f "$NGINX_CONFIG" ]]; then
    echo "❌ Nginx configuration file not found: $NGINX_CONFIG"
    exit 1
fi

echo "✅ Nginx configuration found: $NGINX_CONFIG"

# Test the configuration
echo "🧪 Testing nginx configuration..."
if sudo nginx -t -c "$NGINX_CONFIG"; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    exit 1
fi

# Check if any nginx processes are running
if pgrep nginx > /dev/null; then
    echo "⚠️  Nginx is already running. Stopping existing processes..."
    sudo nginx -s quit 2>/dev/null || sudo pkill nginx
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
if sudo nginx -c "$NGINX_CONFIG"; then
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
    echo "📋 To stop nginx: sudo nginx -s quit"
    echo "🔄 To reload config: sudo nginx -s reload"
else
    echo "❌ Failed to start nginx"
    exit 1
fi
