 # PPL Meta Signage - Remote Configuration Guide (Developer Tool)

## ⚠️ Important: Developer Tool Only

**This document describes remote HTTP API-based configuration for DEVELOPER use only.**

**For production deployments and admin users**, use the **console-based setup tool** that runs ON the device via SSH. See [Production Deployment Guide](./signage-production-deployment.md).

---

## Overview

The PPL Meta Signage service includes an HTTP API for **remote configuration** that runs on port 8009. This is intended for **developers** during development to configure test devices from their laptop without physical access.

### When to Use This

✅ **Developer scenarios:**
- Testing signage app on your dev laptop network
- Quickly reconfiguring test devices during development
- Debugging configuration issues
- Iterating on backend changes with live device

❌ **NOT for production:**
- Admin users don't have these Python tools
- Requires network access  to device HTTP API
- Intended for developer workflows only

### Production Alternative

**Admin users and production deployments should use:**
- **Console Setup Tool**: `setup_console.py` (runs ON the device via SSH)
- **Production Deployment Guide**: [signage-production-deployment.md](./signage-production-deployment.md)

---

## Overview (Developer Use)

The PPL Meta Signage service now supports **remote configuration** via its built-in HTTP server. This allows you to configure signage devices (such as Raspberry Pi 5) from your development laptop without requiring physical access to the device.

## Architecture

The signage application runs a REST API server on port **8009** that provides:
- Health checks
- Configuration retrieval
- Configuration updates
- Playback control
- Status monitoring

## Prerequisites

1. **Signage Device Requirements:**
   - PPL Meta Signage application installed and running
   - Network connectivity (same network or accessible via IP)
   - HTTP server running on port 8009 (enabled by default)

2. **Client Requirements:**
   - Network access to the signage device
   - Python 3.x with `requests` library OR `curl` for bash script
   - Knowledge of the device's IP address

## Installation

### Install Python Dependencies

```bash
pip install requests
```

Or if using pipenv/poetry in your development environment:

```bash
pip install requests
```

## Usage

### Method 1: Python CLI Tool (Recommended)

Location: `tools/configure_signage_remote.py`

#### Check Device Health

```bash
./tools/configure_signage_remote.py --device-ip 192.168.1.100 --check
```

Expected output:
```
🔌 Connecting to signage device at 192.168.1.100:8009

✅ Device is healthy
   Service: signage-simple
   Version: 1.0.0
   Device ID: abc123...
```

#### Get Current Configuration

```bash
./tools/configure_signage_remote.py --device-ip 192.168.1.100 --get
```

Expected output:
```
📋 Current Configuration:
   Backend IP: 192.168.1.50
   Discovery Port: 8006
   Configured: True
   Discovery URL: http://192.168.1.50:8006
   Media URL: http://192.168.1.50:8000
   Gateway URL: http://192.168.1.50:8080
```

#### Set Configuration

```bash
./tools/configure_signage_remote.py \
  --device-ip 192.168.1.100 \
  --backend-ip 192.168.1.50 \
  --discovery-port 8006
```

Expected output:
```
🔧 Updating Configuration:
   Backend IP: 192.168.1.50
   Discovery Port: 8006

✅ Configuration Updated Successfully!
⚠️  Restart Required: Please restart the signage application for changes to take effect.

📋 New Configuration:
   Backend IP: 192.168.1.50
   Discovery Port: 8006
   Discovery URL: http://192.168.1.50:8006
   Media URL: http://192.168.1.50:8000
   Gateway URL: http://192.168.1.50:8080
```

### Method 2: Bash Script

Location: `tools/configure-signage-remote.sh`

```bash
# Check health
./tools/configure-signage-remote.sh --device-ip 192.168.1.100 --check

# Get configuration
./tools/configure-signage-remote.sh --device-ip 192.168.1.100 --get

# Set configuration
./tools/configure-signage-remote.sh \
  --device-ip 192.168.1.100 \
  --backend-ip 192.168.1.50 \
  --discovery-port 8006
```

### Method 3: Direct HTTP API Calls

#### Check Health

```bash
curl http://192.168.1.100:8009/health
```

#### Get Configuration

```bash
curl http://192.168.1.100:8009/api/v1/config
```

#### Set Configuration

```bash
curl -X POST http://192.168.1.100:8009/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "backend_ip": "192.168.1.50",
    "discovery_port": 8006
  }'
```

## API Reference

### Endpoints

#### `GET /health`

Health check endpoint to verify the device is online and responsive.

**Response:**
```json
{
  "status": "healthy",
  "service": "signage-simple",
  "version": "1.0.0",
  "device_id": "abc123...",
  "timestamp": "2026-02-13T10:30:00.000Z"
}
```

#### `GET /api/v1/config`

Retrieve current configuration from the device.

**Response:**
```json
{
  "status": "success",
  "configuration": {
    "backend_ip": "192.168.1.50",
    "discovery_port": 8006,
    "is_configured": true,
    "discovery_service_url": "http://192.168.1.50:8006",
    "media_service_url": "http://192.168.1.50:8000",
    "gateway_url": "http://192.168.1.50:8080"
  },
  "device_id": "abc123...",
  "timestamp": "2026-02-13T10:30:00.000Z"
}
```

