#!/bin/bash

# ================================================================
# Phase 1 Deployment Script
# PPL Meta Platform - Enhanced Person Detection System
# ================================================================

set -e  # Exit on error

echo "🚀 PPL Meta Phase 1 Deployment Script"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-ppl_meta}
DB_USER=${DB_USER:-ppl_user}
DB_PASSWORD=${DB_PASSWORD:-ppl_password}
API_PORT=${API_PORT:-8010}

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        return 1
    fi
    return 0
}

# ================================================================
# Step 1: Environment Validation
# ================================================================

log_info "Step 1: Validating environment..."

# Check required commands
REQUIRED_COMMANDS=("python3" "pip3" "psql")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if check_command $cmd; then
        log_success "$cmd is available"
    else
        log_error "Required command $cmd not found"
        exit 1
    fi
done

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log_info "Python version: $PYTHON_VERSION"

# ================================================================
# Step 2: Database Setup
# ================================================================

log_info "Step 2: Setting up Phase 1 database..."

# Check if PostgreSQL is running
if ! pg_isready -h $DB_HOST -p $DB_PORT &> /dev/null; then
    log_error "PostgreSQL is not running on $DB_HOST:$DB_PORT"
    log_info "Please start PostgreSQL and ensure it's accessible"
    exit 1
fi

log_success "PostgreSQL is running on $DB_HOST:$DB_PORT"

# Test database connection
log_info "Testing database connection..."
export PGPASSWORD=$DB_PASSWORD
if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" &> /dev/null; then
    log_success "Database connection successful"
else
    log_warning "Database connection failed. Attempting to create database..."
    
    # Try to create database
    if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" &> /dev/null; then
        log_success "Database $DB_NAME created"
    else
        log_error "Failed to create database. Please create it manually:"
        log_error "  createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME"
        exit 1
    fi
fi

# Check for pgvector extension
log_info "Checking pgvector extension..."
if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT * FROM pg_extension WHERE extname='vector';" | grep -q vector; then
    log_success "pgvector extension is installed"
else
    log_warning "pgvector extension not found. Attempting to install..."
    if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION vector;" &> /dev/null; then
        log_success "pgvector extension installed"
    else
        log_error "Failed to install pgvector extension"
        log_error "Please install pgvector manually or ensure user has CREATE permissions"
        exit 1
    fi
fi

# Deploy database schema
log_info "Deploying Phase 1 database schema..."
SCHEMA_FILE="database/phase1_database_schema.sql"
if [ -f "$SCHEMA_FILE" ]; then
    if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$SCHEMA_FILE" &> /dev/null; then
        log_success "Database schema deployed successfully"
    else
        log_error "Failed to deploy database schema"
        exit 1
    fi
else
    log_error "phase1_database_schema.sql not found at $SCHEMA_FILE"
    exit 1
fi

# ================================================================
# Step 3: Python Dependencies
# ================================================================

log_info "Step 3: Installing Python dependencies..."

