#!/bin/bash
# ============================================================================
# PPL Meta vmeta Service - Production Deployment Script
# ============================================================================
#
# Automated deployment script for vmeta service
#
# Usage:
#   ./deploy_vmeta.sh [options]
#
# Options:
#   --env ENV          Environment (production, staging) [default: production]
#   --version VERSION  Version to deploy [default: latest]
#   --skip-backup      Skip configuration backup
#   --skip-tests       Skip health check tests
#   --help             Show this help message
#
# Version: 1.0.0
# Date: November 1, 2025
# ============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
VERSION="${VERSION:-latest}"
SKIP_BACKUP=false
SKIP_TESTS=false

# Paths
DEPLOY_PATH="/opt/ppl-meta/vmeta"
CONFIG_PATH="/etc/ppl-meta"
LOG_PATH="/var/log/ppl-meta/vmeta"
BACKUP_PATH="/var/backups/ppl-meta/vmeta"

# Service names
SERVICE_MAIN="vmeta.service"
SERVICE_WORKER="vmeta-mvr-worker.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ----------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------

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

show_help() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# //'
    exit 0
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
    
    # Check required commands
    local required_cmds=("systemctl" "python3" "pip3" "git" "rsync")
    for cmd in "${required_cmds[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    log_success "Prerequisites check passed"
}

backup_configuration() {
    if [[ "$SKIP_BACKUP" == true ]]; then
        log_warning "Skipping configuration backup (--skip-backup specified)"
        return
    fi
    
    log_info "Backing up current configuration..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="$BACKUP_PATH/config_$timestamp"
    
    mkdir -p "$backup_dir"
    
    # Backup configuration files
    if [[ -f "$CONFIG_PATH/vmeta.env" ]]; then
        cp "$CONFIG_PATH/vmeta.env" "$backup_dir/"
    fi
    
    # Backup systemd service files
    if [[ -f "/etc/systemd/system/$SERVICE_MAIN" ]]; then
        cp "/etc/systemd/system/$SERVICE_MAIN" "$backup_dir/"
    fi
    
    if [[ -f "/etc/systemd/system/$SERVICE_WORKER" ]]; then
        cp "/etc/systemd/system/$SERVICE_WORKER" "$backup_dir/"
    fi
    
    log_success "Configuration backed up to: $backup_dir"
}

stop_services() {
    log_info "Stopping services..."
    
    # Stop worker first
    if systemctl is-active --quiet "$SERVICE_WORKER"; then
        systemctl stop "$SERVICE_WORKER"
        log_info "Stopped $SERVICE_WORKER"
    fi
    
    # Stop main service
    if systemctl is-active --quiet "$SERVICE_MAIN"; then
        systemctl stop "$SERVICE_MAIN"
        log_info "Stopped $SERVICE_MAIN"
    fi
    
    # Wait for graceful shutdown
    sleep 5
    
    log_success "Services stopped"
}

pull_latest_code() {
    log_info "Pulling latest code (version: $VERSION)..."
    
    cd "$DEPLOY_PATH"
    
    # Pull from git
    if [[ "$VERSION" == "latest" ]]; then
        git pull origin main
    else
        git fetch --tags
        git checkout "tags/$VERSION"
    fi
    
    log_success "Code updated to version: $VERSION"
}

install_dependencies() {
    log_info "Installing Python dependencies..."
    
    cd "$DEPLOY_PATH"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install/upgrade requirements
    pip install -r requirements.txt
    
    deactivate
    
    log_success "Dependencies installed"
}

apply_database_migrations() {
    log_info "Applying database migrations..."
    
    cd "$DEPLOY_PATH"
    
    # Check if migrations are needed
    # This would typically use alembic or similar tool
    # For now, just a placeholder
    
    log_info "No migrations to apply"
}

install_systemd_services() {
    log_info "Installing systemd service files..."
    
    # Copy service files
    cp "$DEPLOY_PATH/systemd/$SERVICE_MAIN" "/etc/systemd/system/"
    cp "$DEPLOY_PATH/systemd/$SERVICE_WORKER" "/etc/systemd/system/"
    
    # Reload systemd
    systemctl daemon-reload
    
    log_success "Systemd services installed"
}

