# PPL Meta Platform - Storage Volume Management Guide

This guide provides comprehensive documentation for the Docker volume management system implemented to resolve ISSUE-021. The solution includes automated backup/restore, monitoring, and permission management for all platform storage volumes.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Installation & Setup](#installation--setup)
5. [Usage Examples](#usage-examples)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

## Overview

The PPL Meta Platform manages the following critical storage volumes:

### Critical Volumes (Require daily backups)
- **postgres_data**: PostgreSQL database data
- **redis_data**: Redis cache and session storage
- **media-storage**: Media files and uploads
- **user-data**: User profiles and configuration

### Infrastructure Volumes (Weekly backups recommended)
- **orchestrator-data**: Orchestrator service data
- **consul_data**: Service discovery data
- **prometheus_data**: Metrics and monitoring data
- **grafana_data**: Dashboard configurations
- **jaeger_data**: Distributed tracing data
- **wireguard_config**: VPN mesh configuration

## Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Volume Manager    │    │  Backup Automation  │    │ Monitoring Service  │
│                     │    │                     │    │                     │
│ • Backup/Restore    │────│ • Scheduled Backups │────│ • Prometheus Metrics│
│ • Permission Fixing │    │ • Cleanup/Retention │    │ • REST API          │
│ • Health Checks     │    │ • Notifications     │    │ • Alerting          │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │
           ┌─────────────────────────────────────────────────────┐
           │                Docker Volumes                        │
           │  postgres_data  redis_data  media-storage  ...      │
           └─────────────────────────────────────────────────────┘
```

## Components

### 1. Volume Manager (`shared/storage/volume_manager.py`)

Primary utility for volume operations:

**Features:**
- Automated backup/restore with metadata tracking
- Service-specific permission fixing
- Volume usage monitoring
- Health checks and reporting
- Prometheus metrics generation

**Key Methods:**
- `backup_volume(volume_name, tag)`: Create compressed backup
- `restore_volume(volume_name, backup_file)`: Restore from backup
- `fix_volume_permissions(volume_name)`: Fix permission issues
- `health_check()`: Comprehensive health assessment
- `generate_monitoring_metrics()`: Prometheus metrics

### 2. Backup Automation (`shared/storage/backup_automation.sh`)

Scheduled backup automation script:

**Features:**
- Automated daily/weekly backup scheduling
- Configurable retention policies
- Email and Slack notifications
- Health monitoring and alerts
- Systemd timer integration

**Configuration Variables:**
- `BACKUP_SCHEDULE`: Cron schedule (default: daily at 2 AM)
- `RETENTION_DAYS`: Backup retention period (default: 30 days)
- `MIN_BACKUPS`: Minimum backups to keep (default: 5)
- `NOTIFICATION_EMAIL`: Email for alerts
- `SLACK_WEBHOOK`: Slack webhook URL

### 3. Monitoring Service (`shared/storage/monitoring_service.py`)

Real-time storage monitoring service:

**Features:**
- Prometheus metrics endpoint (`/metrics`)
- REST API for storage queries (`/api/volumes`, `/api/health`)
- Real-time usage monitoring
- Configurable alerting thresholds

**Endpoints:**
- `GET /metrics`: Prometheus metrics
- `GET /api/volumes`: Volume status summary
- `GET /api/volumes/{name}`: Individual volume details
- `GET /api/health`: Health check endpoint

### 4. Permission Fixer (`shared/storage/permission_fixer.py`)

Volume permission diagnosis and repair:

**Features:**
- Automated permission issue detection
- Service-specific permission fixes
- Integration with Docker container contexts
- Comprehensive reporting

## Installation & Setup

### Prerequisites

```bash
# Ensure Docker and Docker Compose are installed
docker --version
docker-compose --version

# Python 3.8+ required for utilities
python3 --version

# Install required Python packages
pip3 install aiohttp prometheus_client psutil
```

### 1. Basic Setup

```bash
# Create backup directory
sudo mkdir -p /var/backups/ppl-volumes
sudo chown $USER:$USER /var/backups/ppl-volumes

# Make scripts executable
chmod +x shared/storage/backup_automation.sh
chmod +x shared/storage/volume_manager.py
chmod +x shared/storage/permission_fixer.py
```

### 2. Environment Configuration

Create `.env` file in project root:

```bash
# Storage Management Configuration
BACKUP_DIR=/var/backups/ppl-volumes
RETENTION_DAYS=30
MIN_BACKUPS=5

# Notification Configuration
NOTIFICATION_EMAIL=admin@example.com
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Monitoring Configuration
STORAGE_MONITORING_PORT=8090
PROMETHEUS_METRICS_ENABLED=true
```

### 3. Systemd Timer Setup (Production)

```bash
# Copy systemd files
sudo cp shared/storage/systemd/ppl-backup.service /etc/systemd/system/
sudo cp shared/storage/systemd/ppl-backup.timer /etc/systemd/system/

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable ppl-backup.timer
sudo systemctl start ppl-backup.timer

# Check timer status
sudo systemctl status ppl-backup.timer
```

## Usage Examples

### Basic Volume Operations

```bash
# List all platform volumes
./shared/storage/volume_manager.py list

# Create backup of critical volume
./shared/storage/volume_manager.py backup postgres_data --tag daily-backup

# List available backups
./shared/storage/volume_manager.py list --backups --volume postgres_data

# Restore from backup
./shared/storage/volume_manager.py restore postgres_data /var/backups/ppl-volumes/postgres_data_20250107_020000.tar.gz

# Fix volume permissions
./shared/storage/volume_manager.py fix-permissions postgres_data

# Perform health check
./shared/storage/volume_manager.py health

# Generate monitoring metrics
./shared/storage/volume_manager.py metrics
```

### Automated Backup Operations

```bash
# Run manual backup of all critical volumes
./shared/storage/backup_automation.sh --mode manual --volumes critical

# Test notification system
./shared/storage/backup_automation.sh --test-notifications

# Cleanup old backups
./shared/storage/backup_automation.sh --cleanup-only

# Generate backup report
./shared/storage/backup_automation.sh --report
```

### Monitoring Service

```bash
# Start monitoring service
python3 shared/storage/monitoring_service.py --port 8090

# Query volume status via API
curl http://localhost:8090/api/volumes

# Get specific volume details
curl http://localhost:8090/api/volumes/postgres_data

# Check health endpoint
curl http://localhost:8090/api/health

# Get Prometheus metrics
curl http://localhost:8090/metrics
```

## Monitoring & Alerting

### Prometheus Metrics

The system exposes the following metrics for monitoring:

```
# Volume existence and health
ppl_volume_exists{volume="postgres_data"} 1
ppl_volume_usage_percent{volume="postgres_data"} 45.2

# Backup metrics
ppl_volume_backup_count{volume="postgres_data"} 7
ppl_volume_backup_age_hours{volume="postgres_data"} 12.5

# System metrics
ppl_volume_total 10
ppl_volume_critical_total 4
ppl_backup_count_total 35
```

### Grafana Dashboard

Import the provided dashboard configuration:

```bash
# Import dashboard
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @shared/storage/grafana/ppl-storage-dashboard.json
```

### Alert Rules

Configure Prometheus alert rules in `prometheus.yml`:

```yaml
groups:
- name: ppl_storage
  rules:
  - alert: VolumeUsageHigh
    expr: ppl_volume_usage_percent > 90
    labels:
      severity: warning
    annotations:
      summary: "Volume {{ $labels.volume }} usage is high"
      
  - alert: BackupAge
    expr: ppl_volume_backup_age_hours > 48
    labels:
      severity: critical
    annotations:
      summary: "Volume {{ $labels.volume }} backup is too old"
```

## Troubleshooting

### Common Issues

#### 1. Volume Permission Errors

**Symptoms:**
- Service containers fail to start
- Permission denied errors in logs
- Database initialization failures

**Solution:**
```bash
# Diagnose permission issues
./shared/storage/permission_fixer.py diagnose postgres_data

# Auto-fix permissions
./shared/storage/volume_manager.py fix-permissions postgres_data

# Manual fix for PostgreSQL
docker run --rm -v postgres_data:/data postgres:15-alpine \
  sh -c 'chown -R postgres:postgres /data && chmod -R 700 /data'
```

#### 2. Backup Failures

**Symptoms:**
- Backup commands fail
- Insufficient disk space
- Corrupted backup files

**Solution:**
```bash
# Check disk space
df -h /var/backups/ppl-volumes

# Test backup process
./shared/storage/volume_manager.py backup postgres_data --tag test

# Verify backup integrity
tar -tzf /var/backups/ppl-volumes/postgres_data_test.tar.gz | head -10

# Clean up old backups
./shared/storage/volume_manager.py cleanup --days 7
```

#### 3. Monitoring Service Issues

**Symptoms:**
- Metrics endpoint not responding
- Missing volume data
- API errors

**Solution:**
```bash
# Check service status
ps aux | grep monitoring_service

# Test metrics endpoint
curl -v http://localhost:8090/metrics

# Check volume accessibility
docker volume ls | grep ppl

# Restart monitoring service
pkill -f monitoring_service.py
python3 shared/storage/monitoring_service.py --port 8090 &
```

### Log Analysis

```bash
# Check Docker volume driver logs
journalctl -u docker | grep volume

# Monitor backup automation logs
tail -f /var/log/ppl-backup.log

# Check service container logs
docker-compose -f docker-compose.minimal.yml logs postgres
docker-compose -f docker-compose.minimal.yml logs redis
```

## Production Deployment

### Security Considerations

1. **Backup Encryption**: Encrypt sensitive backups
```bash
# Create encrypted backup
gpg --symmetric --cipher-algo AES256 backup_file.tar.gz
```

2. **Access Control**: Restrict backup directory access
```bash
sudo chmod 700 /var/backups/ppl-volumes
sudo chown root:backup-group /var/backups/ppl-volumes
```

3. **Network Security**: Secure monitoring endpoints
```bash
# Use reverse proxy with authentication
nginx -> monitoring_service (localhost only)
```

### High Availability Setup

1. **Remote Backup Storage**:
```bash
# Sync to remote storage
rsync -av /var/backups/ppl-volumes/ backup-server:/backups/ppl-platform/
```

2. **Multi-region Replication**:
```bash
# Configure volume replication
docker volume create --driver rexray postgres_data_replica
```

3. **Monitoring Redundancy**:
```bash
# Deploy monitoring service on multiple nodes
docker service create --replicas 3 ppl-storage-monitor
```

### Performance Optimization

1. **Backup Compression**: Optimize backup size
```bash
# Use better compression
tar -I 'gzip -9' -cf backup.tar.gz /data
```

2. **Parallel Backups**: Process multiple volumes
```bash
# Parallel backup execution
./backup_automation.sh --parallel --workers 4
```

3. **Incremental Backups**: Reduce backup time
```bash
# Implement rsync-based incremental backups
rsync -av --link-dest=../last-backup /volume-data/ /backup-new/
```

## CI/CD Integration

### Automated Testing

```yaml
# .github/workflows/storage-test.yml
name: Storage Management Tests
on: [push, pull_request]

jobs:
  test-volume-management:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Test backup/restore
      run: |
        ./shared/storage/volume_manager.py backup test-volume
        ./shared/storage/volume_manager.py restore test-volume backup.tar.gz
    - name: Test monitoring
      run: |
        python3 shared/storage/monitoring_service.py --test
```

### Deployment Validation

```bash
# Pre-deployment checks
./shared/storage/volume_manager.py health
./shared/storage/backup_automation.sh --validate

# Post-deployment verification
./shared/storage/volume_manager.py metrics | grep ppl_volume_exists
```

This comprehensive storage management system ensures robust data protection, monitoring, and operational efficiency for the PPL Meta Platform.