# Create virtual environment if it doesn't exist
if [ ! -d "phase1_venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv phase1_venv
    log_success "Virtual environment created"
fi

# Activate virtual environment
source phase1_venv/bin/activate
log_info "Virtual environment activated"

# Upgrade pip
pip install --upgrade pip

# Install core dependencies
log_info "Installing core dependencies..."
pip install fastapi uvicorn asyncpg python-multipart

# Install computer vision dependencies
log_info "Installing computer vision dependencies..."
pip install opencv-python pillow numpy

# Install DeepFace for facial embeddings
log_info "Installing DeepFace for facial embeddings..."
pip install deepface

# Install additional dependencies
pip install python-dotenv requests

log_success "All Python dependencies installed"

# ================================================================
# Step 4: Configuration
# ================================================================

log_info "Step 4: Creating configuration files..."

# Create .env file
cat > .env << EOF
# Phase 1 Database Configuration
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# Phase 1 API Configuration
API_HOST=0.0.0.0
API_PORT=$API_PORT

# Phase 1 Vision Configuration
DISTANCE_MULTIPLIER=1000000.0
EMBEDDING_MODEL=Facenet512
DETECTOR_BACKEND=opencv
CONFIDENCE_THRESHOLD=0.5
FRAMES_PER_SECOND=3

# Phase 1 Features
ENABLE_DISTANCE_CALCULATION=true
ENABLE_EMBEDDING_GENERATION=true
ENABLE_ROUTE_TRACKING=true
EOF

log_success "Configuration file .env created"

# ================================================================
# Step 5: System Validation
# ================================================================

log_info "Step 5: Validating Phase 1 system..."

# Check if all Phase 1 files exist
REQUIRED_FILES=(
    "integration/phase1_integration.py"
    "integration/phase1_database_client.py"
    "integration/phase1_enhanced_vision_service.py"
    "integration/phase1_orchestrator_workflow.py"
    "database/phase1_database_schema.sql"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "$file found"
    else
        log_error "Required file $file not found"
        exit 1
    fi
done

# Test database schema
log_info "Validating database schema..."
REQUIRED_TABLES=(
    "persons_lifecycle_master_workflows"
    "person_routes"
    "face_detections"
    "person_objects"
)

for table in "${REQUIRED_TABLES[@]}"; do
    if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1 FROM $table LIMIT 1;" &> /dev/null; then
        log_success "Table $table exists and accessible"
    else
        log_error "Table $table not found or not accessible"
        exit 1
    fi
done

# ================================================================
# Step 6: Start Phase 1 System
# ================================================================

log_info "Step 6: Starting Phase 1 system..."

# Create start script
cat > start_phase1.sh << 'EOF'
#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Activate virtual environment
source phase1_venv/bin/activate

echo "🚀 Starting PPL Meta Phase 1 Enhanced Person Detection System"
echo "📊 Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo "🌐 API Server: http://0.0.0.0:$API_PORT"
echo "📖 API Documentation: http://localhost:$API_PORT/docs"
echo ""

# Start the Phase 1 application
python phase1_integration.py
EOF

chmod +x start_phase1.sh

# Create stop script
cat > stop_phase1.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping PPL Meta Phase 1 system..."

# Kill any running Phase 1 processes
pkill -f "phase1_integration.py" 2>/dev/null || true
pkill -f "uvicorn.*phase1_integration" 2>/dev/null || true

echo "✅ Phase 1 system stopped"
EOF

chmod +x stop_phase1.sh

# Create health check script
cat > health_check_phase1.sh << 'EOF'
#!/bin/bash

if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

API_PORT=${API_PORT:-8010}

echo "🏥 PPL Meta Phase 1 Health Check"
echo "================================"
echo ""

# Check if service is running
if curl -s http://localhost:$API_PORT/health > /dev/null; then
    echo "✅ Phase 1 API is running"
    
    # Get health status
    echo ""
    echo "📊 Health Status:"
    curl -s http://localhost:$API_PORT/health | python3 -m json.tool
    
    echo ""
    echo "📈 System Metrics:"
    curl -s http://localhost:$API_PORT/metrics | python3 -m json.tool
    
else
    echo "❌ Phase 1 API is not running"
    echo "💡 Start it with: ./start_phase1.sh"
fi
EOF

chmod +x health_check_phase1.sh

log_success "Phase 1 management scripts created"

# ================================================================
# Deployment Complete
# ================================================================

echo ""
echo "================================================================"
log_success "🎉 Phase 1 Deployment Completed Successfully!"
echo "================================================================"
echo ""

echo "📋 Phase 1 Features Deployed:"
echo "  ✅ Session-based processing (no duplicate prevention)"
echo "  ✅ 3D distance calculation using autonomous system methodology"
echo "  ✅ 512-dimensional facial embeddings with DeepFace"
echo "  ✅ Person routes tracking with movement analytics"
echo "  ✅ Vector similarity search with pgvector"
echo "  ✅ Spatial analysis and heatmap generation"
echo "  ✅ Master workflow lifecycle management"
echo "  ✅ Complete REST API for all features"
echo ""

echo "🚀 To start Phase 1 system:"
echo "  ./start_phase1.sh"
echo ""

echo "🏥 To check system health:"
echo "  ./health_check_phase1.sh"
echo ""

echo "🛑 To stop Phase 1 system:"
echo "  ./stop_phase1.sh"
echo ""

echo "📖 API Documentation:"
echo "  http://localhost:$API_PORT/docs"
echo ""

echo "🧪 Quick Test:"
echo "  curl -X POST http://localhost:$API_PORT/dev/quick-test"
echo ""

echo "📊 Database Configuration:"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

log_info "Phase 1 deployment complete. You can now start the enhanced person detection system!"

# Optional: Start the system immediately
read -p "🚀 Start Phase 1 system now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting Phase 1 system..."
    ./start_phase1.sh
fi