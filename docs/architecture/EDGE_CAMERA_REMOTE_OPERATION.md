# Edge Camera Remote Operation Architecture

**Date**: February 1, 2026  
**Version**: 2.24.31  
**Target Platform**: Raspberry Pi 5 (Native & Docker)

## Executive Summary

This document analyzes and defines the architecture for remotely operating edge cameras deployed on Raspberry Pi 5 devices, either as native Python applications or Docker containers. It addresses configuration, control, monitoring, and lifecycle management challenges specific to headless IoT deployment scenarios.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Remote Operation Requirements](#remote-operation-requirements)
3. [Architecture Options Comparison](#architecture-options-comparison)
4. [Recommended Solution: Unified Remote Control](#recommended-solution-unified-remote-control)
5. [Implementation Specification](#implementation-specification)
6. [Deployment Scenarios](#deployment-scenarios)
7. [Security Considerations](#security-considerations)
8. [Monitoring & Diagnostics](#monitoring--diagnostics)

---

## Current State Analysis

### Edge Camera Architecture (As-Built)

The edge camera application consists of:

```
ppl-meta-edge-camera/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration management
│   ├── camera/
│   │   ├── capture.py             # OpenCV camera capture
│   │   └── encoder.py             # MJPEG encoding
│   ├── streaming/
│   │   ├── client.py              # HTTP frame upload to platform
│   │   └── buffer.py              # Frame buffering
│   └── platform/
│       ├── registration.py        # Discovery service registration
│       ├── health.py              # Health monitoring
│       └── websocket_client.py    # WebSocket command handler
├── config/
│   └── default.yaml               # YAML configuration
└── requirements.txt
```

### Current Control Mechanisms

**1. WebSocket Commands (Platform → Edge Camera)**
- **Commands**: `connect`, `disconnect`, `start-stream`, `stop-stream`
- **Handler**: `PlatformWebSocketClient` in `websocket_client.py`
- **Connection**: Via Communications Service (port 8009)
- **Limitation**: Platform-initiated only, requires platform availability

**2. Configuration (YAML File)**
```yaml
platform:
  cameras_url: "http://localhost:8005"
  discovery_url: "http://localhost:8006"
  api_key: null  # JWT Bearer token
```
- **Limitation**: Requires file editing and restart for changes
- **Issue**: No remote configuration update capability

**3. Local FastAPI Server**
```python
server:
  host: "0.0.0.0"
  port: 9001
```
- **Current**: Minimal endpoints (health check)
- **Limitation**: Not exposed for remote management

### Comparison with Mobile Camera

The mobile camera (Flutter app) provides:

1. **User Interface** for configuration:
   - Discovery service IP/port input
   - Network prefix configuration
   - Service status display
   
2. **Local Storage** (`SharedPreferences`):
   - Discovery service configuration
   - Device IP prefix
   - Persistent settings across restarts

3. **Auto-Discovery**:
   - Network scanning for services
   - Multi-IP fallback (nginx proxy, direct access)
   - Configuration validation

**Key Difference**: Mobile app has UI for user input; edge camera on RPi5 is headless.

---

## Remote Operation Requirements

### Essential Capabilities

| Capability | Priority | Rationale |
|------------|----------|-----------|
| **Remote Start/Stop** | Critical | Enable/disable camera without physical access |
| **Configuration Update** | Critical | Change platform URLs, credentials without re-deployment |
| **Service Discovery Config** | High | Support network changes, service migrations |
| **Log Access** | High | Troubleshooting without SSH access |
| **Status Monitoring** | High | Health checks, uptime, error tracking |
| **Restart/Reboot** | Medium | Recovery from errors without manual intervention |
| **Firmware/Code Update** | Medium | Deploy fixes and features remotely |
| **Network Diagnostics** | Medium | Test connectivity to platform services |

### Deployment Scenarios

#### Scenario A: Native Python (systemd)
- **Installation**: `pip install` in virtualenv
- **Control**: systemd service unit
- **Logs**: journald
- **Configuration**: YAML file on filesystem

#### Scenario B: Docker Container
- **Installation**: Docker image
- **Control**: Docker daemon
- **Logs**: Docker logging driver
- **Configuration**: Environment variables + volume-mounted YAML

---

## Architecture Options Comparison

### Option 1: Extend Local FastAPI Server (Management API)

**Architecture**:
```
Edge Camera (RPi5)
├── FastAPI Server (port 9001)
│   ├── /health                  [Existing]
│   ├── /api/config              [New] GET/PUT configuration
│   ├── /api/control/start       [New] Start streaming
│   ├── /api/control/stop        [New] Stop streaming
│   ├── /api/control/restart     [New] Restart application
│   ├── /api/logs                [New] Tail logs
│   └── /api/status              [New] Detailed status
└── Authentication: API key or JWT
```

**Pros**:
- ✅ Simple HTTP API (easy to integrate)
- ✅ Works for both native and Docker deployments
- ✅ No external dependencies
- ✅ Direct control (no platform dependency)

**Cons**:
- ❌ Port management (firewall, NAT traversal)
- ❌ Security burden (need authentication, TLS)
- ❌ No centralized management UI
- ❌ Must track RPi IPs manually

---

### Option 2: WebSocket Command Extension (Platform-Centric)

**Architecture**:
```
Platform Communications Service
  ↓ WebSocket Commands
Edge Camera (RPi5)
  └── Extended command handlers:
      - set-config
      - get-logs
      - restart
      - update-discovery
      - network-test
```

**Pros**:
- ✅ Centralized control via platform UI
- ✅ No port exposure on edge devices
- ✅ Existing authentication via platform
- ✅ Bi-directional real-time communication

**Cons**:
- ❌ Requires platform connectivity (no offline control)
- ❌ Single point of failure (platform down = no control)
- ❌ Complex state management

---

### Option 3: Hybrid (Management API + WebSocket)

**Architecture**:
```
┌─────────────────────────────────────────┐
│  Platform (ppl-meta-cameras)            │
│  ├── WebSocket Commands (priority)      │
│  └── REST API to edge /api endpoints    │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Edge Camera (RPi5)                     │
│  ├── WebSocket Client (control channel) │
│  └── FastAPI Management Server          │
│      ├── /api/config                    │
│      ├── /api/control/*                 │
│      └── /api/logs                      │
└─────────────────────────────────────────┘
```

**Pros**:
- ✅ Best of both worlds
- ✅ Fallback control if WebSocket fails
- ✅ Direct access for debugging (e.g., SSH tunnel)
- ✅ Platform UI can proxy to edge API

**Cons**:
- ❌ More complex (two control paths)
- ❌ Potential confusion (which method to use?)

---

### Option 4: Configuration Management System (Ansible/SaltStack)

**Architecture**:
- Central config management server
- Edge devices run agent
- Push/pull configuration updates
- Orchestrate restarts, updates

**Pros**:
- ✅ Enterprise-grade fleet management
- ✅ Idempotent configuration
- ✅ Audit trail

**Cons**:
- ❌ Heavy infrastructure (overkill for small deployments)
- ❌ Steep learning curve
- ❌ Additional services to maintain

---

## Recommended Solution: Unified Remote Control

**Selected Approach**: **Option 3 (Hybrid)** with phased implementation

### Phase 1: Management API (Immediate)
Extend edge camera's FastAPI server with management endpoints.

### Phase 2: Platform Integration (Short-term)
Platform UI consumes edge camera management API.

### Phase 3: WebSocket Enhancement (Medium-term)
Add advanced commands for real-time control.

---

## Implementation Specification

### Phase 1: Edge Camera Management API

#### 1.1 Configuration Management

**Endpoint**: `GET /api/config`
```json
{
  "device": {
    "id": "edge-camera-001",
    "name": "Laptop USB Camera",
    "location": "test-location"
  },
  "platform": {
    "cameras_url": "http://192.168.1.100:8005",
    "discovery_url": "http://192.168.1.100:8006",
    "health_check_interval": 30
  },
  "camera": {
    "device_id": 0,
    "resolution": {"width": 1280, "height": 720},
    "fps": 15
  }
}
```

**Endpoint**: `PUT /api/config`
```json
{
  "platform": {
    "cameras_url": "http://new-ip:8005",
    "discovery_url": "http://new-ip:8006"
  }
}
```
**Action**: Update YAML file, optionally restart

---

**Endpoint**: `POST /api/config/platform`
```json
{
  "discovery_ip": "192.168.1.100",
  "discovery_port": 8006,
  "cameras_port": 8005,
  "use_nginx": false,
  "api_key": "eyJhbGc..."
}
```
**Action**: Similar to mobile camera's `configureFromUserInput()`

---

#### 1.2 Control Operations

**Endpoint**: `POST /api/control/start`
```json
{
  "action": "start_streaming"
}
```
**Response**:
```json
{
  "success": true,
  "message": "Streaming started",
  "streaming_status": "active"
}
```

---

**Endpoint**: `POST /api/control/stop`
```json
{
  "action": "stop_streaming"
}
```

---

**Endpoint**: `POST /api/control/restart`
```json
{
  "scope": "application"  // or "system" for full RPi reboot
}
```
**Actions**:
- `application`: Restart Python process (systemd restart or Docker restart)
- `system`: `sudo reboot` (requires permissions)

---

**Endpoint**: `POST /api/control/reconnect`
```json
{
  "service": "websocket"  // or "registration"
}
```
**Action**: Re-establish WebSocket or re-register with discovery

---

#### 1.3 Diagnostics & Monitoring

**Endpoint**: `GET /api/logs?lines=100&follow=false`
**Response**:
```json
{
  "logs": [
    "2026-02-01 10:00:00 - INFO - Frame captured",
    "2026-02-01 10:00:01 - INFO - Frame uploaded"
  ],
  "total_lines": 100,
  "log_file": "/var/log/edge-camera/app.log"
}
```
**Native**: Read from file or journald
**Docker**: `docker logs edge-camera-001`

---

**Endpoint**: `GET /api/status`
```json
{
  "application": {
    "version": "2.24.31",
    "uptime_seconds": 3600,
    "status": "running"
  },
  "camera": {
    "connected": true,
    "device_id": 0,
    "resolution": "1280x720",
    "fps_actual": 14.8
  },
  "streaming": {
    "active": true,
    "frames_sent": 10523,
    "errors": 0
  },
  "platform": {
    "websocket_connected": true,
    "registered": true,
    "last_heartbeat": "2026-02-01T10:05:00Z"
  },
  "system": {
    "cpu_usage": 25.5,
    "memory_usage": 128,
    "disk_usage": 45,
    "temperature": 52.3
  }
}
```

---

**Endpoint**: `GET /api/diagnostics/network`
```json
{
  "tests": [
    {
      "service": "discovery",
      "url": "http://192.168.1.100:8006/health",
      "reachable": true,
      "latency_ms": 15
    },
    {
      "service": "cameras",
      "url": "http://192.168.1.100:8005/health",
      "reachable": true,
      "latency_ms": 12
    }
  ]
}
```

---

#### 1.4 Authentication

**API Key Header**:
```
Authorization: Bearer <api_key>
```

**Options**:
1. **Shared Secret**: Pre-configured API key in YAML
2. **Platform JWT**: Use platform's JWT token
3. **Edge-Specific Token**: Generate unique token per device

**Recommendation**: Platform JWT (reuse existing auth)

---

### Phase 2: Platform Integration

#### 2.1 Edge Camera Management UI (ppl-meta-frontend)

**New Section**: "Edge Cameras" in camera management

**Features**:
- List all registered edge cameras
- View status (online/offline, streaming status)
- Configure platform URLs
- View logs (real-time tail)
- Start/Stop streaming
- Restart camera application

**Implementation**:
- Flutter web page: `/cameras/edge`
- API calls to platform backend
- Platform proxies to edge camera's management API

---

#### 2.2 Platform Backend (ppl-meta-cameras)

**New Endpoints**:

`POST /api/v1/edge-cameras/{device_id}/config`
```python
async def update_edge_camera_config(device_id: str, config: dict):
    # Get edge camera IP from discovery or database
    edge_ip = await get_edge_camera_ip(device_id)
    
    # Proxy request to edge camera
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"http://{edge_ip}:9001/api/config",
            json=config,
            headers={"Authorization": f"Bearer {get_platform_jwt()}"}
        )
    return response.json()
```

Similar proxies for:
- `/api/v1/edge-cameras/{device_id}/logs`
- `/api/v1/edge-cameras/{device_id}/control/start`
- `/api/v1/edge-cameras/{device_id}/status`

---

### Phase 3: WebSocket Command Extension

**New Commands** (handled by `PlatformWebSocketClient`):

```python
COMMAND_HANDLERS = {
    "connect": handle_connect_command,
    "disconnect": handle_disconnect_command,
    "start-stream": handle_start_stream_command,
    "stop-stream": handle_stop_stream_command,
    # New commands:
    "set-config": handle_set_config_command,
    "get-logs": handle_get_logs_command,
    "restart": handle_restart_command,
    "network-test": handle_network_test_command,
}
```

**Example - Set Config**:
```json
{
  "command": "set-config",
  "params": {
    "platform.cameras_url": "http://new-ip:8005",
    "platform.discovery_url": "http://new-ip:8006"
  }
}
```

**Advantage**: Real-time push from platform (no polling)

---

## Deployment Scenarios

### Scenario A: Native Python with systemd

#### Installation Script

**File**: `install.sh`
```bash
#!/bin/bash
# Edge Camera Installation Script for Raspberry Pi 5

set -e

INSTALL_DIR="/opt/ppl-meta-edge-camera"
USER="edge-camera"
VENV_DIR="$INSTALL_DIR/venv"

# Create dedicated user
sudo useradd -r -s /bin/false $USER || true

# Create installation directory
sudo mkdir -p $INSTALL_DIR
sudo cp -r . $INSTALL_DIR/
sudo chown -R $USER:$USER $INSTALL_DIR

# Create Python virtual environment
sudo -u $USER python3 -m venv $VENV_DIR
sudo -u $USER $VENV_DIR/bin/pip install -r $INSTALL_DIR/requirements.txt

# Create log directory
sudo mkdir -p /var/log/ppl-meta-edge-camera
sudo chown $USER:$USER /var/log/ppl-meta-edge-camera

# Install systemd service
sudo cp systemd/edge-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable edge-camera.service

echo "✅ Installation complete!"
echo "Configure: sudo nano $INSTALL_DIR/config/default.yaml"
echo "Start: sudo systemctl start edge-camera"
```

---

#### Systemd Service Unit

**File**: `systemd/edge-camera.service`
```ini
[Unit]
Description=PPL Meta Edge Camera Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=edge-camera
Group=edge-camera
WorkingDirectory=/opt/ppl-meta-edge-camera
Environment="PATH=/opt/ppl-meta-edge-camera/venv/bin"
ExecStart=/opt/ppl-meta-edge-camera/venv/bin/python src/main.py

# Restart on failure
Restart=on-failure
RestartSec=10s

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=edge-camera

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

---

#### Remote Control Commands

**Start**:
```bash
curl -X POST http://rpi5.local:9001/api/control/start \
  -H "Authorization: Bearer <api_key>"
```

**Get Logs**:
```bash
# Via API
curl http://rpi5.local:9001/api/logs?lines=50

# Via journald (SSH)
ssh pi@rpi5.local "sudo journalctl -u edge-camera -n 50"
```

**Update Config**:
```bash
curl -X PUT http://rpi5.local:9001/api/config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "platform": {
      "cameras_url": "http://192.168.1.100:8005",
      "discovery_url": "http://192.168.1.100:8006"
    }
  }'
```

**Restart Service**:
```bash
# Via API
curl -X POST http://rpi5.local:9001/api/control/restart

# Via systemd (SSH)
ssh pi@rpi5.local "sudo systemctl restart edge-camera"
```

---

### Scenario B: Docker Container

#### Dockerfile

**File**: `Dockerfile`
```dockerfile
FROM python:3.11-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p /var/log/edge-camera

# Expose management API port
EXPOSE 9001

# Run application
CMD ["python", "src/main.py"]
```

---

#### Docker Compose

**File**: `docker-compose.yml`
```yaml
version: '3.8'

services:
  edge-camera:
    build: .
    container_name: edge-camera-001
    restart: unless-stopped
    
    # Camera device access
    devices:
      - /dev/video0:/dev/video0
    
    # Privileged mode for camera access
    privileged: true
    
    # Configuration via environment variables
    environment:
      - DEVICE__ID=edge-camera-001
      - DEVICE__NAME=RPi5 Camera
      - DEVICE__LOCATION=office
      - PLATFORM__CAMERAS_URL=http://192.168.1.100:8005
      - PLATFORM__DISCOVERY_URL=http://192.168.1.100:8006
      - PLATFORM__API_KEY=${PLATFORM_API_KEY}
    
    # Mount config file (optional override)
    volumes:
      - ./config/default.yaml:/app/config/default.yaml:ro
      - edge-camera-logs:/var/log/edge-camera
    
    # Expose management API
    ports:
      - "9001:9001"
    
    # Network
    network_mode: host  # For camera device access

volumes:
  edge-camera-logs:
```

---

#### Docker Management Commands

**Start**:
```bash
docker-compose up -d
```

**Stop**:
```bash
docker-compose down
```

**View Logs**:
```bash
# Last 50 lines
docker logs edge-camera-001 --tail 50

# Follow logs
docker logs edge-camera-001 -f
```

**Restart**:
```bash
docker restart edge-camera-001
```

**Update Configuration**:
```bash
# Edit environment variables
nano docker-compose.yml

# Recreate container
docker-compose up -d
```

**Remote Control via API** (same as native):
```bash
curl -X POST http://rpi5.local:9001/api/control/start
```

---

#### Docker Deployment Script

**File**: `deploy-docker.sh`
```bash
#!/bin/bash
# Docker deployment script for Raspberry Pi 5

set -e

# Pull or build image
echo "🔨 Building Docker image..."
docker-compose build

# Set API key from environment or prompt
if [ -z "$PLATFORM_API_KEY" ]; then
  read -sp "Enter platform API key: " PLATFORM_API_KEY
  export PLATFORM_API_KEY
fi

# Deploy
echo "🚀 Starting edge camera container..."
docker-compose up -d

# Show status
echo "✅ Deployment complete!"
docker-compose ps
docker logs edge-camera-001 --tail 20
```

---

## Security Considerations

### 1. API Authentication

**Recommendation**: JWT Bearer tokens

**Flow**:
1. Edge camera registers with platform → receives JWT
2. Platform stores edge camera JWT in database
3. Management API validates JWT on each request

**Implementation**:
```python
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    # Validate JWT with platform's public key or shared secret
    if not validate_jwt(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
```

---

### 2. Network Security

**Port Exposure**:
- Management API (9001): Restrict to trusted networks
- Use VPN or SSH tunnel for remote access
- Firewall rules: `sudo ufw allow from 192.168.1.0/24 to any port 9001`

**TLS/HTTPS**:
- For production, use TLS for management API
- Self-signed cert or Let's Encrypt with local DNS

---

### 3. Privilege Escalation

**Restart Command**:
- Application restart: Safe (no sudo required)
- System reboot: Requires sudo

**Solution**:
```bash
# Add to sudoers (edge-camera user)
edge-camera ALL=(ALL) NOPASSWD: /sbin/reboot
```

**API Implementation**:
```python
@app.post("/api/control/restart")
async def restart(scope: str, token: str = Depends(verify_token)):
    if scope == "application":
        # Restart Python process (systemd or Docker)
        if is_systemd():
            subprocess.run(["systemctl", "restart", "edge-camera"])
        else:
            sys.exit(0)  # Docker will restart
    elif scope == "system":
        subprocess.run(["sudo", "reboot"])
```

---

### 4. Configuration Injection

**Risk**: Malicious config could point to rogue platform

**Mitigation**:
- Validate URLs (whitelist domains)
- Require authentication for config changes
- Audit log all config updates

---

## Monitoring & Diagnostics

### 1. Health Checks

**Endpoint**: `GET /health`
```json
{
  "status": "healthy",
  "timestamp": "2026-02-01T10:00:00Z",
  "checks": {
    "camera": "ok",
    "streaming": "ok",
    "websocket": "ok",
    "platform": "ok"
  }
}
```

**Integration**:
- Prometheus metrics endpoint: `/metrics`
- Grafana dashboard for fleet monitoring

---

### 2. Log Aggregation

**Options**:
- **Centralized Logging**: Logstash, Fluentd → Elasticsearch
- **Cloud Logging**: AWS CloudWatch, Google Cloud Logging
- **Simple**: rsyslog to central syslog server

**Native systemd**:
```bash
# Forward journald to remote syslog
sudo nano /etc/systemd/journald.conf
# ForwardToSyslog=yes
# SyslogFacility=local0
# SyslogIdentifier=edge-camera
```

**Docker**:
```yaml
logging:
  driver: syslog
  options:
    syslog-address: "tcp://log-server:514"
    tag: "edge-camera-001"
```

---

### 3. Alerts

**Triggers**:
- Camera disconnected > 5 minutes
- WebSocket reconnection failures
- High error rate in frame uploads
- System temperature > 80°C

**Notification**:
- Platform webhook to orchestrator
- Email/SMS via communications service

---

## Implementation Roadmap

### Phase 1: Management API (1 week)
- [ ] Add FastAPI endpoints to `main.py`
  - `/api/config` (GET/PUT)
  - `/api/control/{action}` (POST)
  - `/api/logs` (GET)
  - `/api/status` (GET)
  - `/api/diagnostics/network` (GET)
- [ ] Implement JWT authentication
- [ ] Add log reading (journald + file)
- [ ] Test on RPi5 (native)

### Phase 2: Docker Support (3 days)
- [ ] Create Dockerfile
- [ ] Create docker-compose.yml
- [ ] Environment variable configuration override
- [ ] Test Docker deployment on RPi5

### Phase 3: Platform Integration (1 week)
- [ ] Platform backend: Proxy endpoints for edge cameras
- [ ] Frontend: Edge camera management UI
- [ ] Discovery service: Track edge camera IPs
- [ ] End-to-end testing

### Phase 4: Production Hardening (1 week)
- [ ] TLS/HTTPS for management API
- [ ] Rate limiting on endpoints
- [ ] Comprehensive error handling
- [ ] Monitoring/alerting integration
- [ ] Documentation and runbooks

---

## Conclusion

The recommended **Hybrid Architecture** (Management API + WebSocket) provides:

1. **Immediate Control**: Direct HTTP API for all operations
2. **Platform Integration**: Centralized management UI
3. **Flexibility**: Works offline (API) and online (WebSocket)
4. **Deployment Agnostic**: Same approach for native and Docker

### Key Benefits

- ✅ **Zero-Touch Configuration**: Update URLs, credentials remotely
- ✅ **Headless Operation**: No physical access needed
- ✅ **Fleet Management**: Platform tracks and controls all edge cameras
- ✅ **Diagnostics**: Logs, status, network tests via API
- ✅ **Security**: JWT authentication, optional TLS

### Next Steps

1. Implement Phase 1 (Management API)
2. Test on RPi5 with both native and Docker deployments
3. Integrate with platform UI
4. Deploy to production edge cameras

---

**Document Version**: 1.0  
**Author**: GitHub Copilot  
**Last Updated**: February 1, 2026
