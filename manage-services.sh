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
    "ppl-meta-media:8000:Media Processing"
    "ppl-meta-gateway:8080:API Gateway"
    "ppl-meta-orchestrator:8002:Orchestrator"
    "ppl-meta-cameras:8005:Camera Service"
    "ppl-meta-vision:8003:Vision Service"
    "ppl-meta-discovery:8006:Discovery Service"
)

# Function to start all services
start_all_services() {
    print_status "🚀 Starting all PPL Meta Python services..."
    
    # Ensure nginx is running first so services can reach each other through the proxy
    start_nginx

    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_config"
        
        if [ -d "$service_name" ] && [ -f "$service_name/src/main.py" ]; then
            print_status "Starting $description ($service_name) on port $port..."
            
            # Create logs directory if it doesn't exist
            mkdir -p logs pids
            
            # Activate virtual environment if it exists and start service
            if [ -d "$service_name/venv" ]; then
                cd "$service_name"
                
                # Special handling for different service types
                case "$service_name" in
                    "ppl-meta-node")
                        # Node service needs special Python path handling
                        nohup bash -c "source venv/bin/activate && PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node uvicorn src.main:app --host 0.0.0.0 --port $port --reload" > "../logs/${service_name}.log" 2>&1 &
                        ;;
                    "ppl-meta-media")
                        # Media service uses uvicorn.run() in main.py
                        nohup bash -c "source venv/bin/activate && PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media python src/main.py" > "../logs/${service_name}.log" 2>&1 &
                        ;;
                    "ppl-meta-gateway")
                        # Gateway runs from src directory - need to cd first
                        (cd src && nohup bash -c "source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port $port --reload" > "../../logs/${service_name}.log" 2>&1 & echo $! > "../../pids/${service_name}.pid")
                        # Skip the normal PID saving since we did it above
                        cd ..
                        continue
                        ;;
                    "ppl-meta-orchestrator")
                        # Orchestrator runs from src directory
                        nohup bash -c "source venv/bin/activate && cd src && uvicorn main:app --host 0.0.0.0 --port $port --reload" > "../logs/${service_name}.log" 2>&1 &
                        ;;
                    "ppl-meta-discovery")
                        # Discovery runs from src directory
                        nohup bash -c "source venv/bin/activate && cd src && uvicorn main:app --host 0.0.0.0 --port $port --reload" > "../logs/${service_name}.log" 2>&1 &
                        ;;
                    *)
                        # Default: try python src/main.py first, then uvicorn
                        if grep -q "uvicorn.run\|app.*FastAPI" "$service_name/src/main.py" 2>/dev/null; then
                            nohup bash -c "source venv/bin/activate && python src/main.py" > "../logs/${service_name}.log" 2>&1 &
                        else
                            nohup bash -c "source venv/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port $port --reload" > "../logs/${service_name}.log" 2>&1 &
                        fi
                        ;;
                esac
                
                echo $! > "../pids/${service_name}.pid"
                cd ..
            else
                print_warning "No virtual environment found for $service_name"
                cd "$service_name"
                
                # Fallback without venv
                case "$service_name" in
                    "ppl-meta-node")
                        nohup bash -c "PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node uvicorn src.main:app --host 0.0.0.0 --port $port --reload" > "../logs/${service_name}.log" 2>&1 &
                        ;;
                    *)
                        nohup python src/main.py > "../logs/${service_name}.log" 2>&1 &
                        ;;
                esac
                
                echo $! > "../pids/${service_name}.pid"
                cd ..
            fi
            
            print_success "$description started ✅"
            sleep 1  # Give service time to start
        else
            print_warning "Skipping $service_name - not found or missing main.py"
        fi
    done
    
    print_success "🎉 All available services started!"
    echo
    echo "📋 Service Status:"
    sleep 3  # Give services time to fully start
    check_services_status
}

# Function to stop all services
stop_all_services() {
    print_status "🛑 Stopping all PPL Meta Python services..."
    
    # Kill processes by multiple patterns to catch all variations
    pkill -f 'ppl-meta.*uvicorn' 2>/dev/null || true
    pkill -f 'ppl-meta.*python.*main.py' 2>/dev/null || true
    pkill -f 'ppl-meta.*python.*src/main.py' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8001' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8000' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8080' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8002' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8003' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8005' 2>/dev/null || true
    pkill -f 'uvicorn.*main:app.*8006' 2>/dev/null || true
    
    # Kill multiprocessing children
    pkill -f 'multiprocessing.*ppl-meta' 2>/dev/null || true
    
    # Give processes time to terminate gracefully
    sleep 2
    
    # Force kill any remaining processes on our service ports
    for port in 8001 8000 8080 8002 8003 8005 8006 8007 8008; do
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    done
    
    # Also kill by PID files if they exist
    if [ -d "pids" ]; then
        for pidfile in pids/*.pid; do
            if [ -f "$pidfile" ]; then
                pid=$(cat "$pidfile")
                kill -9 "$pid" 2>/dev/null || true
                rm -f "$pidfile"
            fi
        done
    fi
    
    # Wait a bit more for ports to be freed
    sleep 1
    
    print_success "✅ All Python services stopped."
}

# Function to check services status
check_services_status() {
    print_status "🏥 Checking service health..."
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name port description <<< "$service_config"
        
        # Use the correct health endpoint for each service
        case "$service_name" in
            "ppl-meta-node")
                health_endpoint="http://localhost:$port/api/v1/health"
                ;;
            *)
                health_endpoint="http://localhost:$port/health"
                ;;
        esac
        
        if curl -s --connect-timeout 3 "$health_endpoint" >/dev/null 2>&1; then
            print_success "$description (port $port) - ✅ Running"
        else
            print_warning "$description (port $port) - ❌ Not responding"
        fi
    done
}

# Function to start nginx
start_nginx() {
    print_status "🌐 Starting Nginx (port 9000)..."
    
    if command -v nginx >/dev/null 2>&1; then
        if pgrep nginx >/dev/null; then
            print_warning "Nginx is already running"
        else
            nginx
            print_success "✅ Nginx started on port 9000"
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
        nginx -s quit
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