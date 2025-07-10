#!/bin/bash
"""
PPL Meta Platform - Automated Volume Backup Script

This script provides automated backup scheduling for Docker volumes
with proper error handling, notifications, and health checks.

Author: PPL Meta Platform Team
Version: 1.0.0
Date: 2025-07-10
"""

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOLUME_MANAGER="$SCRIPT_DIR/../storage/volume_manager.py"
LOG_FILE="$SCRIPT_DIR/backup_automation.log"
LOCK_FILE="/tmp/ppl_backup.lock"
NOTIFICATION_EMAIL="${BACKUP_NOTIFICATION_EMAIL:-}"
SLACK_WEBHOOK="${BACKUP_SLACK_WEBHOOK:-}"

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Check if another backup is running
check_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid
        pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "ERROR" "Another backup process is running (PID: $pid)"
            exit 1
        else
            log "WARNING" "Stale lock file found, removing"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

# Clean up function
cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

# Send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Email notification
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        echo "$message" | mail -s "PPL Meta Platform Backup $status" "$NOTIFICATION_EMAIL" 2>/dev/null || true
    fi
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK" ]; then
        local color="good"
        [ "$status" = "FAILED" ] && color="danger"
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"title\":\"PPL Meta Platform Backup $status\",\"text\":\"$message\"}]}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
}

# Check if volume manager is available
check_prerequisites() {
    if [ ! -f "$VOLUME_MANAGER" ]; then
        log "ERROR" "Volume manager not found: $VOLUME_MANAGER"
        exit 1
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        log "ERROR" "Python 3 is required but not installed"
        exit 1
    fi
    
    if ! command -v docker >/dev/null 2>&1; then
        log "ERROR" "Docker is required but not installed"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log "ERROR" "Docker daemon is not running"
        exit 1
    fi
}

# Backup specific volume
backup_volume() {
    local volume_name="$1"
    local backup_name="${2:-}"
    
    log "INFO" "Starting backup for volume: $volume_name"
    
    if [ -n "$backup_name" ]; then
        python3 "$VOLUME_MANAGER" backup "$volume_name" --name "$backup_name"
    else
        python3 "$VOLUME_MANAGER" backup "$volume_name"
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "INFO" "Successfully backed up volume: $volume_name"
        return 0
    else
        log "ERROR" "Failed to backup volume: $volume_name (exit code: $exit_code)"
        return 1
    fi
}

# Backup all configured volumes
backup_all() {
    log "INFO" "Starting backup for all configured volumes"
    
    local start_time
    start_time=$(date +%s)
    
    python3 "$VOLUME_MANAGER" backup-all > /tmp/backup_all.log 2>&1
    local exit_code=$?
    
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        log "INFO" "All volume backups completed successfully in ${duration}s"
        send_notification "SUCCESS" "All PPL Meta Platform volume backups completed successfully in ${duration} seconds."
        return 0
    else
        log "ERROR" "Some volume backups failed (exit code: $exit_code)"
        local error_details
        error_details=$(tail -20 /tmp/backup_all.log)
        send_notification "FAILED" "PPL Meta Platform volume backup failed. Error details: $error_details"
        return 1
    fi
}

# Clean up old backups
cleanup_backups() {
    local retention_days="${1:-30}"
    
    log "INFO" "Cleaning up backups older than $retention_days days"
    
    python3 "$VOLUME_MANAGER" cleanup --days "$retention_days" > /tmp/cleanup.log 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        local removed_count
        removed_count=$(grep -o "Removed [0-9]\+ old backup" /tmp/cleanup.log | grep -o "[0-9]\+" || echo "0")
        log "INFO" "Cleanup completed: removed $removed_count old backup(s)"
        return 0
    else
        log "ERROR" "Backup cleanup failed (exit code: $exit_code)"
        return 1
    fi
}