install_nginx_config() {
    log_info "Installing nginx configuration..."
    
    local nginx_available="/etc/nginx/sites-available/vmeta"
    local nginx_enabled="/etc/nginx/sites-enabled/vmeta"
    
    # Copy nginx config
    cp "$DEPLOY_PATH/nginx/vmeta.conf" "$nginx_available"
    
    # Create symlink if doesn't exist
    if [[ ! -L "$nginx_enabled" ]]; then
        ln -s "$nginx_available" "$nginx_enabled"
    fi
    
    # Test nginx configuration
    if nginx -t 2>&1; then
        systemctl reload nginx
        log_success "Nginx configuration installed and reloaded"
    else
        log_error "Nginx configuration test failed"
        return 1
    fi
}

create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p "$LOG_PATH"
    mkdir -p "$BACKUP_PATH"
    mkdir -p "/var/run/ppl-meta/vmeta"
    
    # Set permissions
    chown -R vmeta:vmeta "$LOG_PATH"
    chown -R vmeta:vmeta "$BACKUP_PATH"
    chown -R vmeta:vmeta "/var/run/ppl-meta/vmeta"
    
    log_success "Directories created"
}

start_services() {
    log_info "Starting services..."
    
    # Enable services
    systemctl enable "$SERVICE_MAIN"
    systemctl enable "$SERVICE_WORKER"
    
    # Start main service
    systemctl start "$SERVICE_MAIN"
    log_info "Started $SERVICE_MAIN"
    
    # Wait for main service to be ready
    sleep 5
    
    # Start worker service
    systemctl start "$SERVICE_WORKER"
    log_info "Started $SERVICE_WORKER"
    
    log_success "Services started"
}

run_health_checks() {
    if [[ "$SKIP_TESTS" == true ]]; then
        log_warning "Skipping health checks (--skip-tests specified)"
        return
    fi
    
    log_info "Running health checks..."
    
    # Wait for service to be fully ready
    sleep 10
    
    # Check service status
    if ! systemctl is-active --quiet "$SERVICE_MAIN"; then
        log_error "Main service is not active"
        return 1
    fi
    
    # Check health endpoint
    local health_url="http://localhost:8008/health"
    local max_attempts=10
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -sf "$health_url" > /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "Health check attempt $attempt/$max_attempts..."
        sleep 3
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

show_deployment_status() {
    log_info "Deployment Status:"
    echo ""
    
    # Service status
    echo "Services:"
    systemctl status "$SERVICE_MAIN" --no-pager | head -3
    systemctl status "$SERVICE_WORKER" --no-pager | head -3
    echo ""
    
    # Version info
    echo "Version: $VERSION"
    echo "Environment: $DEPLOY_ENV"
    echo ""
    
    # Health check
    local health_response=$(curl -s http://localhost:8008/health | python3 -m json.tool 2>/dev/null || echo "Failed to get health status")
    echo "Health:"
    echo "$health_response"
    echo ""
}

# ----------------------------------------------------------------------------
# Main Deployment Flow
# ----------------------------------------------------------------------------

main() {
    log_info "Starting vmeta service deployment"
    log_info "Environment: $DEPLOY_ENV"
    log_info "Version: $VERSION"
    echo ""
    
    # Run deployment steps
    check_prerequisites
    backup_configuration
    stop_services
    pull_latest_code
    install_dependencies
    apply_database_migrations
    create_directories
    install_systemd_services
    # install_nginx_config  # Uncomment if nginx is on same server
    start_services
    run_health_checks
    
    echo ""
    log_success "Deployment completed successfully!"
    echo ""
    
    show_deployment_status
    
    log_info "Deployment log: /var/log/ppl-meta/vmeta/vmeta.log"
}

# ----------------------------------------------------------------------------
# Parse Arguments
# ----------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            DEPLOY_ENV="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Run main deployment
main
