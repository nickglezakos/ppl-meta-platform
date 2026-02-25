# Signage Configuration Setup - Quick Guide

## Two Configuration Methods

### 1. Console Setup Tool (Production/Admin Users) ⭐

**Runs ON the device** - For production deployments and admin users

- **Location**: `ppl-meta-signage-simple-player/setup_console.py`
- **Usage**: SSH to device and run setup tool
- **Audience**: Admin users, production deployments
- **Docs**: [Production Deployment Guide](docs/signage-production-deployment.md)

```bash
# SSH to device
ssh pi@192.168.1.100

# Run setup
cd /home/pi/ppl-meta-signage
./setup_console.py

# Start application
./start_signage.sh
```

### 2.  Remote HTTP API (Developers Only) 🔧

**Runs FROM your dev laptop** - For developer convenience during development

- **Location**: `tools/configure_signage_remote.py`
- **Usage**: Run from dev laptop to configure remote devices
- **Audience**: Developers only
- **Docs**: [Remote Configuration Guide](docs/signage-remote-configuration.md)

```bash
# From your dev laptop (NOT on the device)
./tools/configure_signage_remote.py --device-ip 192.168.1.100 --backend-ip 192.168.1.50
```

---

## What Was Implemented

### For Production (Primary Method):

#### 1. Console Setup Tool
**File:** `ppl-meta-signage-simple-player/setup_console.py`

- Runs ON the Raspberry Pi device
- Interactive console interface for configuration
- Reads/writes SharedPreferences (same as Flutter app)
- Tests backend connection before saving
- Non-interactive mode for automation
- Persistent storage across restarts

**Features:**
- `./setup_console.py` - Interactive setup
- `./setup_console.py --backend-ip X --discovery-port Y` - Non-interactive
- `./setup_console.py --show` - View current config
- `./setup_console.py --test` - Test connection

#### 2. Startup Script
**File:** `ppl-meta-signage-simple-player/start_signage.sh`

- Checks for configuration on startup
- Tests backend connection
- Prompts for setup if needed or connection fails
- Starts Flutter application

#### 3. Deployment Script  
**File:** `ppl-meta-signage-simple-player/deploy-to-rpi.sh`

- Builds application for Linux
- Transfers files to Raspberry Pi
- Sets up all scripts
- Guides through deployment

### For Developers (Secondary Method):

#### 4. HTTP Server Enhancements
**File:** `ppl-meta-signage-simple-player/lib/services/http_server.dart`

- Added `GET /api/v1/config` - Retrieve configuration
- Added `POST /api/v1/config` - Update configuration

#### 5. Remote CLI Tools (Developer Only)
- **Python Tool:** `tools/configure_signage_remote.py`
- **Bash Script:** `tools/configure-signage-remote.sh`

---

## Production Deployment Workflow

### Step 1: Build and Deploy

From your development machine:

```bash
cd ppl-meta-code

# Option A: Automated deployment
./ppl-meta-signage-simple-player/deploy-to-rpi.sh

# Option B: Manual deployment
cd ppl-meta-signage-simple-player
flutter build linux --release
rsync -avz build/linux/x64/release/bundle/ pi@<RPI_IP>:/home/pi/ppl-meta-signage/app/
rsync -avz setup_console.py start_signage.sh pi@<RPI_IP>:/home/pi/ppl-meta-signage/
```

### Step 2: SSH to Device

```bash
ssh pi@<RPI_IP>
cd /home/pi/ppl-meta-signage
```

### Step 3: Configure Backend Settings

```bash
# Interactive setup (prompts for IP and port)
./setup_console.py

# OR non-interactive
./setup_console.py --backend-ip 192.168.1.50 --discovery-port 8006
```

### Step 4: Start Application

```bash
# Using startup script (recommended)
./start_signage.sh

# OR manually
cd app
./signage_simple_player
```

### Step 5: Enable Auto-Start (Optional)

```bash
# Create systemd service (see Production Deployment Guide)
sudo systemctl enable ppl-meta-signage
sudo systemctl start ppl-meta-signage
```

---

## Developer Workflow (HTTP API Method)

### When to Use

- Testing during development
- Quickly switching backend IPs for test devices
- Debugging without SSH access

### Prerequisites

```bash
pip install requests
```

### Usage

From your dev laptop:

```bash
# Check if device is reachable
./tools/configure_signage_remote.py --device-ip 192.168.1.100 --check

# View current configuration  
./tools/configure_signage_remote.py --device-ip 192.168.1.100 --get

# Update configuration
./tools/configure_signage_remote.py \
  --device-ip 192.168.1.100 \
  --backend-ip 192.168.1.50 \
  --discovery-port 8006
```

