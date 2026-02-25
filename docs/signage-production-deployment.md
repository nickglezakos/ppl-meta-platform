files# PPL Meta Signage - Production Deployment Guide

## Overview

This guide covers deploying the PPL Meta Signage application to Raspberry Pi devices for production use. The application includes a **console-based setup tool** that allows admin users to configure devices via SSH, eliminating the need for physical access to the device display.

## Architecture

### Configuration Storage
- Uses SharedPreferences (Flutter) stored in `~/.local/share/signage_simple_player/shared_preferences.json`
- Persists across restarts
- Console tool reads/writes same storage as Flutter app

### Startup Flow
1. Check for existing configuration
2. If configured: Test backend connection
3. If not configured or connection fails: Prompt user via console
4. Save configuration
5. Start Flutter application

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

Use the provided deployment script from your development machine:

```bash
# From your dev machine
cd ppl-meta-code
./ppl-meta-signage-simple-player/deploy-to-rpi.sh
```

The script will:
- Build the application for Linux
- Transfer files to Raspberry Pi via rsync
- Set up all required scripts
- Display next steps

### Method 2: Manual Deployment

#### Step 1: Build the Application

On your development machine:

```bash
cd ppl-meta-signage-simple-player
flutter build linux --release
```

#### Step 2: Transfer to Raspberry Pi

```bash
# Transfer built application
rsync -avz build/linux/x64/release/bundle/ pi@<RPI_IP>:/home/pi/ppl-meta-signage/app/

# Transfer setup scripts
rsync -avz setup_console.py start_signage.sh pi@<RPI_IP>:/home/pi/ppl-meta-signage/
```

#### Step 3: SSH to Raspberry Pi

```bash
ssh pi@<RPI_IP>
cd /home/pi/ppl-meta-signage
chmod +x setup_console.py start_signage.sh
```

## Configuration

### Interactive Console Setup

SSH to the device and run the setup tool:

```bash
ssh pi@<RPI_IP>
cd /home/pi/ppl-meta-signage
./setup_console.py
```

The tool will prompt for:
- Backend IP address
- Discovery service port
- Connection test

Example session:

```
==========================================================
PPL Meta Signage - Console Setup
============================================================

Backend IP address [192.168.1.50]: 192.168.1.50
Discovery Service Port [8006]: 8006

Configuration Summary:
  Backend IP: 192.168.1.50
  Discovery Port: 8006
  Discovery URL: http://192.168.1.50:8006
  Media URL: http://192.168.1.50:8000
  Gateway URL: http://192.168.1.50:8080

Test connection before saving? (Y/n): y
🔍 Testing connection to http://192.168.1.50:8006...
✅ Successfully connected to Discovery Service
   Service: ppl-meta-discovery

✅ Configuration saved successfully!

Next Steps:
  1. Restart the signage application for changes to take effect
  2. The application will automatically connect to the backend
  3. Check logs for connection status
```

### Non-Interactive Setup

For automated deployments:

```bash
./setup_console.py --backend-ip 192.168.1.50 --discovery-port 8006
```

Skip connection test (save without testing):

```bash
./setup_console.py --backend-ip 192.168.1.50 --force
```

### View Current Configuration

```bash
./setup_console.py --show
```

### Test Connection

```bash
./setup_console.py --test
```

## Starting the Application

### Using the Startup Script (Recommended)

The startup script automatically checks configuration and handles setup:

```bash
cd /home/pi/ppl-meta-signage
./start_signage.sh
```

The script will:
1. Check if configuration exists
2. Test backend connection
3. Prompt for setup if needed
4. Start the Flutter application

### Manual Start

If you prefer to start the Flutter app directly:

```bash
cd /home/pi/ppl-meta-signage/app
./signage_simple_player
```

## Auto-Start on Boot (systemd)

Create a systemd service for automatic startup:

### Step 1: Create Service File

```bash
sudo nano /etc/systemd/system/ppl-meta-signage.service
```

Add the following content:

```ini
[Unit]
Description=PPL Meta Signage Player
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ppl-meta-signage
ExecStart=/home/pi/ppl-meta-signage/start_signage.sh
Restart=always
RestartSec=10
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable ppl-meta-signage
sudo systemctl start ppl-meta-signage
```

### Step 3: Check Status

```bash
sudo systemctl status ppl-meta-signage
```

### View Logs

```bash
sudo journalctl -u ppl-meta-signage -f
```

## Production Workflow

### Initial Deployment

1. **Build on dev machine**: `flutter build linux --release`
2. **Deploy to RPi**: `./deploy-to-rpi.sh`
3. **SSH to device**: `ssh pi@<RPI_IP>`
4. **Run setup**: `./setup_console.py`
5. **Start application**: `./start_signage.sh`
6. **Enable auto-start**: Configure systemd service

