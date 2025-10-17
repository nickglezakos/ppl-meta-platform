#!/bin/bash
# PPL Meta Platform - Services Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# PPL Meta Services Configuration
SERVICES=(
    "ppl-meta-node:8001:User Management"
    "ppl-meta-media:8002:Media Processing"
    "ppl-meta-gateway:8000:API Gateway"
    "ppl-meta-orchestrator:8003:Orchestrator"
    "ppl-meta-cameras:8004:Camera Service"
    "ppl-meta-vision:8005:Vision Service"
    "ppl-meta-discovery:8006:Discovery Service"
)

# Function to start all services
start_all_services() {
    print_status "🚀 Starting all PPL Meta Python services..."
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_config"
        
        if [ -d "$service_name" ] && [ -f "$service_name/src/main.py" ]; then
            print_status "Starting $description ($service_name) on port $port..."
            
            # Activate virtual environment if it exists
            if [ -d "$service_name/venv" ]; then
                cd "$service_name"
                source venv/bin/activate
                nohup python src/main.py > "../logs/${service_name}.log" 2>&1 &
                echo $! > "../pids/${service_name}.pid"
                deactivate
                cd ..
            else
                cd "$service_name"
                nohup python src/main.py > "../logs/${service_name}.log" 2>&1 &
                echo $! > "../pids/${service_name}.pid"
                cd ..
            fi
            
            print_success "$description started ✅"
        else
            print_warning "Skipping $service_name - not found or missing main.py"
        fi
    done
    
    print_success "🎉 All available services started!"
    echo
    echo "📋 Service Status:"
    check_services_status
}

# Function to stop all services
stop_all_services() {
    print_status "🛑 Stopping all PPL Meta Python services..."
    
    # Kill processes by pattern
    pkill -f 'ppl-meta.*python.*main.py' 2>/dev/null || true
    
    # Also kill by PID files if they exist
    if [ -d "pids" ]; then
        for pidfile in pids/*.pid; do
            if [ -f "$pidfile" ]; then
                pid=$(cat "$pidfile")
                kill "$pid" 2>/dev/null || true
                rm -f "$pidfile"
            fi
        done
    fi
    
    print_success "✅ All Python services stopped."
}

# Function to check services status
check_services_status() {
    print_status "🏥 Checking service health..."
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_config"
        
        if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
            print_success "$description (port $port) - ✅ Running"
        else
            print_warning "$description (port $port) - ❌ Not responding"
        fi
    done
}

# Function to start nginx
start_nginx() {
    print_status "🌐 Starting Nginx..."
    
    if command -v nginx >/dev/null 2>&1; then
        if pgrep nginx >/dev/null; then
            print_warning "Nginx is already running"
        else
            sudo nginx
            print_success "✅ Nginx started"
        fi
    else
        print_error "❌ Nginx not installed. Install with: brew install nginx"
        exit 1
    fi
}

# Function to stop nginx
stop_nginx() {
    print_status "🛑 Stopping Nginx..."
    
    if pgrep nginx >/dev/null; then
        sudo nginx -s quit
        print_success "✅ Nginx stopped"
    else
        print_warning "⚠️ Nginx is not running"
    fi
}

# Function to restart all services
restart_all_services() {
    print_status "🔄 Restarting all PPL Meta services..."
    stop_all_services
    sleep 2
    start_all_services
}

# Create necessary directories
mkdir -p logs pids

# Main script logic
case "$1" in
    "start")
        start_all_services
        ;;
    "stop")
        stop_all_services
        ;;
    "restart")
        restart_all_services
        ;;
    "status")
        check_services_status
        ;;
    "nginx-start")
        start_nginx
        ;;
    "nginx-stop")
        stop_nginx
        ;;
    *)
        echo "PPL Meta Platform - Services Management"
        echo "======================================"
        echo
        echo "Usage: $0 {start|stop|restart|status|nginx-start|nginx-stop}"
        echo
        echo "Commands:"
        echo "  start        - Start all PPL Meta Python services"
        echo "  stop         - Stop all PPL Meta Python services"
        echo "  restart      - Restart all PPL Meta Python services"
        echo "  status       - Check status of all services"
        echo "  nginx-start  - Start Nginx web server"
        echo "  nginx-stop   - Stop Nginx web server"
        echo
        echo "Examples:"
        echo "  $0 start     # Start all services"
        echo "  $0 status    # Check which services are running"
        echo "  $0 stop      # Stop all services"
        exit 1
        ;;
esac