**Note**: Device must be running the signage application for HTTP API to work.

---

## Configuration Flow

### How It Works

Both methods use the same underlying storage (SharedPreferences):

1. **Configuration Storage**:
   - Location: `~/.local/share/signage_simple_player/shared_preferences.json`
   - Format: JSON key-value pairs
   - Persists across restarts

2. **Startup Behavior**:
   - App checks for configuration on startup
   - If configured: Attempts auto-connection to backend
   - If not configured or connection fails: 
     - GUI app: Shows setup screen
     - Console: `start_signage.sh` prompts for setup
     - HTTP API: Waits for remote configuration

3. **Configuration Keys**:
   - `flutter.backend_ip` - Backend platform IP
   - `flutter.discovery_port` - Discovery service port
   - `flutter.is_configured` - Configuration flag

---

## Admin User Instructions

**For non-technical admin users deploying devices:**

### Simple Setup Steps

1. **Connect to device using SSH**:
   ```
   ssh pi@<DEVICE_IP_ADDRESS>
   ```

2. **Navigate to signage folder**:
   ```
   cd ppl-meta-signage
   ```

3. **Run setup**:
   ```
   ./setup_console.py
   ```

4. **Answer prompts**:
   - Enter the backend IP address (provided by IT)
   - Enter the  port number (usually 8006)
   - Confirm connection test

5. **Start application**:
   ```
   ./start_signage.sh
   ```

### Quick Reference

```bash
# View current settings
./setup_console.py --show

# Test connection
./setup_console.py --test

# Reconfigure
./setup_console.py

# Restart application
sudo systemctl restart ppl-meta-signage
```

---

## Troubleshooting

### Configuration Not Working

```bash
# Check current config
./setup_console.py --show

# Test connection
./setup_console.py --test

# View config file directly
cat ~/.local/share/signage_simple_player/shared_preferences.json
```

### Reset Configuration

```bash
# Remove config file
rm ~/.local/share/signage_simple_player/shared_preferences.json

# Run setup again
./setup_console.py
```

### Application Won't Start

```bash
# Check if configured
./setup_console.py --show

# Use startup script (handles config checks)
./start_signage.sh

# Check logs if using systemd
sudo journalctl -u ppl-meta-signage -f
```

---

## Documentation Links

### For Admin Users / Production
- **[Production Deployment Guide](docs/signage-production-deployment.md)** ⭐ - Complete production deployment guide
- **Console Setup Tool**: `ppl-meta-signage-simple-player/setup_console.py`
- **Startup Script**: `ppl-meta-signage-simple-player/start_signage.sh`
- **Deployment Script**: `ppl-meta-signage-simple-player/deploy-to-rpi.sh`

### For Developers
- **[Remote Configuration Guide](docs/signage-remote-configuration.md)** - HTTP API developer tool
- **Remote CLI Tool**: `tools/configure_signage_remote.py`
- **HTTP Server Code**: `ppl-meta-signage-simple-player/lib/services/http_server.dart`

---

## Summary

### ✅ What You Now Have

1. **Console Setup Tool** - SSH-based configuration for production deployments
2. **Startup Script** - Automatic config check and prompt on startup
3. **Deployment Script** - Automated build and deploy to Raspberry Pi
4. **HTTP API** - Developer tool for remote configuration during development
5. **Persistent Storage** - Configuration survives restarts
6. **Connection Testing** - Verify backend connectivity before saving

### 🎯 Recommended Approach

- **Production**: Use console setup tool (`setup_console.py`) via SSH
- **Development**: Use remote HTTP API (`configure_signage_remote.py`) from your laptop
- **Initial Deployment**: Use automated deployment script (`deploy-to-rpi.sh`)
- **Updates**: Configuration persists, just redeploy application files

### 📝 Key Files

| File | Purpose | Runs On |
|------|---------|---------|
| `setup_console.py` | Console configuration tool | Device (via SSH) |
| `start_signage.sh` | Startup with auto-config check | Device |
| `deploy-to-rpi.sh` | Automated deployment | Dev machine |
| `configure_signage_remote.py` | Remote config via HTTP | Dev machine |

---

## Next Steps

1. **Test locally**: Run console setup tool on your dev machine
2. **Deploy to RPi**: Use `deploy-to-rpi.sh` script
3. **Configure via SSH**: Run `setup_console.py` on device
4. **Enable auto-start**: Set up systemd service
5. **Document for admins**: Share admin user instructions

For questions, see the [Production Deployment Guide](docs/signage-production-deployment.md).

