# Edge Camera Manual Registration - Quick Start Guide

## 🎯 Overview
This guide shows you how to add an edge camera to the PPL Meta Platform using manual IP entry.

---

## 📸 Screenshots Flow

### Step 1: Edge Camera Startup (RPi5 Console)
```
======================================================================
🎥  PPL Meta Edge Camera - Started Successfully
======================================================================

📡  Connection Information:
    Device ID:       edge-camera-rpi5-001
    IP Address:      192.168.1.150     <--- COPY THIS
    Management Port: 9001
    Streaming Port:  8554

🌐  Access Points:
    Setup Page:      http://192.168.1.150:9001
    Management API:  http://192.168.1.150:9001/api
    Stream URL:      rtsp://192.168.1.150:8554/stream
    Health Check:    http://192.168.1.150:9001/health
    
...
======================================================================
```

---

### Step 2: Edge Camera Landing Page (Optional)
Open `http://192.168.1.150:9001` in browser:

```
┌────────────────────────────────────────────────────┐
│                                                    │
│                       🎥                           │
│           PPL Meta Edge Camera                     │
│          ✅ Connected to Platform                  │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  Device ID:       edge-camera-rpi5-001  [Copy] │
│  │  IP Address:      192.168.1.150        [Copy] │
│  │  Management Port: 9001                         │
│  │  Streaming Port:  8554 (RTSP)                  │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  📝 Setup Instructions                             │
│  1. Note the IP Address above: 192.168.1.150      │
│  2. Open your PPL Meta Platform web interface     │
│  3. Navigate to Cameras → Add Edge Camera         │
│  4. Enter the IP address and click Test Connection│
│  5. Click Add Camera to register                  │
│                                                    │
│  🔌 Available Endpoints                            │
│  Management API: http://192.168.1.150:9001/api    │
│  Stream URL:     rtsp://192.168.1.150:8554/stream │
│  Health Check:   http://192.168.1.150:9001/health │
│  Identify:       http://192.168.1.150:9001/api/id │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

### Step 3: Platform Cameras Screen
```
┌─────────────────────────────────────────────────────────────┐
│  Cameras                          🔄 ➕ 📹                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Edge Cameras                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🎥  Living Room Camera                             │   │
│  │      ● Online  |  Raspberry Pi 5  |  Manage >       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Other Cameras                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📹  Front Door RTSP                                │   │
│  │      ● Online  |  192.168.1.100                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Legend:
🔄 = Refresh
➕ = Add RTSP Camera
📹 = Add Edge Camera  <--- Click this!
```

---

### Step 4: Add Edge Camera Dialog
```
┌─────────────────────────────────────────────────────────┐
│  🎥  Add Edge Camera                               [X]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Camera Name:                                           │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Living Room Camera                               │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  IP Address:                        Port:               │
│  ┌──────────────────────────────┐  ┌────────────────┐  │
│  │  192.168.1.150               │  │  9001          │  │
│  └──────────────────────────────┘  └────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  🔍 Test Connection                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ✅ Connection successful!                              │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  ℹ️  Edge Camera Information                      │ │
│  │  Device ID:        edge-camera-rpi5-001          │ │
│  │  Management Port:  9001                          │ │
│  │  Stream Port:      8554                          │ │
│  │  Status:           unconfigured                  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│                           [Cancel]  [➕ Add Camera]     │
└─────────────────────────────────────────────────────────┘
```

---

### Step 5: Success!
```
┌─────────────────────────────────────────────────────────────┐
│  Cameras                          🔄 ➕ 📹                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Edge camera "Living Room Camera" added successfully     │
│                                                             │
│  Edge Cameras                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🎥  Living Room Camera                 [NEW!]      │   │
│  │      ⚫ Waiting  |  Raspberry Pi 5  |  Manage >     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Click "Manage" to configure platform connection           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Command Reference

### Start Edge Camera on RPi5
```bash
cd /home/pi/ppl-meta-edge-camera
source venv/bin/activate
python -m src.main
```

### Check Edge Camera Status
```bash
# From any computer on the network
curl http://192.168.1.150:9001/health

# Get camera details
curl http://192.168.1.150:9001/api/identify
```

### Find RPi5 IP Address (if lost)
```bash
# On the RPi5 via SSH or console:
hostname -I

# From another computer (if you know hostname):
ping raspberrypi.local

# Check router DHCP list
# (Access your router admin page, usually 192.168.1.1)
```

