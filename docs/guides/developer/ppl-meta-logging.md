# PPL Meta Platform - Logging Configuration

This document describes where each ppl-meta microservice logs its output.

## Logging Overview

Most services use Python's `RotatingFileHandler` with the following configuration:
- **Max file size**: 10 MB
- **Backup count**: 5 files (log rotation)
- **Log level**: Typically INFO or DEBUG

---

## Service Logging Locations

### 1. **ppl-meta-cameras**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/logs/ppl-meta-cameras.log`
- **Log directory**: `ppl-meta-cameras/logs/`
- **Status**: ✅ Active (4.5 MB as of Jan 5, 2026)
- **Contains**: Camera detection, recording sessions, RTSP/USB camera operations, face detection triggers, media uploads

### 2. **ppl-meta-media**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-media.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ✅ Active (173 KB as of Jan 5, 2026)
- **Contains**: Media uploads, storage operations, file processing, thumbnail generation

### 3. **ppl-meta-node**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-node.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ⚠️ Old (last updated Nov 19)
- **Contains**: User authentication, face data, settings, API operations

### 4. **ppl-meta-orchestrator**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-orchestrator.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ⚠️ Old (last updated Nov 19)
- **Contains**: Service orchestration, Enhanced Logic V2 coordination, cross-service workflows

### 5. **ppl-meta-vision**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vision.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ✅ Active (8.7 MB as of Jan 5, 2026)
- **Contains**: Face detection, bulk processing, computer vision operations, person object creation

### 6. **ppl-meta-vmeta**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ✅ Active (1.7 MB as of Jan 5, 2026)
- **Contains**: Cross-video tracking, batch processing, continuous pipeline, MVR person creation, polling events

### 7. **ppl-meta-gateway**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-gateway.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ⚠️ Old (last updated Nov 19)
- **Contains**: API gateway operations, request routing, authentication

### 8. **ppl-meta-discovery**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-discovery.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ⚠️ Old (last updated Nov 19)
- **Contains**: Service discovery, health checks, service registration

### 9. **ppl-meta-bootcore**
- **Log file**: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-bootcore.log`
- **Log directory**: `logs/` (workspace root)
- **Status**: ⚠️ Old (last updated Nov 19)
- **Contains**: Core boot operations, initialization

---

## Log File Patterns

### Standard Services (using workspace root logs/)
```
/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-{service}.log
```
**Services**: media, node, orchestrator, vision, vmeta, gateway, discovery, bootcore

### Services with Local Logs Directory
```
/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-{service}/logs/ppl-meta-{service}.log
```
**Services**: cameras

---

## How to Check Logs

### Real-time Monitoring (Tail)
```bash
# Most active services
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vision.log
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/logs/ppl-meta-cameras.log
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-media.log
```

### Search Logs for Specific Events
```bash
# Face detection in cameras service
grep "FACE-DETECTION" /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/logs/ppl-meta-cameras.log

# Batch processing in vmeta
grep "batch\|Batch" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# Recording events in vmeta
grep "recording" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# Vision service face detection
grep "Enhanced Logic V2\|bulk.*process" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vision.log

# Recent errors (last 100 lines)
grep -i "error\|exception\|failed" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-*.log | tail -100
```

### Check Logs by Time
```bash
# Today's activity (replace with current date)
grep "2026-01-05" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# Recent activity (last 200 lines)
tail -200 /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vision.log
```

---

## Important Note: Some Services May Use stdout

Some services (especially when run with uvicorn --reload) may output logs to **stdout/terminal** instead of log files. If a log file shows old timestamps but the service is active, check the terminal where the service was started.

### Services That May Log to stdout:
- **gateway** (uvicorn)
- **orchestrator** (uvicorn)
- **node** (may use both file + stdout)

To capture stdout logs, redirect when starting:
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 > /path/to/logs/service-stdout.log 2>&1 &
```

---

## Continuous Pipeline Log Tracking

For debugging the **continuous individuals and MVR pipeline** (Faces → Individuals → MVR People):

1. **Camera upload & face detection trigger**: `ppl-meta-cameras/logs/ppl-meta-cameras.log`
2. **Face detection execution**: `logs/ppl-meta-vision.log`
3. **Recording events & polling**: `logs/ppl-meta-vmeta.log`
4. **Batch processing & individuals creation**: `logs/ppl-meta-vmeta.log`
5. **MVR person creation**: `logs/ppl-meta-vmeta.log`

### Typical Log Flow for a Recorded Video:
```
[cameras] → Upload segment → Trigger face detection
[vision]  → Enhanced Logic V2 → Detect faces → Store in database
[vmeta]   → Poll discovers video with faces → Accumulate to batch
[vmeta]   → Batch threshold reached → Trigger cross-video tracking
[vmeta]   → Create individuals → Link MVR people
```

---

## Log Rotation

All services use `RotatingFileHandler` with:
- **maxBytes**: 10 MB per file
- **backupCount**: 5 backup files

When a log file reaches 10 MB:
- Current log renamed to `.log.1`
- Previous `.log.1` → `.log.2`, etc.
- Maximum 5 backup files kept (`.log.1` through `.log.5`)
- Oldest backup (`.log.5`) deleted when rotation occurs

---

## Last Updated
January 5, 2026
