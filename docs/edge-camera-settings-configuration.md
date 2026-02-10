# Edge Camera Settings Configuration Guide

## Overview

This guide explains how to properly configure camera settings (brightness, contrast, saturation, sharpness, focus) on the Raspberry Pi 5 edge camera. The OV5640 USB camera sensor uses v4l2 (Video4Linux2) controls that require specific permissions and procedures to modify.

## Prerequisites

- SSH access to Raspberry Pi (192.168.1.77)
- Sudo privileges on the Pi
- Edge camera Docker container deployed

## Important Concepts

### Why Container Must Be Stopped

The Docker container opens `/dev/video0` with **exclusive access** when running. This prevents other processes (including v4l2-ctl) from modifying hardware settings, even with sudo privileges. You will see "Permission denied" errors if you try to change settings while the container is running.

### Permission Requirements

- **v4l2-ctl** requires **root privileges** to modify hardware camera controls
- Sudo via remote SSH often fails for security reasons
- **Solution**: SSH into the Pi directly and run sudo commands locally

## Step-by-Step Procedure

### 1. SSH into Raspberry Pi

```bash
ssh pi@192.168.1.77
```

Enter password when prompted.

### 2. Stop Edge Camera Container

```bash
cd ~/ppl-meta-deploy
docker compose stop edge-camera
```

Verify container is stopped:
```bash
docker compose ps edge-camera
```

Should show no running containers or STATUS as "exited".

### 3. Check Current Settings (Optional)

```bash
sudo v4l2-ctl --device=/dev/video0 --list-ctrls
```

Or get specific values:
```bash
sudo v4l2-ctl --device=/dev/video0 --get-ctrl=brightness,contrast,saturation,sharpness,focus_automatic_continuous,focus_absolute
```

### 4. Apply New Settings

#### Option A: All Settings at Once (May Fail on focus_absolute)

```bash
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=135,contrast=55,saturation=85,sharpness=4,focus_automatic_continuous=0,focus_absolute=205
```

If you see "Permission denied focus_absolute", proceed to Option B.

#### Option B: Two-Step Application (Recommended)

**Step 1:** Set all controls except focus:
```bash
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=135,contrast=55,saturation=85,sharpness=4,focus_automatic_continuous=0
```

**Step 2:** Set focus separately:
```bash
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=focus_absolute=205
```

### 5. Verify Settings Applied

```bash
sudo v4l2-ctl --device=/dev/video0 --get-ctrl=brightness,contrast,saturation,sharpness,focus_automatic_continuous,focus_absolute
```

Expected output:
```
brightness: 135
contrast: 55
saturation: 85
sharpness: 4
focus_automatic_continuous: 0
focus_absolute: 205
```

### 6. Restart Edge Camera Container

```bash
cd ~/ppl-meta-deploy
docker compose start edge-camera
```

Verify container is running:
```bash
docker compose ps edge-camera
```

Should show STATUS as "running" or "Up".

Check container logs for startup issues:
```bash
docker compose logs --tail 50 edge-camera
```

### 7. Test Stream Quality

View the camera stream in the frontend at **http://localhost:3000** (from your development machine, not the Pi).

## Recommended Settings

### Balanced Quality (Current/Default)
```bash
brightness=135          # Good for indoor lighting
contrast=55             # Enhanced definition without clipping
saturation=85           # Vibrant colors for face detection
sharpness=4             # Doubled from 2 - sharper edges, no artifacts
focus_automatic_continuous=0  # Disable auto-focus for stability
focus_absolute=205      # Manual focus optimized for 0.5-1.5m distance
```

### Maximum Quality (For Testing)
```bash
brightness=135
contrast=60
saturation=90
sharpness=5
focus_automatic_continuous=0
focus_absolute=205
```

**Warning**: Sharpness 5+ may introduce artifacts (rhombus shadows, edge halos).

### Conservative (Fallback)
```bash
brightness=135
contrast=50
saturation=75
sharpness=3
focus_automatic_continuous=0
focus_absolute=205
```

## Parameter Ranges

| Parameter | Min | Max | Current | Unit | Notes |
|-----------|-----|-----|---------|------|-------|
| brightness | 0 | 255 | 135 | absolute | 0=black, 255=white |
| contrast | 0 | 255 | 55 | absolute | Edge definition |
| saturation | 0 | 100 | 85 | percentage | Color vibrancy |
| sharpness | 0 | 7 | 4 | discrete | 0=blur, 7=max sharp |
| focus_automatic_continuous | 0 | 1 | 0 | boolean | 0=manual, 1=auto |
| focus_absolute | 0 | 1023 | 205 | absolute | Focus distance (manual only) |

## Troubleshooting

### Problem: "Permission denied" even with sudo

**Cause**: Docker container still has exclusive lock on device.

**Solution**: 
1. Verify container is stopped: `docker compose ps edge-camera`
2. If still running: `docker compose stop edge-camera`
3. Check for zombie processes: `lsof /dev/video0`
4. If processes found: `sudo fuser -k /dev/video0`

### Problem: Settings don't persist after container restart

**Cause**: v4l2 settings are reset when the device is reopened by a new process.