# Health check for volumes
health_check() {
    log "INFO" "Performing volume health check"
    
    python3 "$VOLUME_MANAGER" monitor > /tmp/health_check.log 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        # Check for alerts
        local alert_count
        alert_count=$(grep -c "\"alerts\":" /tmp/health_check.log || echo "0")
        
        if [ "$alert_count" -gt 0 ]; then
            log "WARNING" "Volume health check completed with alerts"
            local alerts
            alerts=$(grep -A 10 "\"alerts\":" /tmp/health_check.log || echo "No alert details available")
            send_notification "WARNING" "PPL Meta Platform volume health check found issues: $alerts"
        else
            log "INFO" "Volume health check completed successfully - no issues found"
        fi
        return 0
    else
        log "ERROR" "Volume health check failed (exit code: $exit_code)"
        send_notification "FAILED" "PPL Meta Platform volume health check failed."
        return 1
    fi
}

# Install backup service (systemd timer)
install_service() {
    log "INFO" "Installing backup service"
    
    # Create systemd service file
    sudo tee /etc/systemd/system/ppl-backup.service > /dev/null <<EOF
[Unit]
Description=PPL Meta Platform Volume Backup
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=root
ExecStart=$SCRIPT_DIR/backup_automation.sh backup-all
StandardOutput=journal
StandardError=journal
EOF

    # Create systemd timer file
    sudo tee /etc/systemd/system/ppl-backup.timer > /dev/null <<EOF
[Unit]
Description=PPL Meta Platform Volume Backup Timer
Requires=ppl-backup.service

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
EOF

    # Enable and start the timer
    sudo systemctl daemon-reload
    sudo systemctl enable ppl-backup.timer
    sudo systemctl start ppl-backup.timer
    
    log "INFO" "Backup service installed and started"
    sudo systemctl status ppl-backup.timer
}

# Uninstall backup service
uninstall_service() {
    log "INFO" "Uninstalling backup service"
    
    sudo systemctl stop ppl-backup.timer 2>/dev/null || true
    sudo systemctl disable ppl-backup.timer 2>/dev/null || true
    sudo rm -f /etc/systemd/system/ppl-backup.service
    sudo rm -f /etc/systemd/system/ppl-backup.timer
    sudo systemctl daemon-reload
    
    log "INFO" "Backup service uninstalled"
}

# Show help
show_help() {
    cat <<EOF
PPL Meta Platform - Automated Volume Backup Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    backup <volume_name> [backup_name]  Backup a specific volume
    backup-all                          Backup all configured volumes
    cleanup [retention_days]            Clean up old backups (default: 30 days)
    health-check                        Perform volume health check
    install-service                     Install automated backup service
    uninstall-service                   Uninstall automated backup service
    status                             Show backup service status
    help                               Show this help message

Environment Variables:
    BACKUP_NOTIFICATION_EMAIL          Email address for notifications
    BACKUP_SLACK_WEBHOOK              Slack webhook URL for notifications

Examples:
    $0 backup postgres_data
    $0 backup-all
    $0 cleanup 7
    $0 health-check
    $0 install-service

EOF
}

# Show service status
show_status() {
    echo "=== PPL Meta Platform Backup Service Status ==="
    echo
    
    if systemctl is-active --quiet ppl-backup.timer 2>/dev/null; then
        echo "✅ Backup timer is active"
        systemctl status ppl-backup.timer --no-pager -l
    else
        echo "❌ Backup timer is not active"
    fi
    
    echo
    echo "=== Recent Backup Logs ==="
    journalctl -u ppl-backup.service --no-pager -l -n 20 2>/dev/null || echo "No recent logs found"
    
    echo
    echo "=== Volume Status ==="
    python3 "$VOLUME_MANAGER" list --usage 2>/dev/null || echo "Failed to get volume status"
}

# Main function
main() {
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        backup)
            if [ $# -lt 1 ]; then
                echo "Error: Volume name required"
                echo "Usage: $0 backup <volume_name> [backup_name]"
                exit 1
            fi
            check_lock
            check_prerequisites
            backup_volume "$@"
            ;;
        backup-all)
            check_lock
            check_prerequisites
            backup_all
            ;;
        cleanup)
            check_prerequisites
            cleanup_backups "${1:-30}"
            ;;
        health-check)
            check_prerequisites
            health_check
            ;;
        install-service)
            install_service
            ;;
        uninstall-service)
            uninstall_service
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Error: Unknown command '$command'"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
