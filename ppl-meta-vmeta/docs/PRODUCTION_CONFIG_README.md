# Production Configuration Guide - PPL Meta vmeta Service

**Version:** 1.0.0  
**Date:** November 1, 2025  
**Status:** Ready for Production Deployment

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Files](#configuration-files)
3. [Installation](#installation)
4. [Configuration Walkthrough](#configuration-walkthrough)
5. [Deployment](#deployment)
6. [Rollback](#rollback)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## Overview

This document provides comprehensive guidance for deploying and configuring the vmeta service in production environments, including the MVR-People system.

### Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (Port 443)                      │
│  • SSL/TLS Termination                                       │
│  • Rate Limiting                                             │
│  • Caching                                                   │
└───────────────────┬─────────────────────────────────────────┘
                    │
    ┌───────────────┴────────────────┐
    │                                │
┌───▼───────────────────┐  ┌────────▼────────────────────────┐
│  vmeta.service        │  │  vmeta-mvr-worker.service       │
│  (Main API)           │  │  (Background Processor)         │
│  • Port: 8008         │  │  • MVR Auto-matching            │
│  • Workers: 4         │  │  • Orphan Detection             │
│  • Resources: 2GB/4CPU│  │  • Resources: 1GB/2CPU          │
└───────┬───────────────┘  └─────────┬───────────────────────┘
        │                            │
        └────────────┬───────────────┘
                     │
            ┌────────▼─────────┐
            │  PostgreSQL      │
            │  + pgvector      │
            │  (ppl_meta)      │
            └──────────────────┘
```

### Key Features

- **High Availability:** Auto-restart, health monitoring, graceful shutdown
- **Security:** SSL/TLS, rate limiting, systemd hardening
- **Scalability:** Worker processes, connection pooling, caching
- **Observability:** Structured logging, metrics, health checks
- **Automation:** Deployment scripts, rollback capability

---

## Configuration Files

### File Structure

```
ppl-meta-vmeta/
├── .env.production.template        # Environment variables template
├── config/
│   ├── production.yaml             # Main configuration
│   └── logging.yaml                # Logging configuration
├── systemd/
│   ├── vmeta.service               # Main service unit
│   └── vmeta-mvr-worker.service    # Worker service unit
├── nginx/
│   └── vmeta.conf                  # Nginx reverse proxy
├── scripts/
│   ├── deploy_vmeta.sh             # Deployment automation
│   └── rollback_vmeta.sh           # Rollback automation
└── secrets/
    └── README.md                   # Secrets management guide
```

### Configuration Hierarchy

1. **Environment Variables** (.env.production)
   - Runtime configuration
   - Secrets (database passwords, API keys)
   - Feature flags

2. **YAML Configuration** (config/production.yaml)
   - Service settings
   - Database connection pooling
   - MVR-People configuration
   - Security policies

3. **Systemd Units** (systemd/*.service)
   - Process management
   - Resource limits
   - Auto-restart policies

4. **Nginx Configuration** (nginx/vmeta.conf)
   - Reverse proxy
   - SSL/TLS
   - Rate limiting

---

## Installation

### Prerequisites

**System Requirements:**
- OS: Ubuntu 20.04+ or RHEL 8+
- Python: 3.11+
- PostgreSQL: 14+ with pgvector extension
- Nginx: 1.18+
- Systemd: 245+

**Hardware Requirements:**
- CPU: 4+ cores
- RAM: 8GB+ (4GB vmeta + 2GB worker + 2GB system)
- Disk: 50GB+ SSD
- Network: 100Mbps+

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    postgresql-14 \
    postgresql-14-pgvector \
    nginx \
    git \
    curl

# Create service user
sudo useradd -r -s /bin/false vmeta

# Create directories
sudo mkdir -p /opt/ppl-meta/vmeta
sudo mkdir -p /etc/ppl-meta
sudo mkdir -p /var/log/ppl-meta/vmeta
sudo mkdir -p /var/backups/ppl-meta/vmeta

# Set ownership
sudo chown -R vmeta:vmeta /opt/ppl-meta/vmeta
sudo chown -R vmeta:vmeta /var/log/ppl-meta/vmeta
```

### Step 2: Clone Repository

```bash
cd /opt/ppl-meta
sudo -u vmeta git clone https://github.com/your-org/ppl-meta-code.git
cd ppl-meta-code/ppl-meta-vmeta
```

### Step 3: Create Virtual Environment

```bash
sudo -u vmeta python3.11 -m venv venv
sudo -u vmeta venv/bin/pip install --upgrade pip
sudo -u vmeta venv/bin/pip install -r requirements.txt
```

### Step 4: Configure Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE ppl_meta_prod;
CREATE USER vmeta_prod WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE ppl_meta_prod TO vmeta_prod;

# Enable pgvector extension
\c ppl_meta_prod
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Configuration Walkthrough

### Environment Configuration

**1. Copy template:**
```bash
sudo cp .env.production.template /etc/ppl-meta/vmeta.env
```

**2. Edit configuration:**
```bash
sudo nano /etc/ppl-meta/vmeta.env
```

**3. Set critical values:**

```bash
# Environment
VMETA_ENV=production
VMETA_DEBUG=false
LOG_LEVEL=INFO

# Database (UPDATE THESE)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ppl_meta_prod
DB_USER=vmeta_prod
DB_PASSWORD=<SECURE_PASSWORD>  # From secrets manager

# MVR-People
MVR_ENABLED=true
MVR_AUTO_CREATE=true
MVR_SIMILARITY_THRESHOLD=0.85

# Security (UPDATE THESE)
JWT_SECRET_KEY=<GENERATE_SECURE_KEY>
API_RATE_LIMIT_PER_MINUTE=100

# External Services (UPDATE THESE)
ORCHESTRATOR_URL=http://localhost:8002
DISCOVERY_URL=http://localhost:8006
```

**4. Secure the file:**
```bash
sudo chown vmeta:vmeta /etc/ppl-meta/vmeta.env
sudo chmod 600 /etc/ppl-meta/vmeta.env
```

### YAML Configuration

**Location:** `config/production.yaml`

**Key Sections to Review:**

```yaml
# Adjust workers based on CPU cores
service:
  server:
    workers: 4  # Recommended: num_cores

# Tune connection pool
database:
  pool:
    min_size: 10
    max_size: 50  # Adjust based on load

# MVR-People settings
mvr_people:
  auto_merge: false  # Manual approval recommended
  matching:
    similarity_threshold: 0.85  # Tune based on accuracy needs
```

### Systemd Configuration

**1. Install service files:**
```bash
sudo cp systemd/vmeta.service /etc/systemd/system/
sudo cp systemd/vmeta-mvr-worker.service /etc/systemd/system/
```

**2. Update paths if needed:**
```bash
sudo nano /etc/systemd/system/vmeta.service
# Verify WorkingDirectory, EnvironmentFile, ExecStart paths
```

**3. Reload systemd:**
```bash
sudo systemctl daemon-reload
```

### Nginx Configuration

**1. Install configuration:**
```bash
sudo cp nginx/vmeta.conf /etc/nginx/sites-available/vmeta
sudo ln -s /etc/nginx/sites-available/vmeta /etc/nginx/sites-enabled/
```

**2. Configure SSL certificates:**

**Option A: Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d vmeta.yourdomain.com
```

**Option B: Manual certificates**
```bash
# Update paths in vmeta.conf
ssl_certificate /etc/ssl/certs/vmeta.crt;
ssl_certificate_key /etc/ssl/private/vmeta.key;
```

**3. Test configuration:**
```bash
sudo nginx -t
```

**4. Reload nginx:**
```bash
sudo systemctl reload nginx
```

---

## Deployment

### Automated Deployment

**Using deployment script:**
```bash
cd /opt/ppl-meta/ppl-meta-code/ppl-meta-vmeta
sudo ./scripts/deploy_vmeta.sh --env production --version v1.0.0
```

**Script performs:**
1. ✅ Prerequisites check
2. ✅ Configuration backup
3. ✅ Service shutdown
4. ✅ Code update (git pull/checkout)
5. ✅ Dependency installation
6. ✅ Database migrations
7. ✅ Systemd service installation
8. ✅ Service startup
9. ✅ Health check validation
10. ✅ Status report

### Manual Deployment

**1. Stop services:**
```bash
sudo systemctl stop vmeta-mvr-worker.service
sudo systemctl stop vmeta.service
```

**2. Backup configuration:**
```bash
BACKUP_DIR="/var/backups/ppl-meta/vmeta/$(date +%Y%m%d_%H%M%S)"
sudo mkdir -p "$BACKUP_DIR"
sudo cp /etc/ppl-meta/vmeta.env "$BACKUP_DIR/"
sudo cp config/production.yaml "$BACKUP_DIR/"
```

**3. Update code:**
```bash
cd /opt/ppl-meta/ppl-meta-code
sudo -u vmeta git pull origin main
# OR checkout specific version:
# sudo -u vmeta git checkout v1.0.0
```

**4. Install dependencies:**
```bash
cd ppl-meta-vmeta
sudo -u vmeta venv/bin/pip install -r requirements.txt
```

**5. Run migrations:**
```bash
# Example using Alembic (if configured)
sudo -u vmeta venv/bin/alembic upgrade head
```

**6. Start services:**
```bash
sudo systemctl start vmeta.service
sudo systemctl start vmeta-mvr-worker.service
```

**7. Verify health:**
```bash
curl http://localhost:8008/health | jq
```

---

## Rollback

### Automated Rollback

**Using rollback script:**
```bash
# Rollback to latest backup
sudo ./scripts/rollback_vmeta.sh

# Rollback to specific backup
sudo ./scripts/rollback_vmeta.sh 20251101_120000
```

**Script performs:**
1. ✅ Finds backup (latest or specified)
2. ✅ Confirms rollback with user
3. ✅ Stops services
4. ✅ Restores configuration
5. ✅ Reverts code (git reset)
6. ✅ Starts services
7. ✅ Verifies health

### Manual Rollback

**1. Identify backup:**
```bash
ls -la /var/backups/ppl-meta/vmeta/
# Example: 20251101_120000
```

**2. Stop services:**
```bash
sudo systemctl stop vmeta-mvr-worker.service
sudo systemctl stop vmeta.service
```

**3. Restore configuration:**
```bash
BACKUP_DIR="/var/backups/ppl-meta/vmeta/20251101_120000"
sudo cp "$BACKUP_DIR/vmeta.env" /etc/ppl-meta/
sudo cp "$BACKUP_DIR/production.yaml" config/
```

**4. Revert code:**
```bash
cd /opt/ppl-meta/ppl-meta-code
sudo -u vmeta git reset --hard HEAD~1
# OR checkout specific version:
# sudo -u vmeta git checkout v0.9.0
```

**5. Start services:**
```bash
sudo systemctl start vmeta.service
sudo systemctl start vmeta-mvr-worker.service
```

**6. Verify:**
```bash
curl http://localhost:8008/health | jq
```

---

## Monitoring

### Health Checks

**Service health:**
```bash
# Direct service
curl http://localhost:8008/health | jq

# Via nginx
curl https://vmeta.yourdomain.com/health | jq
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-01T12:00:00Z",
  "components": {
    "database": "healthy",
    "mvr_people": "healthy"
  }
}
```

### Service Status

**Systemd status:**
```bash
# Main service
sudo systemctl status vmeta.service

# Worker service
sudo systemctl status vmeta-mvr-worker.service

# Both services
sudo systemctl status vmeta*
```

**Process monitoring:**
```bash
# CPU/Memory usage
ps aux | grep vmeta

# Detailed stats
top -p $(pgrep -f "uvicorn.*vmeta")
```

### Logs

**Real-time logs:**
```bash
# Main service
sudo journalctl -u vmeta.service -f

# Worker service
sudo journalctl -u vmeta-mvr-worker.service -f

# Application logs
sudo tail -f /var/log/ppl-meta/vmeta/vmeta.log

# MVR-specific logs
sudo tail -f /var/log/ppl-meta/vmeta/mvr-people.log
```

**Log analysis:**
```bash
# Errors in last hour
sudo journalctl -u vmeta.service --since "1 hour ago" | grep ERROR

# Performance metrics
sudo grep "performance" /var/log/ppl-meta/vmeta/vmeta.log | tail -n 20
```

### Metrics

**Prometheus metrics endpoint:**
```bash
curl http://localhost:9090/metrics
```

**Key metrics:**
- `vmeta_requests_total` - Total API requests
- `vmeta_request_duration_seconds` - Request latency
- `vmeta_mvr_matches_total` - MVR match operations
- `vmeta_mvr_merges_total` - MVR merge operations
- `vmeta_database_connections_active` - Active DB connections

---

## Troubleshooting

### Service Won't Start

**Check systemd status:**
```bash
sudo systemctl status vmeta.service
sudo journalctl -u vmeta.service -n 50
```

**Common issues:**

1. **Port already in use:**
   ```bash
   sudo lsof -i :8008
   sudo kill -9 <PID>
   ```

2. **Permission denied:**
   ```bash
   sudo chown -R vmeta:vmeta /opt/ppl-meta/vmeta
   sudo chmod -R 750 /opt/ppl-meta/vmeta
   ```

3. **Missing dependencies:**
   ```bash
   sudo -u vmeta venv/bin/pip install -r requirements.txt
   ```

### Database Connection Failed

**Test connection:**
```bash
sudo -u vmeta psql -h localhost -U vmeta_prod -d ppl_meta_prod
```

**Check credentials:**
```bash
sudo -u vmeta cat /etc/ppl-meta/vmeta.env | grep DB_
```

**Verify PostgreSQL:**
```bash
sudo systemctl status postgresql
sudo ss -tlnp | grep 5432
```

### High Memory Usage

**Check current usage:**
```bash
free -h
ps aux --sort=-%mem | head -10
```

**Adjust resource limits:**
```bash
sudo nano /etc/systemd/system/vmeta.service
# Increase MemoryMax if needed
MemoryMax=4G

sudo systemctl daemon-reload
sudo systemctl restart vmeta.service
```

### Slow API Responses

**Check logs for slow queries:**
```bash
sudo grep "slow query" /var/log/ppl-meta/vmeta/vmeta.log
```

**Increase workers:**
```bash
# Edit config/production.yaml
service:
  server:
    workers: 8  # Increase from 4

sudo systemctl restart vmeta.service
```

**Check database performance:**
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Maintenance

### Regular Tasks

**Daily:**
- ✅ Check service health
- ✅ Review error logs
- ✅ Monitor disk space

**Weekly:**
- ✅ Review performance metrics
- ✅ Check backup integrity
- ✅ Update security patches

**Monthly:**
- ✅ Rotate logs manually (if needed)
- ✅ Review resource usage trends
- ✅ Test rollback procedure

**Quarterly:**
- ✅ Rotate secrets (JWT, API keys)
- ✅ Review security configuration
- ✅ Capacity planning

### Log Rotation

**Automatic rotation configured in logging.yaml:**
```yaml
handlers:
  file_main:
    when: midnight
    backupCount: 30  # 30 days retention
```

**Manual cleanup:**
```bash
# Remove logs older than 90 days
find /var/log/ppl-meta/vmeta/ -name "*.log.*" -mtime +90 -delete
```

### Database Maintenance

**Vacuum and analyze:**
```sql
-- Weekly maintenance
VACUUM ANALYZE mvr_people;
VACUUM ANALYZE mvr_face_clusters;
VACUUM ANALYZE mvr_cluster_faces;
```

**Reindex:**
```sql
-- Monthly reindex for performance
REINDEX TABLE mvr_people;
REINDEX INDEX idx_mvr_people_embedding_ivfflat;
```

### Backup Strategy

**Configuration backups:**
- Location: `/var/backups/ppl-meta/vmeta/`
- Frequency: Before each deployment
- Retention: 30 days

**Database backups:**
```bash
# Daily backup
sudo -u postgres pg_dump ppl_meta_prod > /var/backups/ppl-meta/vmeta/db_$(date +%Y%m%d).sql

# Backup with compression
sudo -u postgres pg_dump ppl_meta_prod | gzip > /var/backups/ppl-meta/vmeta/db_$(date +%Y%m%d).sql.gz
```

---

## Contact & Support

**Production Issues:**
- Email: ops-team@example.com
- Slack: #ppl-meta-ops
- On-call: [PagerDuty rotation]

**Security Issues:**
- Email: security@example.com
- PGP Key: [Key ID]

**Documentation:**
- Wiki: https://wiki.example.com/ppl-meta/vmeta
- API Docs: https://vmeta.yourdomain.com/docs

---

## Appendix

### Configuration Checklist

Before production deployment:

- [ ] Environment variables configured in `/etc/ppl-meta/vmeta.env`
- [ ] Secrets properly secured (600 permissions)
- [ ] Database created and user granted permissions
- [ ] pgvector extension enabled
- [ ] Systemd service files installed
- [ ] Nginx configuration installed and tested
- [ ] SSL certificates configured
- [ ] Health checks passing
- [ ] Logs rotating properly
- [ ] Metrics endpoint accessible
- [ ] Backup directory created
- [ ] Deployment script tested in staging
- [ ] Rollback procedure tested
- [ ] Monitoring alerts configured
- [ ] Documentation reviewed

### Common Commands Reference

```bash
# Service management
sudo systemctl start vmeta.service
sudo systemctl stop vmeta.service
sudo systemctl restart vmeta.service
sudo systemctl status vmeta.service

# Logs
sudo journalctl -u vmeta.service -f
sudo tail -f /var/log/ppl-meta/vmeta/vmeta.log

# Health check
curl http://localhost:8008/health | jq

# Deployment
sudo ./scripts/deploy_vmeta.sh --env production

# Rollback
sudo ./scripts/rollback_vmeta.sh

# Configuration test
sudo nginx -t
python -m yaml -c config/production.yaml
```

---

**Document Version:** 1.0.0  
**Last Updated:** November 1, 2025  
**Next Review:** February 1, 2026
