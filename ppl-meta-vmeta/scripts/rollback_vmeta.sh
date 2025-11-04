#!/bin/bash
# ============================================================================
# PPL Meta vmeta Service - Rollback Script
# ============================================================================
#
# Quick rollback to previous deployment
#
# Usage:
#   ./rollback_vmeta.sh [backup_timestamp]
#
# If no backup timestamp provided, will use the most recent backup
#
# Version: 1.0.0
# Date: November 1, 2025
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BACKUP_PATH="/var/backups/ppl-meta/vmeta"
CONFIG_PATH="/etc/ppl-meta"
DEPLOY_PATH="/opt/ppl-meta/vmeta"

SERVICE_MAIN="vmeta.service"
SERVICE_WORKER="vmeta-mvr-worker.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

find_latest_backup() {
    local latest_backup=$(ls -td "$BACKUP_PATH"/config_* 2>/dev/null | head -1)
    
    if [[ -z "$latest_backup" ]]; then
        log_error "No backups found in $BACKUP_PATH"
        exit 1
    fi
    
    echo "$latest_backup"
}

list_available_backups() {
    log_info "Available backups:"
    ls -lh "$BACKUP_PATH" | grep "^d" | awk '{print $NF, "(" $6, $7, $8 ")"}'
}

confirm_rollback() {
    local backup_dir=$1
    
    log_warning "You are about to rollback vmeta service"
    log_info "Backup to restore: $backup_dir"
    echo ""
    
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
}

stop_services() {
    log_info "Stopping services..."
    
    systemctl stop "$SERVICE_WORKER" 2>/dev/null || true
    systemctl stop "$SERVICE_MAIN" 2>/dev/null || true
    
    sleep 3
    
    log_success "Services stopped"
}

restore_configuration() {
    local backup_dir=$1
    
    log_info "Restoring configuration from backup..."
    
    # Restore environment file
    if [[ -f "$backup_dir/vmeta.env" ]]; then
        cp "$backup_dir/vmeta.env" "$CONFIG_PATH/"
        log_info "Restored vmeta.env"
    fi
    
    # Restore systemd service files
    if [[ -f "$backup_dir/$SERVICE_MAIN" ]]; then
        cp "$backup_dir/$SERVICE_MAIN" "/etc/systemd/system/"
        log_info "Restored $SERVICE_MAIN"
    fi
    
    if [[ -f "$backup_dir/$SERVICE_WORKER" ]]; then
        cp "$backup_dir/$SERVICE_WORKER" "/etc/systemd/system/"
        log_info "Restored $SERVICE_WORKER"
    fi
    
    # Reload systemd
    systemctl daemon-reload
    
    log_success "Configuration restored"
}

rollback_code() {
    log_info "Rolling back code..."
    
    cd "$DEPLOY_PATH"
    
    # Get previous git commit/tag
    local previous_commit=$(git rev-parse HEAD~1)
    
    log_info "Rolling back to commit: $previous_commit"
    git reset --hard "$previous_commit"
    
    log_success "Code rolled back"
}

start_services() {
    log_info "Starting services..."
    
    systemctl start "$SERVICE_MAIN"
    sleep 5
    systemctl start "$SERVICE_WORKER"
    
    log_success "Services started"
}

verify_rollback() {
    log_info "Verifying rollback..."
    
    # Check service status
    if ! systemctl is-active --quiet "$SERVICE_MAIN"; then
        log_error "Main service failed to start"
        return 1
    fi
    
    # Check health endpoint
    sleep 10
    
    if curl -sf http://localhost:8008/health > /dev/null; then
        log_success "Rollback verified - service is healthy"
        return 0
    else
        log_error "Health check failed after rollback"
        return 1
    fi
}

# ----------------------------------------------------------------------------
# Main Rollback Flow
# ----------------------------------------------------------------------------

main() {
    local backup_timestamp=${1:-""}
    local backup_dir=""
    
    log_info "Starting vmeta service rollback"
    echo ""
    
    check_root
    
    # Determine which backup to use
    if [[ -z "$backup_timestamp" ]]; then
        backup_dir=$(find_latest_backup)
        log_info "Using latest backup: $backup_dir"
    else
        backup_dir="$BACKUP_PATH/config_$backup_timestamp"
        if [[ ! -d "$backup_dir" ]]; then
            log_error "Backup not found: $backup_dir"
            echo ""
            list_available_backups
            exit 1
        fi
    fi
    
    echo ""
    confirm_rollback "$backup_dir"
    
    # Execute rollback
    stop_services
    restore_configuration "$backup_dir"
    rollback_code
    start_services
    
    if verify_rollback; then
        echo ""
        log_success "Rollback completed successfully!"
        echo ""
        
        # Show status
        systemctl status "$SERVICE_MAIN" --no-pager | head -10
    else
        echo ""
        log_error "Rollback completed but service health check failed"
        log_info "Check logs: journalctl -u $SERVICE_MAIN -n 50"
        exit 1
    fi
}

# Show help if requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# //'
    echo ""
    list_available_backups
    exit 0
fi

# Run main rollback
main "$@"