#### `POST /api/v1/config`

Update device configuration remotely.

**Request Body:**
```json
{
  "backend_ip": "192.168.1.50",
  "discovery_port": 8006
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration updated successfully. Please restart the application for changes to take effect.",
  "configuration": {
    "backend_ip": "192.168.1.50",
    "discovery_port": 8006,
    "discovery_service_url": "http://192.168.1.50:8006",
    "media_service_url": "http://192.168.1.50:8000",
    "gateway_url": "http://192.168.1.50:8080"
  },
  "restart_required": true,
  "timestamp": "2026-02-13T10:30:00.000Z"
}
```

## Common Use Cases

### 1. Initial Device Setup (Remote)

When you deploy a new Raspberry Pi with the signage application:

```bash
# From your dev laptop
./tools/configure_signage_remote.py \
  --device-ip 192.168.1.100 \
  --backend-ip 192.168.1.50
```

Then restart the signage application on the device.

### 2. Changing Backend Server

If you move your backend platform to a new IP address:

```bash
./tools/configure_signage_remote.py \
  --device-ip 192.168.1.100 \
  --backend-ip 192.168.1.75
```

### 3. Multiple Device Configuration

Configure multiple devices in a loop:

```bash
#!/bin/bash
BACKEND_IP="192.168.1.50"
DEVICES=("192.168.1.100" "192.168.1.101" "192.168.1.102")

for DEVICE in "${DEVICES[@]}"; do
    echo "Configuring device: $DEVICE"
    ./tools/configure_signage_remote.py \
      --device-ip "$DEVICE" \
      --backend-ip "$BACKEND_IP"
    echo "---"
done
```

### 4. Health Monitoring

Create a simple monitoring script:

```bash
#!/bin/bash
while true; do
    ./tools/configure_signage_remote.py --device-ip 192.168.1.100 --check
    sleep 60
done
```

## Troubleshooting

### Connection Refused

**Problem:** Cannot connect to device
```
❌ Cannot reach device: Connection refused
```

**Solutions:**
1. Verify the device IP address
2. Ensure the signage application is running
3. Check network connectivity: `ping 192.168.1.100`
4. Verify port 8009 is not blocked by firewall

### Configuration Not Applied

**Problem:** Configuration updated but device still uses old settings

**Solution:** Restart the signage application on the device. The configuration is saved to persistent storage but the application needs to restart to reload it.

### Invalid IP Address

**Problem:** Configuration fails with "Invalid IP address format"

**Solution:** Ensure you're providing a valid IPv4 address in the format: `xxx.xxx.xxx.xxx`

### Port Not Available

**Problem:** HTTP server won't start due to port conflict

**Solution:** Ensure port 8009 is not already in use:
```bash
# On the Raspberry Pi
sudo lsof -i :8009
```

## Security Considerations

### Current Implementation

The current implementation does not include authentication. The HTTP server accepts requests from any client that can reach it on the network.

### Recommended Security Measures

1. **Network Isolation:** Deploy signage devices on a separate VLAN or network segment
2. **Firewall Rules:** Configure firewall to only allow connections from trusted IP addresses
3. **VPN:** Use a VPN connection for remote configuration over the internet

### Future Enhancements

Consider adding:
- API key authentication
- Basic HTTP authentication
- TLS/SSL encryption
- Rate limiting
- IP whitelisting

## Integration with Existing Workflow

### Development Workflow

1. **Local Development:** Develop and test backend on your laptop (e.g., `192.168.1.50`)
2. **Deploy to Pi:** Configure Pi to point to your dev laptop:
   ```bash
   ./tools/configure_signage_remote.py \
     --device-ip 192.168.1.100 \
     --backend-ip 192.168.1.50
   ```
3. **Test:** Restart signage app and verify it connects to your dev backend
4. **Iterate:** Make changes to backend and test against live device

### Production Deployment

1. **Pre-configure Devices:** Before shipping devices, configure them:
   ```bash
   ./tools/configure_signage_remote.py \
     --device-ip 192.168.1.100 \
     --backend-ip production.backend.com
   ```
2. **Remote Management:** Update device configurations remotely as needed
3. **Monitoring:** Regularly check health status of deployed devices

## Related Documentation

- [Signage Application README](../ppl-meta-signage-simple-player/README.md)
- [HTTP Server Implementation](../ppl-meta-signage-simple-player/lib/services/http_server.dart)
- [Configuration Service](../ppl-meta-signage-simple-player/lib/services/config_service.dart)

## Support

For issues or questions:
1. Check the application logs on the device
2. Verify network connectivity
3. Ensure all services are running
4. Review this documentation

## Changelog

### v1.0.0 (2026-02-13)
- Initial implementation of remote configuration
- Added GET/POST `/api/v1/config` endpoints
- Created Python CLI tool
- Created Bash script alternative
- Added comprehensive documentation
