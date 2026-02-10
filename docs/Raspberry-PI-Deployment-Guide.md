# Raspberry Pi 5 Deployment Guide
## PPL Meta Edge Camera + Signage Simple Player

**Document Version:** 1.0  
**Last Updated:** February 2, 2026  
**Target Platform:** Raspberry Pi 5  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start - Headless Setup](#2-quick-start---headless-setup)
3. [Hardware Setup](#3-hardware-setup)
4. [Software Deployment Plan](#4-software-deployment-plan)
5. [Installation Guide](#5-installation-guide)
6. [Usage and Monitoring](#6-usage-and-monitoring)
7. [Troubleshooting](#7-troubleshooting)
8. [Appendix](#8-appendix)

---

## 1. Overview

This guide provides complete instructions for deploying the PPL Meta edge camera and signage player on a Raspberry Pi 5. The system captures video from an Arducam and displays digital signage content on a connected TV.

### System Architecture

```
┌─────────────────────────────────────────────┐
│         Raspberry Pi 5                       │
│                                              │
│  ┌──────────────────┐  ┌─────────────────┐ │
│  │  Edge Camera     │  │ Signage Player  │ │
│  │  (Docker)        │  │ (Docker)        │ │
│  │  Port: 9001      │  │ Port: 8009      │ │
│  └────────┬─────────┘  └────────┬────────┘ │
│           │                     │           │
└───────────┼─────────────────────┼───────────┘
            │                     │
    ┌───────▼────────┐    ┌──────▼──────┐
    │   Arducam      │    │   TV/HDMI   │
    │   (Camera)     │    │  (Display)  │
    └────────────────┘    └─────────────┘
            │                     │
            └─────────┬───────────┘
                      │
              ┌───────▼────────┐
              │  PPL Meta      │
              │  Platform      │
              │  (Backend)     │
              └────────────────┘
```

### Services Overview

| Service | Description | Port | Protocol |
|---------|-------------|------|----------|
| **Edge Camera** | Captures video from Arducam, streams to platform | 9001 | HTTP/WebSocket |
| **Signage Player** | Displays playlist content on TV | 8009 | HTTP/Flutter |

---

## 2. Quick Start - Headless Setup

> **Perfect Timing!** Since you haven't powered on your Raspberry Pi yet, you can do **EVERYTHING from your MacBook M1** without needing a TV, keyboard, or mouse. This section provides a streamlined headless setup path.

### 2.1 Setup Choice: Headless vs. Traditional

You have two options for initial setup:

#### ✅ **Option A: Headless Setup (RECOMMENDED - No TV/Keyboard/Mouse Needed)**

**What you need:**
- ✅ Your assembled Raspberry Pi 5 with Arducam (NOT powered on yet)
- ✅ MicroSD card (inserted or available)
- ✅ **Computer for SD card preparation:**
  - **Option 1:** Windows laptop with built-in SD card reader (EASIEST!)
  - **Option 2:** MacBook M1 Air + USB-C to SD card reader
- ✅ WiFi network credentials
- ✅ Power cable for Pi
- ✅ MacBook M1 Air for SSH/remote management (after Pi boots)

**What you DON'T need:**
- ❌ TV/Monitor
- ❌ Keyboard
- ❌ Mouse
- ❌ HDMI cable (until final deployment)

**How it works:**
1. Configure the SD card on your MacBook BEFORE first boot
2. Enable SSH and WiFi in the configuration
3. Power on the Pi (power cable only)
4. SSH into Pi from your MacBook
5. Do everything from VS Code on your MacBook

**Jump to:** [Section 2.2 - Headless Setup Instructions](#22-headless-setup-step-by-step)

---

#### Option B: Traditional Setup (With TV/Keyboard/Mouse)

**What you need:**
- All hardware including TV, HDMI cable, keyboard, mouse
- Connect everything before first boot
- Use Pi's desktop interface for setup

**Jump to:** [Section 2.5 - Traditional Setup Quick Steps](#25-traditional-setup-quick-steps)

---

### 2.5 Traditional Setup Quick Steps

> **You chose this path!** Follow these steps to initialize your RPi5 with keyboard, mouse, and TV, then continue from your MacBook M1.

#### Pre-Boot Checklist

Before powering on, ensure everything is connected:
- ✅ RPi5 in case with Arducam attached
- ✅ **SD card with Raspberry Pi OS written to it** (NOT blank!)
- ✅ HDMI cable from Pi's **HDMI 0 port** (closest to power) to TV
- ✅ USB keyboard plugged into Pi
- ✅ USB mouse plugged into Pi
- ✅ TV powered on and set to correct HDMI input
- ✅ Power cable ready (don't plug in yet)

**⚠️ IMPORTANT:** The SD card MUST have Raspberry Pi OS already written to it. A blank SD card will not boot!

---

#### Troubleshooting: "Boot Mode: USB-MSD (04)" Error

**If you see this message repeating every 30 seconds:**

```
Boot Mode: USB - MSD (04) order f
```

**This means: The Pi cannot find a bootable SD card.**

**STOP! Unplug power and follow these steps:**

**Problem 1: SD Card is Blank**
- If your SD card doesn't have Raspberry Pi OS on it, you need to write it first
- **Solution:** Follow [Section 2.2 - Headless Setup](#22-headless-setup-step-by-step) Steps 1-2 on your Windows laptop OR MacBook to write the OS
- Use Raspberry Pi Imager to write the OS image
- Then come back here

**Problem 2: SD Card Not Fully Inserted**
1. Unplug power from Pi
2. Remove SD card completely
3. Check for dust/debris in SD card slot
4. Re-insert SD card firmly until it clicks
5. It should be flush with the board, not sticking out
6. Plug power back in

**Problem 3: SD Card Write Failed**
- The OS write may have been corrupted
- **Solution:**
  1. Remove SD card from Pi
  2. Insert into Windows laptop or MacBook
  3. Format SD card (FAT32)
  4. Use Raspberry Pi Imager to write OS again
  5. Wait for verification to complete
  6. Safely eject
  7. Re-insert into Pi

**Problem 4: Incompatible or Defective SD Card**
- Not all SD cards work with Raspberry Pi
- **Requirements:**
  - Minimum 8GB (32GB+ recommended)
  - Class 10 or better (U1/U3)
  - Reputable brand (SanDisk, Samsung, Kingston)
- **Solution:** Try a different SD card

**Problem 5: SD Card in Wrong Slot**
- Raspberry Pi 5 has the SD card slot on the **bottom side**
- Make sure you're using the correct slot

---

#### Step 1: First Boot and Initial Setup

**⚠️ Only proceed if you have Raspberry Pi OS written to the SD card!**

1. **Plug in power cable** to Raspberry Pi
   - Green LED will start blinking
   - TV should show Raspberry Pi splash screen
   - Wait 30-60 seconds for boot

2. **Complete the Setup Wizard** on TV screen:
   
   **Welcome Screen:**
   - Click "Next"
   
   **Set Country:**
   - Country: Select your country
   - Language: English (US) or your preference
   - Timezone: Select your timezone
   - Click "Next"
   
   **Create User:**
   - Username: `pi` (recommended)
   - Password: Enter a secure password (you'll need this for SSH!)
   - Confirm password
   - Click "Next"
   
   **Set Up Screen:**
   - Check box if you see black borders (if applicable)
   - Click "Next"
   
   **Select WiFi Network:**
   - Select your WiFi network from the list
   - Click "Next"
   
   **Enter WiFi Password:**
   - Type your WiFi password
   - Click "Next"
   - Wait for connection (green checkmark appears)
   
   **Update Software:**
   - Click "Next" to download and install updates (RECOMMENDED)
   - This takes 5-15 minutes - wait for completion
   - Click "Restart" when prompted

3. **Wait for reboot** (30-60 seconds)
   - You'll see the desktop after reboot

---

#### Step 2: Enable SSH

SSH must be enabled to connect from your MacBook.

1. **Open Raspberry Pi Configuration:**
   - Click **Raspberry Pi menu** (top-left corner)
   - Go to: **Preferences → Raspberry Pi Configuration**

2. **Enable SSH:**
   - Click the **Interfaces** tab
   - Find **SSH** row
   - Click the **Enable** radio button
   - Click **OK**

3. **Reboot** (if prompted) or close the window

---

#### Step 3: Enable Camera

1. **Open Raspberry Pi Configuration** (if not still open):
   - Menu → Preferences → Raspberry Pi Configuration

2. **Enable Camera:**
   - Click the **Interfaces** tab
   - Find **Legacy Camera** row
   - Click **Enable**
   - Click **OK**
   - Click **Yes** to reboot

3. **Wait for reboot** (30-60 seconds)

---

#### Step 4: Find Your Pi's IP Address

You need the IP address to SSH from your MacBook.

1. **Hover mouse over WiFi icon** (top-right corner of screen)
   - A tooltip will show your IP address (e.g., `192.168.1.150`)
   - **Write this down!**

2. **Alternative method** - Open Terminal on the Pi:
   - Click **Raspberry Pi menu** → **Accessories** → **Terminal**
   - Type:
     ```bash
     hostname -I
     ```
   - First number shown is your IP address (e.g., `192.168.1.150`)
   - **Write this down!**

---

#### Step 5: Test Camera (Optional but Recommended)

1. **Open Terminal** on the Pi (if not already open):
   - Menu → Accessories → Terminal

2. **Check camera is detected:**
   ```bash
   vcgencmd get_camera
   ```
   - Should show: `supported=1 detected=1`

3. **Take a test photo:**
   ```bash
   libcamera-jpeg -o test.jpg
   ```
   - Should show preview window and take photo
   - If you see the camera view, it's working! ✅

---

#### Step 6: Connect from Your MacBook M1 Air

**Switch to your MacBook now!** You can leave the Pi running but won't need the keyboard/mouse/TV anymore.

1. **Open Terminal on MacBook:**
   - Applications → Utilities → Terminal
   - Or press `Cmd + Space`, type "Terminal", press Enter

2. **SSH into the Pi:**
   ```bash
   # Replace 192.168.1.150 with YOUR Pi's IP address from Step 4
   ssh pi@192.168.1.150
   ```

3. **First connection warning:**
   - You'll see: "Are you sure you want to continue connecting?"
   - Type: `yes` and press Enter

4. **Enter password:**
   - Type the password you created in Step 1
   - You won't see characters as you type (this is normal)
   - Press Enter

5. **You're in!** You should see:
   ```
   pi@raspberrypi:~ $
   ```

---

#### Step 7: Set Up SSH Keys (Recommended)

This allows you to connect without typing password every time.

**From your MacBook Terminal** (in a NEW terminal window, not the SSH session):

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter for all prompts (use defaults)

# Copy your public key to the Pi
# Replace 192.168.1.150 with your Pi's IP
ssh-copy-id pi@192.168.1.150
# Enter your password one last time

# Test passwordless login
ssh pi@192.168.1.150
# Should connect without asking for password!
```

---

#### Step 8: Set Up VS Code Remote (Highly Recommended)

Work on the Pi directly from VS Code on your MacBook!

1. **Install Remote-SSH Extension:**
   - Open VS Code on MacBook
   - Press `Cmd+Shift+X` (Extensions)
   - Search: "Remote - SSH"
   - Click Install on **"Remote - SSH"** by Microsoft

2. **Connect to Pi:**
   - Press `Cmd+Shift+P` (Command Palette)
   - Type: "Remote-SSH: Connect to Host"
   - Enter: `pi@192.168.1.150` (use your Pi's IP)
   - Select "Linux" as platform
   - Enter password (if you didn't set up SSH keys)
   - Wait for VS Code server to install (~1 minute)

3. **Open Terminal in VS Code:**
   - Press `` Ctrl+` `` or Terminal → New Terminal
   - You're now running commands on the Pi from VS Code!

4. **Open workspace:**
   - File → Open Folder
   - Navigate to `/home/pi`
   - Click OK

**Now you can edit files on Pi directly from your MacBook!**

---

#### Step 9: Continue with Docker Installation

You're all set! Now continue with:

**→ [Section 5.2 - Install Docker](#52-install-docker)**

All remaining steps will be done from your MacBook via SSH or VS Code!

**Optional:** You can now disconnect keyboard, mouse, and turn off TV. The Pi will stay running and connected to WiFi. You'll do everything else from your MacBook! 🎉

---

### 2.2 Headless Setup Step-by-Step

Follow these steps to set up your Pi completely from your MacBook M1.

#### Step 1: Prepare the SD Card

**✅ RECOMMENDED: Use Your Windows Laptop**

Since your Windows laptop has a **built-in SD card reader**, use it for this step - it's much easier!

**Steps:**
1. **Remove SD card from Pi** (if already inserted)
2. **Insert SD card into Windows laptop's SD card slot**
3. Windows will recognize it automatically

**Alternative: Use MacBook M1 Air**

If you prefer to use your MacBook:
- You'll need a **USB-C to SD card reader** adapter
- Insert SD card into reader, plug into MacBook's USB-C port
- macOS will mount the card automatically

**Either computer works!** The rest of the setup (SSH, Docker, etc.) will be done from your MacBook after the Pi boots.

#### Step 2: Write Raspberry Pi OS with Headless Configuration

1. **Download Raspberry Pi Imager** (if not installed):
   
   **On Windows Laptop:**
   - Visit: https://www.raspberrypi.com/software/
   - Download "Raspberry Pi Imager for Windows"
   - Install and launch the application
   
   **On MacBook (alternative):**
   ```bash
   # Visit: https://www.raspberrypi.com/software/
   # Or install via Homebrew:
   brew install --cask raspberry-pi-imager
   ```

2. **Launch Raspberry Pi Imager**

3. **Choose Operating System:**
   - Click "Choose OS"
   - Select: **"Raspberry Pi OS (64-bit)"** with Desktop
   - (Full desktop version needed for signage display)

4. **Choose Storage:**
   - Click "Choose Storage"
   - Select your SD card

5. **⚠️ CRITICAL: Configure Headless Settings** (click the gear icon ⚙️):

   **General Tab:**
   - ✅ Set hostname: `ppl-edge-device` (or your preference)
   - ✅ **Enable SSH** → Use password authentication
   - ✅ Set username and password:
     - Username: `pi`
     - Password: `your-secure-password` (remember this!)
   - ✅ **Configure wireless LAN:**
     - SSID: `Your-WiFi-Network-Name`
     - Password: `Your-WiFi-Password`
     - Wireless LAN country: `US` (or your country code)
   - ✅ Set locale settings:
     - Time zone: Your timezone
     - Keyboard layout: `us` (or your layout)

   **Services Tab:**
   - ✅ Enable SSH

6. **Write to SD Card:**
   - Click "Save" on settings
   - Click "Write"
   - Confirm (this will erase the SD card)
   - Wait 5-10 minutes for writing and verification

7. **Eject SD Card** safely
   - **Windows:** Right-click SD card → "Eject" in File Explorer
   - **macOS:** Drag SD card icon to Trash or right-click → Eject

💡 **From this point forward, use your MacBook M1 Air** for all SSH and management tasks.

#### Step 3: Insert SD Card and Power On Pi

1. **Insert SD card** into Raspberry Pi (if not already)
2. **DO NOT connect TV/keyboard/mouse** - not needed!
3. **Connect power cable** to Raspberry Pi
4. **Wait 1-2 minutes** for Pi to boot and connect to WiFi
5. **Green LED should blink** (activity indicator)

#### Step 4: Find Your Pi on the Network

**Switch to your MacBook M1 Air now** - all remaining steps use SSH from the MacBook.

Open Terminal on your MacBook (Applications → Utilities → Terminal) and try these methods:

```bash
# Method 1: Use hostname (easiest if mDNS works)
ping ppl-edge-device.local
# If you see replies, it's working! Press Ctrl+C to stop

# Method 2: If hostname doesn't work, scan your network
# First, find your network range
ifconfig | grep "inet " | grep -v 127.0.0.1

# Then scan (adjust IP range to match your network)
# Example: if your MacBook is 192.168.1.x, scan 192.168.1.0/24
sudo nmap -sn 192.168.1.0/24 | grep -B 2 "Raspberry Pi"

# Method 3: Check your router's web interface
# Look for connected device named "ppl-edge-device" or "raspberrypi"
# Note its IP address (e.g., 192.168.1.150)
```

**Example output when found:**
```
Nmap scan report for ppl-edge-device.local (192.168.1.150)
Host is up (0.0023s latency).
MAC Address: D8:3A:DD:XX:XX:XX (Raspberry Pi Foundation)
```

#### Step 5: SSH into Your Pi (From MacBook)

```bash
# Connect using hostname (if mDNS works)
ssh pi@ppl-edge-device.local

# OR connect using IP address (from step 4)
ssh pi@192.168.1.150

# First time connection will show fingerprint warning
# Type: yes

# Enter the password you set in Raspberry Pi Imager
```

**You're in!** You should see:
```
pi@ppl-edge-device:~ $
```

#### Step 6: Update System (From MacBook via SSH)

```bash
# Update package list and upgrade system
sudo apt update && sudo apt upgrade -y

# This may take 10-20 minutes
# You'll see progress in your MacBook terminal

# Reboot to apply updates
sudo reboot

# Wait 1 minute, then reconnect
ssh pi@ppl-edge-device.local
```

#### Step 7: Enable Camera Interface

```bash
# From SSH session on your MacBook
sudo raspi-config
```

Navigation:
1. Use arrow keys to navigate
2. Select: `Interface Options` → Press Enter
3. Select: `Camera` → Press Enter  
4. Select: `Yes` to enable → Press Enter
5. Select: `Finish` → Press Enter
6. Select: `Yes` to reboot → Press Enter

Wait 1 minute and reconnect:
```bash
ssh pi@ppl-edge-device.local
```

#### Step 8: Verify Camera (From MacBook via SSH)

```bash
# Check camera is detected
vcgencmd get_camera
# Should show: supported=1 detected=1

# List camera devices
libcamera-hello --list-cameras

# Take test photo (optional)
libcamera-jpeg -o test.jpg
# Photo saved on Pi, you can download it:
# exit
# scp pi@ppl-edge-device.local:~/test.jpg ~/Desktop/
# ssh pi@ppl-edge-device.local
```

#### Step 9: Set Up VS Code Remote Development (Optional but Highly Recommended)

Working from VS Code makes everything easier!

1. **Install Remote-SSH Extension in VS Code:**
   - Open VS Code on your MacBook
   - Press `Cmd+Shift+X` (Extensions)
   - Search: "Remote - SSH"
   - Install: **"Remote - SSH"** by Microsoft

2. **Connect to Raspberry Pi:**
   - Press `Cmd+Shift+P` (Command Palette)
   - Type: "Remote-SSH: Connect to Host"
   - Enter: `pi@ppl-edge-device.local` (or IP address)
   - New VS Code window opens
   - Select "Linux" as platform
   - Enter your password
   - Wait for VS Code to install server components (first time only, ~1 minute)

3. **Open Terminal in VS Code:**
   - Press `` Ctrl+` `` or Terminal → New Terminal
   - You now have Pi's terminal inside VS Code!

4. **Open Workspace:**
   - File → Open Folder
   - Navigate to: `/home/pi`
   - Click OK

**Now you can:**
- ✅ Edit files on Pi directly from MacBook
- ✅ Run commands in integrated terminal
- ✅ View logs with syntax highlighting
- ✅ Use all VS Code features on Pi files
- ✅ No more SSH command line needed!

#### Step 10: Transfer Deployment Files

From your MacBook terminal (or VS Code terminal connected to Pi):

```bash
# Option A: From MacBook's local terminal (if you have source code)
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Transfer source directories
scp -r ppl-meta-edge-camera pi@ppl-edge-device.local:~/
scp -r ppl-meta-signage-simple-player pi@ppl-edge-device.local:~/

# OR use rsync (faster, skips unchanged files)
rsync -avz --progress ppl-meta-edge-camera/ pi@ppl-edge-device.local:~/ppl-meta-edge-camera/
rsync -avz --progress ppl-meta-signage-simple-player/ pi@ppl-edge-device.local:~/ppl-meta-signage-simple-player/

# Option B: From VS Code terminal (connected to Pi)
# Create deployment directory
mkdir -p ~/ppl-meta-deployment
cd ~/ppl-meta-deployment
```

#### Step 11: Continue with Installation

Now that your Pi is set up and you're connected from your MacBook, continue with:

- **[Section 5.2 - Install Docker](#52-install-docker)** onwards

You'll do everything from your MacBook terminal (or VS Code) without ever touching the Pi physically!

---

### 2.3 When to Connect the TV

You only need to connect the TV when:
- ✅ **Testing signage display** - After Docker containers are running
- ✅ **Final deployment** - When putting system into production

For all setup, configuration, and Docker installation, TV is **not needed**!

---

### 2.4 Summary: Your Current Situation

✅ **What you have:**
- Assembled Pi 5 with Arducam
- SD card inserted
- Never powered on

✅ **What to do:**
1. Follow [Section 2.2 - Headless Setup](#22-headless-setup-step-by-step) above
2. Configure SD card BEFORE first power-on (Step 2)
3. Power on Pi (Step 3)
4. SSH from MacBook (Steps 4-5)
5. Complete all setup from MacBook (Steps 6-10)
6. Skip Section 3 hardware assembly (already done)
7. Continue with [Section 5.2 - Install Docker](#52-install-docker)

✅ **What you DON'T need right now:**
- TV/Monitor
- Keyboard
- Mouse

**You'll connect the TV later** when testing the signage player display!

---

## 3. Hardware Setup

### 3.1 Required Components

- ✅ Raspberry Pi 5 (4GB or 8GB RAM recommended)
- ✅ Raspberry Pi 5 case (with fan recommended for cooling)
- ✅ Arducam camera module
- ✅ Camera cable (CSI cable)
- ✅ Arducam camera case (optional but recommended)
- ✅ TV with HDMI input
- ✅ HDMI cable (standard or micro HDMI to HDMI, depending on your RPi case)
- ✅ Power supply for Raspberry Pi 5 (5V 5A USB-C recommended)
- ✅ MicroSD card (32GB+ recommended, Class 10 or better)
- ✅ Keyboard and mouse (for initial setup)
- ✅ Ethernet cable or WiFi access

### 3.2 Hardware Assembly (Step-by-Step)

#### Step 1: Install Raspberry Pi in Case

1. **Open the case**: Remove the top cover of your Raspberry Pi 5 case
2. **Check orientation**: Note the GPIO pins location (40-pin header) and ensure case alignment
3. **Place the Pi**: Gently set the Raspberry Pi 5 into the case, aligning mounting holes
4. **Secure with screws**: Use provided screws to secure the Pi to the case bottom
5. **Attach heatsinks** (if included): Place heatsinks on the CPU and other chips
6. **Connect fan** (if included): 
   - Connect fan power cable to GPIO pins (usually 5V and GND)
   - Standard connection: Red wire to Pin 4 (5V), Black wire to Pin 6 (GND)

#### Step 2: Install Arducam Camera

1. **Locate the CSI camera connector** on your Raspberry Pi 5:
   - It's between the HDMI ports and the USB ports
   - Small black connector with a white/beige ribbon cable slot

2. **Prepare the CSI cable**:
   - Handle carefully - the ribbon cable is fragile
   - Note the blue tab side and the metal contacts side

3. **Connect camera cable to Raspberry Pi**:
   - Gently pull up the black tab on the CSI connector (it should lift up, not pull out)
   - Insert the ribbon cable with **metal contacts facing the USB ports**
   - The blue tab should face the HDMI ports
   - Push the black tab down to lock the cable in place

4. **Connect camera cable to Arducam**:
   - Lift the connector tab on the camera module
   - Insert ribbon cable with **metal contacts facing the camera lens side**
   - Push down the tab to lock

5. **Mount Arducam in case** (if using Arducam case):
   - Place camera module in the camera case
   - Ensure lens is visible through the case opening
   - Secure with provided screws
   - Route cable neatly to avoid pinching

6. **Position camera**:
   - Place camera where it can capture the desired view
   - Ensure cable has enough slack but isn't strained
   - Camera can be mounted using adhesive or mounting brackets

#### Step 3: Connect Display (TV)

1. **Locate HDMI port** on Raspberry Pi 5:
   - Two micro HDMI ports on the Pi
   - Use **HDMI 0** (the one closest to the power port) for primary display

2. **Connect HDMI cable**:
   - If your case has HDMI passthrough: Connect micro HDMI cable to Pi, route through case
   - Connect other end to TV HDMI input
   - Note which HDMI input number on TV (e.g., HDMI 1, HDMI 2)

3. **Power on TV**: Switch to the correct HDMI input

#### Step 4: Insert MicroSD Card

1. **Prepare SD card** (see Section 4.1 for OS installation)
2. **Insert SD card**: 
   - Locate SD card slot on bottom/side of Raspberry Pi
   - Insert with contacts facing the PCB
   - Push until it clicks into place

#### Step 5: Connect Power and Peripherals

1. **Connect keyboard and mouse**: Use USB ports on Raspberry Pi
2. **Connect Ethernet** (recommended for initial setup): Plug into Ethernet port
3. **Connect power last**: 
   - Connect USB-C power cable to Raspberry Pi
   - Plug power adapter into wall outlet
   - Pi should boot automatically (green LED will flash)

#### Step 6: First Boot

1. **Wait for boot**: First boot takes 1-2 minutes
2. **TV should display**: Raspberry Pi OS boot screen, then desktop
3. **Complete initial setup**: Follow on-screen Raspberry Pi OS setup wizard
   - Set country, language, timezone
   - Set password for `pi` user
   - Connect to WiFi (if not using Ethernet)
   - Update software (recommended)

### 3.3 Hardware Diagram

```
                    Top View of Raspberry Pi 5
    
    ┌─────────────────────────────────────────────┐
    │                                              │
    │  [PWR LED]                      [ACT LED]   │
    │                                              │
    │  ┌──────┐  ┌──────┐                         │
    │  │HDMI 0│  │HDMI 1│  [Camera CSI Connector] │
    │  └──────┘  └──────┘          ↑              │
    │                               │              │
    │                          Ribbon Cable        │
    │                                              │
    │  [USB-C]                                     │
    │   Power     [USB 2.0] [USB 3.0] [USB 3.0]  │
    │                                              │
    │  [Ethernet]                    [GPIO Pins]  │
    │                                   (40-pin)  │
    │                                              │
    │                        [MicroSD Slot]       │
    └─────────────────────────────────────────────┘
                   (on bottom side)
```

---

## 4. Software Deployment Plan

### 4.1 Deployment Strategy

We will deploy both services using **Docker containers** for:
- ✅ Consistent environment across devices
- ✅ Easy updates and rollbacks
- ✅ Isolated dependencies
- ✅ Simple monitoring and management

### 4.2 Docker Images

#### Edge Camera Docker Image

**Base:** `python:3.11-slim-bullseye`  
**Key Components:**
- OpenCV with camera support
- FastAPI for management API
- Camera streaming libraries
- Health check endpoint

**Dockerfile Location:** `ppl-meta-edge-camera/Dockerfile` (to be created)

#### Signage Player Docker Image

**Base:** `ubuntu:22.04` (for Flutter/GUI support)  
**Key Components:**
- Flutter SDK
- Linux GUI libraries (X11/Wayland)
- Video playback codecs
- HTTP server for remote control

**Dockerfile Location:** `ppl-meta-signage-simple-player/Dockerfile` (to be created)

### 4.3 Docker Compose Configuration

A `docker-compose.yml` file will orchestrate both services:

```yaml
version: '3.8'

services:
  edge-camera:
    image: ppl-meta-edge-camera:latest
    container_name: ppl-edge-camera
    restart: unless-stopped
    privileged: true  # For camera access
    devices:
      - /dev/video0:/dev/video0  # Camera device
    ports:
      - "9001:9001"
    environment:
      - DEVICE_ID=${CAMERA_DEVICE_ID:-edge-camera-rpi5}
      - PLATFORM_CAMERAS_URL=${PLATFORM_CAMERAS_URL}
      - PLATFORM_DISCOVERY_URL=${PLATFORM_DISCOVERY_URL}
      - CAMERA_DEVICE_ID=0
    volumes:
      - ./config/camera-config.yaml:/app/config/default.yaml:ro
      - camera-logs:/app/logs
    networks:
      - ppl-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  signage-player:
    image: ppl-meta-signage-player:latest
    container_name: ppl-signage-player
    restart: unless-stopped
    privileged: true  # For display access
    environment:
      - DISPLAY=:0
      - DEVICE_ID=${SIGNAGE_DEVICE_ID:-signage-player-rpi5}
      - DISCOVERY_SERVICE_URL=${PLATFORM_DISCOVERY_URL}
      - MEDIA_SERVICE_URL=${PLATFORM_MEDIA_URL}
      - GATEWAY_URL=${PLATFORM_GATEWAY_URL}
    ports:
      - "8009:8009"
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw  # X11 display
      - signage-data:/app/data
      - signage-logs:/app/logs
    networks:
      - ppl-network
    depends_on:
      - edge-camera
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8009/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  ppl-network:
    driver: bridge

volumes:
  camera-logs:
  signage-data:
  signage-logs:
```

### 4.4 Required Environment Variables

Create a `.env` file in the deployment directory:

```bash
# Device Identifiers
CAMERA_DEVICE_ID=edge-camera-rpi5-001
SIGNAGE_DEVICE_ID=signage-player-rpi5-001

# Platform Services URLs (adjust to your backend)
PLATFORM_CAMERAS_URL=http://YOUR_BACKEND_IP:8005
PLATFORM_DISCOVERY_URL=http://YOUR_BACKEND_IP:8010
PLATFORM_MEDIA_URL=http://YOUR_BACKEND_IP:8000
PLATFORM_GATEWAY_URL=http://YOUR_BACKEND_IP:8080

# Camera Settings
CAMERA_RESOLUTION_WIDTH=1280
CAMERA_RESOLUTION_HEIGHT=720
CAMERA_FPS=15

# Optional: API Keys
PLATFORM_API_KEY=your-api-key-here
```

### 4.5 Build Process

The Docker images will be built on a development machine and transferred to the Raspberry Pi, OR built directly on the Pi if sufficient time/resources are available.

**Option A: Build on Development Machine (Recommended)**
```bash
# Cross-compile for ARM64
docker buildx build --platform linux/arm64 -t ppl-meta-edge-camera:latest ./ppl-meta-edge-camera
docker buildx build --platform linux/arm64 -t ppl-meta-signage-player:latest ./ppl-meta-signage-simple-player

# Save and transfer
docker save ppl-meta-edge-camera:latest | gzip > edge-camera-arm64.tar.gz
docker save ppl-meta-signage-player:latest | gzip > signage-player-arm64.tar.gz

# Transfer to Raspberry Pi
scp edge-camera-arm64.tar.gz pi@raspberrypi.local:~/
scp signage-player-arm64.tar.gz pi@raspberrypi.local:~/
```

**Option B: Build Directly on Raspberry Pi**
```bash
# Build on the Pi (takes longer but simpler)
cd ~/ppl-meta-deployment
docker-compose build
```

---

## 5. Installation Guide

### 5.0 Remote Setup from MacBook M1

You can set up and manage your Raspberry Pi 5 directly from your MacBook M1 without needing a separate keyboard, mouse, or monitor. There are two connection methods:

#### Method A: WiFi Connection (Recommended - Easiest)

This method allows you to connect to the Pi over your local WiFi network.

**Step 1: Configure WiFi in Raspberry Pi Imager**

When writing the OS image (see Section 4.1), click the gear icon in Raspberry Pi Imager and configure:
- ✅ Enable SSH
- ✅ Set username/password: `pi` / `your-password`
- ✅ Configure WiFi: Enter your network SSID and password
- ✅ Set wireless LAN country

**Step 2: Boot Pi and Find IP Address**

After writing the SD card and booting the Pi (power only, no peripherals needed):

```bash
# From your MacBook, find the Pi on your network (wait 1-2 minutes after boot)
# Option 1: Using hostname (if mDNS works)
ping raspberrypi.local

# Option 2: Scan your network for the Pi
sudo nmap -sn 192.168.1.0/24 | grep -B 2 "Raspberry Pi"

# Option 3: Check your router's DHCP client list
# Look for device named "raspberrypi" or with Raspberry Pi Foundation MAC prefix
```

**Step 3: SSH from MacBook**

```bash
# Connect via hostname (if mDNS works)
ssh pi@raspberrypi.local

# Or connect via IP address
ssh pi@192.168.1.XXX

# First connection will ask to verify fingerprint, type 'yes'
# Enter the password you set in Raspberry Pi Imager
```

**Step 4: Set Up SSH Keys (Optional but Recommended)**

```bash
# From your MacBook, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy your public key to the Pi
ssh-copy-id pi@raspberrypi.local

# Now you can SSH without password
ssh pi@raspberrypi.local
```

#### Method B: USB-C Connection (Direct Cable - Advanced)

**⚠️ Not Recommended for MacBook M1 Air** - This method is complex with RPi 5 and your MacBook's limited USB-C ports. Use **Method A (WiFi)** instead for simplicity.

<details>
<summary>Click to expand USB-C connection method (Advanced Users Only)</summary>

You can theoretically connect the Pi directly to your MacBook using USB-C, but it's complicated:

**Limitations with MacBook M1 Air:**
- Only 2 USB-C ports (one will be needed for power to Pi, one for connection)
- RPi 5's USB-C port is primarily for power input
- USB gadget mode on RPi 5 is less stable than on earlier models
- Requires manual network configuration

**If you still want to try:**

**Step 1: Enable USB Gadget Mode**

After writing the OS with Raspberry Pi Imager (with SSH enabled), before first boot:

1. **Edit config.txt on the SD card**:
   ```bash
   # From MacBook, with SD card still inserted after imaging
   # Mount the boot partition (it will auto-mount)
   echo "dtoverlay=dwc2" | sudo tee -a /Volumes/bootfs/config.txt
   ```

2. **Edit cmdline.txt**:
   ```bash
   # Open cmdline.txt (all on one line!)
   sudo nano /Volumes/bootfs/cmdline.txt
   
   # After "rootwait", add: modules-load=dwc2,g_ether
   # Example:
   # ... rootwait modules-load=dwc2,g_ether quiet init=/usr/lib/...
   ```

3. **Enable SSH** (create empty file):
   ```bash
   touch /Volumes/bootfs/ssh
   ```

4. **Eject SD card and insert into Pi**

**Step 2: Connect USB-C Cable**

1. Connect USB-C cable from Pi's **USB-C power port** to your MacBook's USB-C port
2. Pi will boot and appear as a network device

**Step 3: Connect from MacBook**

```bash
# Pi will have default IP: 169.254.X.X (link-local)
# Or use mDNS
ssh pi@raspberrypi.local

# If that doesn't work, find the USB network interface
ifconfig | grep -A 3 "169.254"

# Connect via IP
ssh pi@169.254.X.X
```

⚠️ **Note**: USB gadget mode provides network only - you still need separate power if your MacBook's USB port doesn't provide enough power (5V 3A minimum). The Pi 5's USB-C port is primarily a power port, so for USB networking you may need a powered USB hub or separate power adapter.

</details>

**Recommendation**: Skip Method B and use **Method A (WiFi)** - it's much simpler and more reliable!

#### Method C: Ethernet Cable Connection (Alternative)
   - System Preferences → Sharing → Internet Sharing
   - Share WiFi over Ethernet
3. SSH to Pi (should get IP from MacBook):
   ```bash
   ssh pi@raspberrypi.local
   ```

#### Working from VS Code IDE

Once SSH is set up, you can work directly from VS Code on your MacBook:

**Step 1: Install Remote-SSH Extension**

```bash
# Open VS Code on your MacBook
# Install extension: "Remote - SSH" by Microsoft
# Extension ID: ms-vscode-remote.remote-ssh
```

**Step 2: Connect to Raspberry Pi**

1. Press `Cmd+Shift+P` → "Remote-SSH: Connect to Host"
2. Enter: `pi@raspberrypi.local` (or IP address)
3. Select "Linux" as the platform
4. VS Code will install server components on the Pi (first time only)

**Step 3: Open Remote Workspace**

1. Once connected, click "Open Folder"
2. Navigate to `/home/pi/ppl-meta-deployment`
3. You can now edit files, run terminal commands, and manage the Pi from VS Code!

**Step 4: Transfer Project Files**

```bash
# From MacBook terminal (in your ppl-meta-code directory)

# Transfer source code to Pi
scp -r ppl-meta-edge-camera pi@raspberrypi.local:~/
scp -r ppl-meta-signage-simple-player pi@raspberrypi.local:~/

# Or use rsync for faster transfer (skips unchanged files)
rsync -avz --progress ppl-meta-edge-camera/ pi@raspberrypi.local:~/ppl-meta-edge-camera/
rsync -avz --progress ppl-meta-signage-simple-player/ pi@raspberrypi.local:~/ppl-meta-signage-simple-player/

# Transfer deployment configs
scp docker-compose.yml pi@raspberrypi.local:~/ppl-meta-deployment/
scp .env pi@raspberrypi.local:~/ppl-meta-deployment/
```

**Step 5: Use Integrated Terminal**

In VS Code's remote session, you can:
- Edit configuration files directly
- Run Docker commands
- View logs in real-time
- Debug issues
- All from your MacBook!

#### File Synchronization with VS Code

For ongoing development, you can use VS Code's Remote-SSH to:
1. Edit files directly on the Pi (changes are saved in real-time)
2. Use Git from the Pi to pull updates
3. Use VS Code's built-in terminal to run commands
4. View and debug logs with VS Code's log viewer

#### Quick Setup Summary

**For WiFi Connection (RECOMMENDED):**
```bash
# 1. ON WINDOWS LAPTOP: Insert SD card, run Raspberry Pi Imager
#    Enable SSH + WiFi in settings (gear icon)
# 2. Eject SD card from Windows laptop
# 3. Insert SD card into Pi, connect power (no peripherals)
# 4. Wait 1-2 minutes for boot
# 5. ON MACBOOK M1 AIR: Open Terminal
ping ppl-edge-device.local
ssh pi@ppl-edge-device.local
# 6. Continue with headless setup from MacBook!
```

**For VS Code Remote Development (After WiFi Setup):**
```bash
# 1. Install "Remote - SSH" extension in VS Code
# 2. Cmd+Shift+P → "Remote-SSH: Connect to Host"
# 3. Enter: pi@ppl-edge-device.local
# 4. Open folder: /home/pi/ppl-meta-deployment
# 5. Work directly on Pi from MacBook!
```

**Required Accessories:**
- ✅ **Windows laptop with SD card reader** - Easiest for writing OS to SD card
  - OR USB-C to SD card reader (if using MacBook for SD card prep)
- ⚠️ USB-C to Ethernet adapter - Only if using Method C (optional)
- ⚠️ USB-C hub - Helpful if you need multiple ports simultaneously (optional)

---

### 5.1 Prepare Raspberry Pi OS

#### Step 1: Install Raspberry Pi OS

1. **Download Raspberry Pi Imager**: https://www.raspberrypi.com/software/
2. **Choose OS**: Raspberry Pi OS (64-bit) with Desktop
3. **Select SD Card**: Your microSD card
4. **Configure Settings** (click gear icon):
   - Set hostname: `ppl-edge-device`
   - Enable SSH
   - Set username/password: `pi` / `your-password`
   - Configure WiFi (optional)
5. **Write to SD Card**: Takes 5-10 minutes

#### Step 2: Initial Raspberry Pi Setup

1. **Boot the Pi**: Insert SD card and power on
2. **Complete setup wizard** (if not configured in imager)
3. **Update system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo reboot
   ```

#### Step 3: Enable Camera Interface

1. **Enable camera**:
   ```bash
   sudo raspi-config
   ```
   - Navigate to: `Interface Options` → `Camera` → `Enable`
   - Reboot when prompted

2. **Verify camera**:
   ```bash
   vcgencmd get_camera
   # Should show: supported=1 detected=1
   
   # Test camera capture
   libcamera-hello --list-cameras
   libcamera-jpeg -o test.jpg
   ```

### 5.2 Install Docker

#### Step 1: Install Docker Engine

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Logout and login for group changes to take effect
exit
# SSH back in or reboot
```

#### Step 2: Install Docker Compose

```bash
# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 5.3 Prepare Deployment Files

#### Step 1: Create Deployment Directory

```bash
# Create deployment directory
mkdir -p ~/ppl-meta-deployment
cd ~/ppl-meta-deployment

# Create subdirectories
mkdir -p config logs data
```

#### Step 2: Create Dockerfiles

**Create Edge Camera Dockerfile:**

```bash
nano ~/ppl-meta-deployment/Dockerfile.edge-camera
```

Paste the following content:

```dockerfile
# Edge Camera Dockerfile for Raspberry Pi 5 (ARM64)
FROM python:3.11-slim-bullseye

# Install system dependencies for OpenCV and camera
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# Run application
CMD ["python", "src/main.py"]
```

**Create Signage Player Dockerfile:**

```bash
nano ~/ppl-meta-deployment/Dockerfile.signage-player
```

Paste the following content:

```dockerfile
# Signage Player Dockerfile for Raspberry Pi 5 (ARM64)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    libglu1-mesa \
    libgtk-3-0 \
    libglib2.0-0 \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    libmpv1 \
    mpv \
    xdotool \
    wmctrl \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter
ENV FLUTTER_HOME=/opt/flutter
ENV PATH="$FLUTTER_HOME/bin:$PATH"

RUN git clone https://github.com/flutter/flutter.git -b stable --depth 1 $FLUTTER_HOME && \
    flutter precache --linux && \
    flutter config --enable-linux-desktop && \
    flutter doctor

# Set working directory
WORKDIR /app

# Copy application files
COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get

COPY . .

# Build Flutter application for Linux
RUN flutter build linux --release

# Expose port
EXPOSE 8009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Run application
CMD ["./build/linux/x64/release/bundle/signage_simple_player"]
```

#### Step 3: Create Docker Compose File

```bash
nano ~/ppl-meta-deployment/docker-compose.yml
```

Paste the Docker Compose configuration from Section 3.3.

#### Step 4: Create Environment File

```bash
nano ~/ppl-meta-deployment/.env
```

Paste the environment configuration from Section 3.4, adjusting values for your setup.

#### Step 5: Create Camera Configuration

```bash
nano ~/ppl-meta-deployment/config/camera-config.yaml
```

```yaml
device:
  id: edge-camera-rpi5-001
  name: "Edge Camera - Living Room"
  location: "Living Room"
  type: edge

camera:
  device_id: 0  # /dev/video0
  resolution:
    width: 1280
    height: 720
  fps: 15
  format: mjpeg
  buffer_size: 10

platform:
  cameras_url: http://YOUR_BACKEND_IP:8005
  discovery_url: http://YOUR_BACKEND_IP:8010
  health_check_interval: 30
  max_reconnect_attempts: 10
  reconnect_interval: 5

server:
  host: 0.0.0.0
  port: 9001

stream:
  encoding: mjpeg
  quality: 80
  chunk_size: 4096

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 5.4 Build and Deploy

#### Option A: Load Pre-built Images (Recommended)

If you built images on a development machine and transferred them:

```bash
cd ~/ppl-meta-deployment

# Load images
docker load < edge-camera-arm64.tar.gz
docker load < signage-player-arm64.tar.gz

# Verify images
docker images | grep ppl-meta
```

#### Option B: Build Images on Raspberry Pi

If building directly on the Pi:

```bash
cd ~/ppl-meta-deployment

# Copy source code (you'll need to transfer the source directories)
# Assume they're in ~/ppl-meta-code/

# Build edge camera
docker build -f Dockerfile.edge-camera \
    -t ppl-meta-edge-camera:latest \
    ~/ppl-meta-code/ppl-meta-edge-camera

# Build signage player
docker build -f Dockerfile.signage-player \
    -t ppl-meta-signage-player:latest \
    ~/ppl-meta-code/ppl-meta-signage-simple-player
```

⚠️ **Note**: Building on Raspberry Pi can take 30-60 minutes or more depending on the model.

### 5.5 Configure Display Access

For the signage player to display on the TV:

```bash
# Allow Docker to access X11 display
xhost +local:docker

# Make this permanent by adding to ~/.bashrc
echo "xhost +local:docker" >> ~/.bashrc
```

### 5.6 Start Services

```bash
cd ~/ppl-meta-deployment

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### 5.7 Configure Autostart on Boot

```bash
# Enable Docker Compose to start on boot
sudo nano /etc/systemd/system/ppl-meta-services.service
```

Add the following content:

```ini
[Unit]
Description=PPL Meta Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/ppl-meta-deployment
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=pi

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ppl-meta-services
sudo systemctl start ppl-meta-services
```

---

## 6. Usage and Monitoring

### 6.1 Docker Monitoring

#### Basic Docker Commands

```bash
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# View container logs
docker logs ppl-edge-camera
docker logs ppl-signage-player

# Follow logs in real-time
docker logs -f ppl-edge-camera

# View resource usage
docker stats

# Restart a service
docker restart ppl-edge-camera

# Stop all services
docker compose down

# Start all services
docker compose up -d
```

#### Container Health Checks

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' ppl-edge-camera
docker inspect --format='{{.State.Health.Status}}' ppl-signage-player

# View detailed health check logs
docker inspect ppl-edge-camera | grep -A 10 Health
```

#### Resource Monitoring

```bash
# Real-time resource usage
docker stats

# View specific container stats
docker stats ppl-edge-camera ppl-signage-player

# Disk usage
docker system df

# Cleanup unused resources
docker system prune -a
```

### 6.2 Edge Camera Monitoring

#### Health Check Endpoint

```bash
# Basic health check
curl http://localhost:9001/health

# Expected response:
{
  "status": "healthy",
  "service": "edge-camera",
  "version": "1.0.0",
  "timestamp": "2026-02-02T10:30:00Z"
}
```

#### Status Endpoint

```bash
# Get detailed status
curl http://localhost:9001/status

# Expected response:
{
  "device_id": "edge-camera-rpi5-001",
  "camera": {
    "connected": true,
    "device": "/dev/video0",
    "resolution": "1280x720",
    "fps": 15,
    "streaming": true
  },
  "platform": {
    "cameras_service": "connected",
    "discovery_service": "registered",
    "last_heartbeat": "2026-02-02T10:29:50Z"
  },
  "uptime_seconds": 86400
}
```

#### Camera Testing

```bash
# Test camera capture (from Raspberry Pi terminal)
libcamera-jpeg -o test_capture.jpg

# Check camera device
ls -la /dev/video*

# View camera info
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --all
```

#### Edge Camera Logs

```bash
# View logs
docker logs ppl-edge-camera

# Follow logs
docker logs -f ppl-edge-camera

# View last 100 lines
docker logs --tail 100 ppl-edge-camera

# View logs with timestamps
docker logs -t ppl-edge-camera
```

### 6.3 Signage Player Monitoring

#### Health Check Endpoint

```bash
# Basic health check
curl http://localhost:8009/health

# Expected response:
{
  "status": "healthy",
  "service": "signage-simple-player",
  "version": "1.0.0",
  "timestamp": "2026-02-02T10:30:00Z"
}
```

#### Status Endpoint

```bash
# Get detailed playback status
curl http://localhost:8009/api/v1/status

# Expected response:
{
  "device_id": "signage-player-rpi5-001",
  "is_playing": true,
  "current_playlist": {
    "id": "playlist-123",
    "name": "Store Front Display",
    "video_count": 5
  },
  "current_video": {
    "index": 2,
    "id": "video-456",
    "title": "Product Showcase",
    "progress": 0.65,
    "duration_seconds": 150
  },
  "last_sync": "2026-02-02T10:15:00Z"
}
```

#### Control Endpoints

```bash
# Start playback
curl -X POST http://localhost:8009/api/v1/playback/start

# Pause playback
curl -X POST http://localhost:8009/api/v1/playback/pause

# Stop playback
curl -X POST http://localhost:8009/api/v1/playback/stop

# Next video
curl -X POST http://localhost:8009/api/v1/playback/next

# Previous video
curl -X POST http://localhost:8009/api/v1/playback/previous

# Manual sync
curl -X POST http://localhost:8009/api/v1/sync
```

#### Playback History

```bash
# Get playback history
curl http://localhost:8009/api/v1/history?limit=20

# Get history for specific playlist
curl "http://localhost:8009/api/v1/history?playlist_id=playlist-123&limit=50"
```

#### Display Monitoring

```bash
# Check display output
xrandr  # Shows connected displays

# Verify HDMI connection
tvservice -s

# Test display with sample video
mpv --fs /path/to/test/video.mp4
```

#### Signage Player Logs

```bash
# View logs
docker logs ppl-signage-player

# Follow logs
docker logs -f ppl-signage-player

# View last 100 lines
docker logs --tail 100 ppl-signage-player
```

### 6.4 System Monitoring

#### Raspberry Pi System Status

```bash
# CPU temperature
vcgencmd measure_temp

# CPU frequency
vcgencmd measure_clock arm

# Memory usage
free -h

# Disk usage
df -h

# Overall system status
htop  # Install with: sudo apt install htop
```

#### Network Monitoring

```bash
# Check network connectivity
ping -c 4 google.com

# Check connection to backend
ping -c 4 YOUR_BACKEND_IP

# View network interfaces
ip addr show

# Test port accessibility
nc -zv YOUR_BACKEND_IP 8005  # Cameras service
nc -zv YOUR_BACKEND_IP 8010  # Discovery service
```

#### Automated Health Check Script

Create a monitoring script:

```bash
nano ~/health-check.sh
```

```bash
#!/bin/bash

echo "================================"
echo "PPL Meta Services Health Check"
echo "================================"
echo ""

# Docker status
echo "Docker Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Edge Camera health
echo "Edge Camera:"
curl -s http://localhost:9001/health | python3 -m json.tool || echo "❌ Not responding"
echo ""

# Signage Player health
echo "Signage Player:"
curl -s http://localhost:8009/health | python3 -m json.tool || echo "❌ Not responding"
echo ""

# System resources
echo "System Resources:"
echo "  Temperature: $(vcgencmd measure_temp)"
echo "  Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "  Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
echo ""

echo "================================"
```

Make executable and run:

```bash
chmod +x ~/health-check.sh
./health-check.sh
```

#### Set Up Monitoring Cron Job

```bash
# Edit crontab
crontab -e

# Add health check every 5 minutes
*/5 * * * * /home/pi/health-check.sh >> /home/pi/health-check.log 2>&1

# Add daily log rotation
0 0 * * * mv /home/pi/health-check.log /home/pi/health-check.log.$(date +\%Y\%m\%d) && touch /home/pi/health-check.log
```

### 6.5 Remote Monitoring

#### SSH Access

```bash
# SSH from remote machine
ssh pi@raspberrypi.local
# or
ssh pi@<RASPBERRY_PI_IP>

# Use SSH keys for passwordless access
ssh-copy-id pi@raspberrypi.local
```

#### Remote Dashboard (Optional)

You can set up a simple web dashboard using Portainer:

```bash
# Install Portainer
docker volume create portainer_data
docker run -d -p 9000:9000 -p 9443:9443 \
    --name portainer --restart=always \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer-ce:latest

# Access dashboard at:
# http://raspberrypi.local:9000
```

---

## 7. Troubleshooting

### 7.1 Camera Issues

#### Problem: Camera not detected

```bash
# Check camera connection
vcgencmd get_camera

# Should show: supported=1 detected=1
# If detected=0, check physical connection

# List video devices
ls -la /dev/video*

# Test with libcamera
libcamera-hello --list-cameras
```

**Solutions:**
1. Ensure camera cable is properly connected (metal contacts facing correct direction)
2. Enable camera in `raspi-config`
3. Reboot after enabling camera
4. Check cable for damage

#### Problem: Camera permission denied in Docker

```bash
# Check container has access
docker exec ppl-edge-camera ls -la /dev/video0
```

**Solutions:**
1. Ensure `privileged: true` in docker-compose.yml
2. Add device mapping: `- /dev/video0:/dev/video0`
3. Check user permissions: `sudo usermod -aG video pi`

### 7.2 Display Issues

#### Problem: No output on TV

**Solutions:**
1. Check HDMI cable connection
2. Verify TV is on correct HDMI input
3. Check display output:
   ```bash
   tvservice -s
   xrandr
   ```
4. Force HDMI output:
   ```bash
   sudo nano /boot/config.txt
   # Add:
   hdmi_force_hotplug=1
   hdmi_group=1
   hdmi_mode=16  # 1080p 60Hz
   ```
5. Reboot after config changes

#### Problem: Signage player not displaying

```bash
# Check X11 access
echo $DISPLAY
xhost

# Grant Docker access
xhost +local:docker

# Verify container can access display
docker exec ppl-signage-player env | grep DISPLAY
```

### 7.3 Docker Issues

#### Problem: Container won't start

```bash
# Check logs
docker logs ppl-edge-camera
docker logs ppl-signage-player

# Check compose status
docker compose ps

# Recreate containers
docker compose down
docker compose up -d
```

#### Problem: Out of disk space

```bash
# Check disk usage
df -h
docker system df

# Clean up unused resources
docker system prune -a
docker volume prune
```

### 7.4 Network Issues

#### Problem: Cannot connect to backend services

```bash
# Test connectivity
ping YOUR_BACKEND_IP

# Test specific ports
nc -zv YOUR_BACKEND_IP 8005
nc -zv YOUR_BACKEND_IP 8010

# Check firewall
sudo iptables -L

# Check DNS
nslookup YOUR_BACKEND_HOSTNAME
```

**Solutions:**
1. Verify backend services are running
2. Check firewall rules on backend
3. Ensure correct URLs in `.env` file
4. Use IP addresses instead of hostnames if DNS issues

### 7.5 Performance Issues

#### Problem: High CPU/temperature

```bash
# Check temperature
vcgencmd measure_temp

# Check CPU usage
htop

# Check Docker stats
docker stats
```

**Solutions:**
1. Ensure case fan is working
2. Reduce camera FPS or resolution
3. Add heatsinks
4. Improve ventilation
5. Check for runaway processes

### 7.6 Common Error Messages

| Error | Solution |
|-------|----------|
| `Camera not found` | Check cable connection, enable camera in raspi-config |
| `Permission denied: /dev/video0` | Add user to video group, ensure privileged mode in Docker |
| `Cannot connect to X server` | Run `xhost +local:docker`, ensure DISPLAY variable set |
| `Connection refused` | Check backend service is running, verify URLs in .env |
| `No space left on device` | Run `docker system prune -a`, expand SD card partition |

---

## 8. Appendix

### 8.1 Configuration Reference

#### Edge Camera Configuration (camera-config.yaml)

```yaml
device:
  id: string                    # Unique device identifier
  name: string                  # Human-readable name
  location: string              # Physical location
  type: edge                    # Device type

camera:
  device_id: 0                  # Camera device index
  resolution:
    width: 1280                 # Video width (px)
    height: 720                 # Video height (px)
  fps: 15                       # Frames per second
  format: mjpeg                 # Encoding format
  buffer_size: 10               # Frame buffer size

platform:
  cameras_url: string           # Cameras service URL
  discovery_url: string         # Discovery service URL
  health_check_interval: 30     # Heartbeat interval (sec)
  max_reconnect_attempts: 10    # Max reconnection tries
  reconnect_interval: 5         # Retry delay (sec)

server:
  host: 0.0.0.0                 # Server bind address
  port: 9001                    # Server port

stream:
  encoding: mjpeg               # Stream encoding
  quality: 80                   # JPEG quality (1-100)
  chunk_size: 4096              # Stream chunk size

logging:
  level: INFO                   # Log level
  format: string                # Log format string
```

#### Signage Player Environment Variables

```bash
DEVICE_ID                     # Unique device identifier
DISCOVERY_SERVICE_URL         # Discovery service endpoint
MEDIA_SERVICE_URL             # Media service endpoint  
GATEWAY_URL                   # Gateway service endpoint
DISPLAY                       # X11 display (default: :0)
HTTP_SERVER_PORT              # HTTP server port (default: 8009)
```

### 8.2 Maintenance Tasks

#### Daily Tasks
- ✅ Check health endpoints (automated via cron)
- ✅ Monitor logs for errors
- ✅ Verify display output

#### Weekly Tasks
- ✅ Review disk space usage
- ✅ Check for system updates
- ✅ Verify backend connectivity
- ✅ Test remote control endpoints

#### Monthly Tasks
- ✅ Full system update: `sudo apt update && sudo apt upgrade`
- ✅ Docker image updates
- ✅ Clean up old logs
- ✅ Backup configuration files
- ✅ Test recovery procedures

### 8.3 Backup and Recovery

#### Backup Configuration

```bash
# Create backup directory
mkdir -p ~/backups/$(date +%Y%m%d)

# Backup configuration
cp -r ~/ppl-meta-deployment/config ~/backups/$(date +%Y%m%d)/
cp ~/ppl-meta-deployment/.env ~/backups/$(date +%Y%m%d)/
cp ~/ppl-meta-deployment/docker-compose.yml ~/backups/$(date +%Y%m%d)/

# Backup data volumes
docker run --rm -v ppl-meta-deployment_signage-data:/data \
    -v ~/backups/$(date +%Y%m%d):/backup \
    alpine tar czf /backup/signage-data.tar.gz -C /data .
```

#### Restore from Backup

```bash
# Restore configuration
cp ~/backups/20260202/config/* ~/ppl-meta-deployment/config/
cp ~/backups/20260202/.env ~/ppl-meta-deployment/
cp ~/backups/20260202/docker-compose.yml ~/ppl-meta-deployment/

# Restore data volume
docker run --rm -v ppl-meta-deployment_signage-data:/data \
    -v ~/backups/20260202:/backup \
    alpine tar xzf /backup/signage-data.tar.gz -C /data

# Restart services
cd ~/ppl-meta-deployment
docker compose down
docker compose up -d
```

### 8.4 Update Procedures

#### Update Docker Images

```bash
cd ~/ppl-meta-deployment

# Pull new images (if using registry)
docker compose pull

# Or load new images from files
docker load < new-edge-camera-arm64.tar.gz
docker load < new-signage-player-arm64.tar.gz

# Recreate containers with new images
docker compose down
docker compose up -d

# Verify
docker compose ps
docker compose logs -f
```

#### Rollback to Previous Version

```bash
# Stop current containers
docker compose down

# Load previous images
docker load < old-edge-camera-arm64.tar.gz
docker load < old-signage-player-arm64.tar.gz

# Start with old images
docker compose up -d
```

### 8.5 Security Recommendations

1. **Change default passwords**: Change the default `pi` user password
2. **Use SSH keys**: Disable password authentication for SSH
3. **Firewall**: Enable UFW firewall
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 9001
   sudo ufw allow 8009
   sudo ufw enable
   ```
4. **Regular updates**: Keep OS and Docker updated
5. **API authentication**: Use API keys in production
6. **Network isolation**: Use separate VLAN for edge devices

### 8.6 Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Edge Camera | 9001 | HTTP | Management API, Health checks |
| Signage Player | 8009 | HTTP | Control API, Health checks |
| Backend Cameras | 8005 | HTTP | Video streaming endpoint |
| Backend Discovery | 8010 | HTTP | Service registration |
| Backend Media | 8000 | HTTP | Playlist management |
| Backend Gateway | 8080 | HTTP | API gateway |
| Portainer (optional) | 9000 | HTTP | Docker management UI |
| SSH | 22 | SSH | Remote access |

### 8.7 Useful Commands Cheat Sheet

```bash
# System
sudo reboot                                    # Reboot system
sudo shutdown -h now                           # Shutdown system
vcgencmd measure_temp                          # Check temperature
htop                                           # System monitor

# Docker
docker ps                                      # List running containers
docker compose up -d                           # Start services
docker compose down                            # Stop services
docker compose logs -f                         # Follow all logs
docker logs -f ppl-edge-camera                 # Follow specific log
docker stats                                   # Resource usage
docker system prune -a                         # Clean up

# Camera
vcgencmd get_camera                            # Check camera status
libcamera-hello --list-cameras                 # List cameras
v4l2-ctl --list-devices                        # List video devices

# Display
tvservice -s                                   # HDMI status
xrandr                                         # Display info
xhost +local:docker                            # Allow Docker X11 access

# Network
ping YOUR_BACKEND_IP                           # Test connectivity
nc -zv HOST PORT                               # Test port
ifconfig                                       # Network interfaces

# Health Checks
curl http://localhost:9001/health              # Edge camera health
curl http://localhost:9001/status              # Edge camera status
curl http://localhost:8009/health              # Signage player health
curl http://localhost:8009/api/v1/status       # Signage status
```

### 8.8 Support and Resources

- **PPL Meta Platform Documentation**: [Internal docs URL]
- **Raspberry Pi Documentation**: https://www.raspberrypi.com/documentation/
- **Docker Documentation**: https://docs.docker.com/
- **Flutter Documentation**: https://docs.flutter.dev/
- **Arducam Support**: https://www.arducam.com/docs/

---

## Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-02 | Initial deployment guide created |

---

**End of Deployment Guide**

For issues or questions, please contact the PPL Meta platform team.
