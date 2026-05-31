#!/bin/bash

# PPL Meta Platform - Start All Services Script
# This script starts all services with proper logging and process management

# NOTE: Do NOT use set -e here, as services need to start independently
# If one service fails, others should still attempt to start

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting PPL Meta Platform Services..."
echo "================================================"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local start_command=$3
    local port=$4
    
    echo "Starting $service_name on port $port..."
    
    # Check if directory exists
    if [ ! -d "$PROJECT_ROOT/$service_dir" ]; then
        echo "  ⚠️  Warning: Directory not found: $service_dir"
        return 1
    fi
    
    # Change to service directory and start with nohup (survives terminal close)
    cd "$PROJECT_ROOT/$service_dir" || return 1
    
    # Start service using nohup (immune to hangups)
    nohup bash -c "$start_command" > "$PROJECT_ROOT/logs/$service_name.log" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "$PROJECT_ROOT/pids/$service_name.pid"
    
    # Return to project root
    cd "$PROJECT_ROOT"
    
    # Give service a moment to start
    sleep 1
    
    # Check if process is still running
    if kill -0 "$pid" 2>/dev/null; then
        echo "  ✓ Started (PID: $pid)"
        return 0
    else
        echo "  ✗ Failed to start (check logs: logs/$service_name.log)"
        return 1
    fi
}

# Create pids directory
mkdir -p "$PROJECT_ROOT/pids"

# Start Discovery Service
start_service \
    "ppl-meta-discovery" \
    "ppl-meta-discovery/src" \
    "source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8006 --reload" \
    "8006"

# Start Node Service
start_service \
    "ppl-meta-node" \
    "ppl-meta-node" \
    "source $PROJECT_ROOT/scripts/load-presence-runtime-env.sh && source venv/bin/activate && PYTHONPATH=$PROJECT_ROOT/ppl-meta-node python src/main.py" \
    "8001"

# Start Media Service
start_service \
    "ppl-meta-media" \
    "ppl-meta-media" \
    "source venv/bin/activate && PYTHONPATH=$PROJECT_ROOT/ppl-meta-media python src/main.py" \
    "8000"

# Start Gateway Service
start_service \
    "ppl-meta-gateway" \
    "ppl-meta-gateway/src" \
    "source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8080 --reload" \
    "8080"

# Start Orchestrator Service
start_service \
    "ppl-meta-orchestrator" \
    "ppl-meta-orchestrator/src" \
    "source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8002 --reload" \
    "8002"

# Start Vision Service
start_service \
    "ppl-meta-vision" \
    "ppl-meta-vision" \
    "source venv/bin/activate && python src/main.py" \
    "8003"

# Start Cameras Service
start_service \
    "ppl-meta-cameras" \
    "ppl-meta-cameras" \
    "set -a && source .env && set +a && source $PROJECT_ROOT/scripts/load-presence-runtime-env.sh && PYTHONPATH=$PROJECT_ROOT/ppl-meta-cameras $PROJECT_ROOT/ppl-meta-cameras/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload" \
    "8005"

# Start Bootcore Service
start_service \
    "ppl-meta-bootcore" \
    "ppl-meta-bootcore/src" \
    "source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8007 --reload" \
    "8007"

# Start VMeta Service
start_service \
    "ppl-meta-vmeta" \
    "ppl-meta-vmeta" \
    "source venv/bin/activate && cd src && PYTHONPATH=$PROJECT_ROOT/ppl-meta-vmeta/src uvicorn main:app --host 0.0.0.0 --port 8008 --reload" \
    "8008"

# Start Presence Service
start_service \
    "ppl-meta-presence" \
    "ppl-meta-presence/src" \
    "source $PROJECT_ROOT/scripts/load-presence-runtime-env.sh && python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8011 --reload" \
    "8011"

echo ""
echo "================================================"
echo "✅ All services started successfully!"
echo ""
echo "📋 Service Status:"
echo "  • Discovery Service:    http://localhost:8006/health"
echo "  • Node Service:         http://localhost:8001/api/v1/health"
echo "  • Media Service:        http://localhost:8000/health"
echo "  • Gateway Service:      http://localhost:8080/health"
echo "  • Orchestrator Service: http://localhost:8002/health"
echo "  • Vision Service:       http://localhost:8003/health"
echo "  • Cameras Service:      http://localhost:8005/health"
echo "  • Bootcore Service:     http://localhost:8007/health"
echo "  • VMeta Service:        http://localhost:8008/health"
echo "  • Presence Service:     http://localhost:8011/health"
echo ""
echo "📝 Logs are being written to: $PROJECT_ROOT/logs/"
echo "🔍 To view logs: tail -f $PROJECT_ROOT/logs/<service-name>.log"
echo "🛑 To stop all services: ./scripts/stop-all-services.sh"
echo ""