**Solution**: Settings applied before container start will persist for that session. To make permanent:
1. Create a systemd service to apply settings on boot
2. Add settings to container startup script
3. Or manually apply before each container start (current method)

### Problem: focus_absolute fails even when applied separately

**Cause**: Some OV5640 firmware versions lock focus control.

**Solution**:
1. Try USB device reset:
```bash
sudo sh -c 'echo "1-1" > /sys/bus/usb/devices/1-1/authorized'
sudo sh -c 'echo "0" > /sys/bus/usb/devices/1-1/authorized'
sleep 2
sudo sh -c 'echo "1" > /sys/bus/usb/devices/1-1/authorized'
sleep 2
```

2. Then retry setting focus:
```bash
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=focus_absolute=205
```

### Problem: Image quality worse after settings change

**Symptoms**: Over-sharpening artifacts, washed out colors, too much contrast

**Solution**:
1. Reset to defaults:
```bash
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=128,contrast=32,saturation=64,sharpness=2,focus_automatic_continuous=0,focus_absolute=200
```

2. Apply recommended balanced settings (see above)
3. Fine-tune incrementally

### Problem: Cannot SSH into Pi

**Cause**: Pi offline, SSH disabled, or network issue.

**Solution**:
1. Ping Pi: `ping 192.168.1.77`
2. Check Pi power/network cable
3. Access Pi via keyboard/monitor
4. Enable SSH: `sudo raspi-config` → Interface Options → SSH → Enable

## Common Workflow Scenarios

### Scenario 1: Quick Brightness Adjustment

```bash
# 1. SSH in
ssh pi@192.168.1.77

# 2. Adjust brightness without stopping container (if it works)
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=140

# If fails with permission denied:
cd ~/ppl-meta-deploy
docker compose stop edge-camera
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=140
docker compose start edge-camera
```

### Scenario 2: Full Quality Tune-Up

```bash
# 1. SSH in
ssh pi@192.168.1.77

# 2. Stop container
cd ~/ppl-meta-deploy
docker compose stop edge-camera

# 3. Get current settings
sudo v4l2-ctl --device=/dev/video0 --get-ctrl=brightness,contrast,saturation,sharpness

# 4. Apply new settings
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=135,contrast=55,saturation=85,sharpness=4,focus_automatic_continuous=0
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=focus_absolute=205

# 5. Verify
sudo v4l2-ctl --device=/dev/video0 --get-ctrl=brightness,contrast,saturation,sharpness,focus_automatic_continuous,focus_absolute

# 6. Restart
docker compose start edge-camera

# 7. Check logs
docker compose logs --tail 50 edge-camera
```

### Scenario 3: Reset to Factory Defaults

```bash
# 1. SSH in
ssh pi@192.168.1.77

# 2. Stop container
cd ~/ppl-meta-deploy
docker compose stop edge-camera

# 3. Reset to OV5640 defaults
sudo v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=128,contrast=32,saturation=64,sharpness=2,focus_automatic_continuous=1

# 4. Restart
docker compose start edge-camera
```

## Why These Settings Matter for Face Detection

### Sharpness (Most Critical)
- **Too Low (0-2)**: Blurry edges, face detection accuracy drops 20-30%
- **Optimal (3-5)**: Clear facial features, good edge definition
- **Too High (6-7)**: Artifacts can confuse detection algorithms

### Saturation
- **Too Low (<60)**: Washed out colors, harder to distinguish skin tones
- **Optimal (75-90)**: Vibrant colors, better demographic classification
- **Too High (>95)**: Oversaturation, unnatural skin tones

### Contrast
- **Too Low (<40)**: Flat image, poor feature separation
- **Optimal (50-65)**: Good dynamic range without clipping
- **Too High (>70)**: Blown highlights, crushed shadows

### Focus (Manual)
- **205**: Optimized for 0.5-1.5m distance (typical use case)
- **Auto Focus**: Causes lag, hunting, inconsistent quality
- **Manual Focus**: Stable, predictable, better for fixed-position cameras

## Camera Specifications (OV5640)

- **Sensor**: 5MP CMOS, 1.4μm pixel size
- **Resolution**: 2592×1944 maximum, 1920×1080 operational
- **Frame Rate**: 30fps @ 1080p (MJPEG), 10fps @ 1080p (YUYV)
- **Dynamic Range**: ~60dB (limited compared to professional cameras)
- **Aperture**: f/2.8 fixed (no iris control)
- **Focus Range**: 30cm to 3m (manual), optimal 0.5-1.5m
- **Lens**: Fixed focal length, no optical zoom

## References

- [edge-camera-quality-settings.md](edge-camera-quality-settings.md) - Comprehensive quality analysis
- [edge-camera-issues.md](edge-camera-issues.md) - Issue tracking and resolutions
- v4l2-ctl man page: `man v4l2-ctl`
- OV5640 datasheet: [OmniVision OV5640 Documentation]

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-08 | 1.0 | Initial document - settings configuration procedure |

---

**Last Updated**: February 8, 2026  
**Tested On**: Raspberry Pi 5, OV5640 USB Camera, Docker v29.2.1  
**Status**: ✅ Verified Working
