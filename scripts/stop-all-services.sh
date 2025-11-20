#!/bin/bash

# PPL Meta Platform - Stop All Services Script
# This script stops all running services gracefully

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🛑 Stopping PPL Meta Platform Services..."
echo "================================================"
echo ""

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PROJECT_ROOT/pids/$service_name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo "Stopping $service_name (PID: $pid)..."
            kill $pid 2>/dev/null || true
            rm -f "$pid_file"
            echo "  ✓ Stopped"
        else
            echo "  ⚠ $service_name not running (stale PID file)"
            rm -f "$pid_file"
        fi
    else
        echo "  ℹ No PID file for $service_name"
    fi
}

# Stop all services
stop_service "ppl-meta-discovery"
stop_service "ppl-meta-node"
stop_service "ppl-meta-media"
stop_service "ppl-meta-gateway"
stop_service "ppl-meta-orchestrator"
stop_service "ppl-meta-vision"
stop_service "ppl-meta-cameras"
stop_service "ppl-meta-bootcore"
stop_service "ppl-meta-vmeta"

# Force kill any remaining processes (single pkill is more efficient)
echo ""
echo "Cleaning up any remaining processes..."
pkill -9 -f 'ppl-meta.*python\|ppl-meta.*uvicorn' 2>/dev/null || true

# Clear Python caches ONLY for service directories (not entire project)
echo "Clearing Python caches (service directories only)..."
for service in ppl-meta-node ppl-meta-media ppl-meta-gateway ppl-meta-orchestrator \
               ppl-meta-vision ppl-meta-cameras ppl-meta-discovery ppl-meta-bootcore ppl-meta-vmeta; do
    if [ -d "$PROJECT_ROOT/$service" ]; then
        find "$PROJECT_ROOT/$service" -maxdepth 3 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    fi
done

# Force kill ports (batch processing is more efficient)
echo "Cleaning up ports..."
lsof -ti:8000,8001,8002,8003,8005,8006,8007,8008,8080 2>/dev/null | xargs kill -9 2>/dev/null || true

echo ""
echo "✅ All services stopped!"
echo ""