### Updating Configuration

If backend IP changes or setup needs updating:

```bash
# SSH to device
ssh pi@<RPI_IP>

# Reconfigure
cd /home/pi/ppl-meta-signage
./setup_console.py

# Restart application
sudo systemctl restart ppl-meta-signage
```

### Deploying Updates

When deploying updated application:

```bash
# From dev machine
./deploy-to-rpi.sh

# On RPi (via SSH)
sudo systemctl restart ppl-meta-signage
```

Configuration is preserved during updates.

## Troubleshooting

### Configuration File Location

```bash
# View configuration file
cat ~/.local/share/signage_simple_player/shared_preferences.json
```

### Reset Configuration

```bash
# Remove configuration file
rm ~/.local/share/signage_simple_player/shared_preferences.json

# Run setup again
./setup_console.py
```

### Connection Issues

1. **Verify backend is running**:
   ```bash
   curl http://<BACKEND_IP>:8006/health
   ```

2. **Check network connectivity**:
   ```bash
   ping <BACKEND_IP>
   ```

3. **Test connection**:
   ```bash
   ./setup_console.py --test
   ```

### Application Won't Start

1. **Check logs**:
   ```bash
   sudo journalctl -u ppl-meta-signage -n 50
   ```

2. **Verify configuration**:
   ```bash
   ./setup_console.py --show
   ```

3. **Test backend connection**:
   ```bash
   ./setup_console.py --test
   ```

4. **Restart service**:
   ```bash
   sudo systemctl restart ppl-meta-signage
   ```

## Multiple Device Deployment

For deploying to multiple Raspberry Pi devices:

### Create Device List

```bash
# devices.txt
192.168.1.100
192.168.1.101
192.168.1.102
```

### Deploy to All Devices

```bash
#!/bin/bash
BACKEND_IP="192.168.1.50"

while IFS= read -r RPI_IP; do
    echo "Deploying to $RPI_IP..."
    
    # Deploy application
    rsync -avz build/linux/x64/release/bundle/ pi@${RPI_IP}:/home/pi/ppl-meta-signage/app/
    rsync -avz setup_console.py start_signage.sh pi@${RPI_IP}:/home/pi/ppl-meta-signage/
    
    # Configure automatically
    ssh pi@${RPI_IP} "cd /home/pi/ppl-meta-signage && ./setup_console.py --backend-ip ${BACKEND_IP} --force"
    
    # Restart service
    ssh pi@${RPI_IP} "sudo systemctl restart ppl-meta-signage"
    
    echo "✅ $RPI_IP complete"
    echo ""
done < devices.txt
```

## Security Considerations

### Network Security

- Deploy devices on isolated VLAN
- Use firewall rules to restrict access
- Consider VPN for remote management

### SSH Security

- Use SSH keys instead of passwords
- Disable password authentication
- Change default username if needed
- Keep SSH access restricted

### Configuration Security

- Configuration file permissions: `chmod 600 ~/.local/share/signage_simple_player/shared_preferences.json`
- Restrict access to setup scripts
- Use read-only filesystem for production (optional)

## Admin User Guide

### For Non-Technical Users

1. **Connect to device**:
   - Use SSH client (PuTTY on Windows, Terminal on Mac/Linux)
   - Connect to device IP address
   - Login with provided credentials

2. **Run configuration**:
   ```bash
   cd ppl-meta-signage
   ./setup_console.py
   ```

3. **Follow prompts**:
   - Enter backend IP address (provided by IT/admin)
   - Enter port (usually 8006)
   - Test connection
   - Save configuration

4. **Start application**:
   ```bash
   ./start_signage.sh
   ```

### Quick Reference Card

```
SSH Connection:
  ssh pi@<DEVICE_IP>

Navigate to signage:
  cd ppl-meta-signage

Configure:
  ./setup_console.py

Start:
  ./start_signage.sh

Restart:
  sudo systemctl restart ppl-meta-signage

View logs:
  sudo journalctl -u ppl-meta-signage -f
```

## Related Documentation

- [Console Setup Tool](./setup_console.py) - Main configuration tool
- [Startup Script](./start_signage.sh) - Application startup with config check
- [Deployment Script](./deploy-to-rpi.sh) - Automated deployment
- [Remote Configuration (Developer Tool)](../docs/signage-remote-configuration.md) - For developers only

## Support

For deployment issues:
1. Check this guide
2. Review logs: `sudo journalctl -u ppl-meta-signage`
3. Test configuration: `./setup_console.py --test`
4. Verify backend services are running
