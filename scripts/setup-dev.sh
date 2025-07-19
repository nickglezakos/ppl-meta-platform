#!/bin/bash
# PPL Meta Platform - Development Setup Script

set -e

echo "🚀 Setting up PPL Meta Platform development environment..."

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

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    required_version="3.11"
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_warning "Python 3.11+ recommended. Current version: $python_version"
    else
        print_success "Python version: $python_version ✓"
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Some features will not be available."
    else
        print_success "Docker found ✓"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose not found. Infrastructure setup will not be available."
    else
        print_success "Docker Compose found ✓"
    fi
}

# Setup individual service environments
setup_service() {
    local service_path=$1
    local service_name=$(basename "$service_path")
    
    print_status "Setting up $service_name..."
    
    cd "$service_path"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment for $service_name..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies for $service_name..."
        pip install -r requirements.txt
    fi
    
    # Deactivate virtual environment
    deactivate
    
    print_success "$service_name environment ready ✓"
    cd - > /dev/null
}

# Main setup function
main() {
    echo
    echo "╔══════════════════════════════════════╗"
    echo "║      PPL Meta Platform Setup         ║"
    echo "║                                      ║"
    echo "║  🔧 Development Environment Setup    ║"
    echo "╚══════════════════════════════════════╝"
    echo
    
    check_prerequisites
    echo
    
    # Setup services with Python requirements
    services=(
        "ppl-meta-node"
        "ppl-meta-media" 
        "ppl-meta-gateway"
    )
    
    for service in "${services[@]}"; do
        if [ -d "$service" ] && [ -f "$service/requirements.txt" ]; then
            setup_service "$service"
            echo
        else
            print_warning "Skipping $service - directory or requirements.txt not found"
        fi
    done
    
    # Setup service template
    if [ -d "service-template" ]; then
        setup_service "service-template"
        echo
    fi
    
    print_status "Creating development configuration files..."
    
    # Create .env.example for each service if it doesn't exist
    for service in "${services[@]}"; do
        if [ -d "$service" ] && [ ! -f "$service/.env.example" ]; then
            cat > "$service/.env.example" << EOF
# $service Environment Configuration
DEBUG=true
LOG_LEVEL=info
HOST=0.0.0.0
PORT=800X

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/${service}_db

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# External Services
# Add service-specific environment variables here
EOF
            print_status "Created .env.example for $service"
        fi
    done
    
    echo
    print_success "🎉 Development environment setup complete!"
    echo
    echo "📋 Next Steps:"
    echo "   1. Copy .env.example to .env in each service directory"
    echo "   2. Update environment variables in .env files"
    echo "   3. Start infrastructure: docker-compose -f docker-compose.ecosystem.yml up -d"
    echo "   4. Run individual services from their directories"
    echo
    echo "📖 Documentation:"
    echo "   - README.md - Main documentation"
    echo "   - docs/ - Detailed guides"
    echo "   - Each service has its own README.md"
    echo
    echo "🚀 To start a service:"
    echo "   cd ppl-meta-node"
    echo "   source venv/bin/activate"
    echo "   python src/main.py"
    echo
}

# Run main function
main "$@"