---

## ⚠️ Troubleshooting

### "Cannot reach edge camera" Error

**Causes:**
- Edge camera not running
- Wrong IP address
- Firewall blocking port 9001
- Different subnet/VLAN

**Solutions:**
```bash
# 1. Verify edge camera is running
ssh pi@192.168.1.150
ps aux | grep main.py

# 2. Test port accessibility
nc -zv 192.168.1.150 9001

# 3. Check firewall (on RPi5)
sudo ufw status
sudo ufw allow 9001

# 4. Verify network connectivity
ping 192.168.1.150
```

### "Edge camera already exists" Error

**Cause:** Device ID already registered

**Solution:**
```bash
# Option 1: Use different device ID (change in edge camera config)

# Option 2: Remove existing registration via SQL
psql -d ppl_meta -c "DELETE FROM cameras WHERE device_id='edge-camera-rpi5-001';"

# Option 3: Update existing camera in frontend
```

### Cannot Find Edge Camera IP

**Solutions:**

1. **HDMI Monitor:** Connect monitor to RPi5, see console banner
2. **SSH Access:** `ssh pi@raspberrypi.local` then run `hostname -I`
3. **Router DHCP:** Check router admin page for device list
4. **Network Scanner:** Use tool like Angry IP Scanner
5. **mDNS:** Try `http://raspberrypi.local:9001` (if mDNS enabled)

---

## 📝 Step-by-Step Checklist

- [ ] Start edge camera on RPi5
- [ ] Note IP address from console banner
- [ ] (Optional) Verify landing page accessible in browser
- [ ] Open PPL Meta Platform web interface
- [ ] Navigate to Cameras screen
- [ ] Click "Add Edge Camera" button (camera icon)
- [ ] Enter IP address and port
- [ ] Click "Test Connection"
- [ ] Verify ✅ success message and camera info
- [ ] Click "Add Camera"
- [ ] See camera in cameras list
- [ ] Click "Manage" to configure platform connection
- [ ] Edge camera status changes from "Waiting" to "Online"

---

## 🎓 Pro Tips

### For Developers
```bash
# Start edge camera with debug logging
LOG_LEVEL=DEBUG python -m src.main

# Monitor edge camera logs
tail -f /var/log/ppl-edge-camera/app.log

# Test identify endpoint
curl -s http://192.168.1.150:9001/api/identify | jq .
```

### For Production
1. **Static IP:** Assign static IP to RPi5 in router DHCP settings
2. **Hostname:** Set meaningful hostname: `edge-cam-livingroom`
3. **Autostart:** Create systemd service to start on boot
4. **Monitoring:** Set up health check alerts
5. **Backup Config:** Save edge camera config to git

---

## 📊 Expected Behavior

| Action | Expected Result | Typical Time |
|--------|----------------|--------------|
| Start edge camera | Banner displays in <5s | 3-5 seconds |
| Access landing page | HTML loads immediately | <1 second |
| Test connection | ✅ or ❌ response | 2-3 seconds |
| Add camera | Success + appears in list | 3-5 seconds |
| Click Manage | Opens management screen | <1 second |

---

## 🔐 Security Notes

- **No Authentication Required:** Identify endpoint is public (discovery only)
- **Local Network Only:** Edge camera should NOT be exposed to internet
- **Platform Auth:** Management API requires JWT token (after configuration)
- **Firewall:** Only open ports 9001 (management) and 8554 (RTSP)

---

## 🎯 Success Criteria

✅ You've successfully added an edge camera when:

1. Camera appears in "Edge Cameras" section
2. Status shows ⚫ Waiting (unconfigured) or ● Online (configured)
3. Clicking "Manage" opens edge camera management screen
4. Can configure platform connection
5. Edge camera receives commands from platform

---

**Next Steps:**
1. Configure platform connection in management screen
2. Test streaming functionality
3. Set up triggers and recording schedules
4. Monitor camera health and performance

**Documentation:**
- Full architecture: `docs/architecture/EDGE_CAMERA_REMOTE_OPERATION.md`
- Implementation details: `docs/implementation/EDGE_CAMERA_MANUAL_REGISTRATION.md`
- Management API: `docs/api/EDGE_CAMERA_MANAGEMENT_API.md`
