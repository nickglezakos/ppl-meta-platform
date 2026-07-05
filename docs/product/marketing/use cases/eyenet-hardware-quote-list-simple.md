# EyeNet Hardware Quote List — Simplified (by Device Type)

> **Purpose:** Hardware requirements list for the [Door Entrance Use Case](./door-entrance-use-case.md), grouped by device type. Extracted from the full [Hardware Options & Alternatives](./door-entrance-hardware.md) reference. Tiers, prices, and deployment configurations excluded — see the [full quote list](./eyenet-hardware-quote-list.md) for those.

---

## 1. Cameras

All camera options for capturing video of people approaching/entering the door.

| Device Type | Example Models | Notes |
|---|---|---|
| USB Webcam (UVC) | Logitech C920 / C922 / Brio, Microsoft LifeCam, any 1080p UVC webcam | 1080p recommended; plug-and-play; USB cable limited to ~5m |
| Raspberry Pi Camera Module | Raspberry Pi Camera Module 3 (12MP), Pi Camera Module 3 Wide (102° FOV) | Connects via ribbon cable to Raspberry Pi; compact, fanless |
| RTSP IP Camera | TP-Link Tapo C110 / C210 / C310, Hikvision DS-2CD2xxx series, Dahua Lite series, Amcrest, Reolink | PoE preferred; 1080p–4MP; outdoor-rated models available; RTSP URL config required |
| Enterprise IP Camera | Hikvision DeepinView series, Dahua WizMind series, Axis P-series, Bosch FLEXIDOME | 4MP–8MP; IR night vision; WDR; varifocal lens; vandal-resistant; PoE+; onboard analytics |

---

## 2. Computers / Compute Devices

All compute hardware — from Raspberry Pi edge units to enterprise servers — that runs EyeNet platform services.

| Device Type | Example Models | Notes |
|---|---|---|
| Raspberry Pi 4 / 5 | Raspberry Pi 4 (4GB), Raspberry Pi 5 (4/8GB) | Runs edge-camera and signage-simple-player at the door; fanless, low power; microSD or SSD storage |
| Raspberry Pi Compute Module 5 (CM5) | CM5 with 16–32GB RAM on a carrier board with M.2 slot | High-performance edge unit for door deployments; NVMe SSD; Gigabit Ethernet; fanless |
| Business PC / Laptop (repurposed) | Any Intel i5/i7 (8th gen+) or AMD Ryzen 5/7, 16GB RAM, 500GB SSD | Ubuntu Server 22.04/24.04 LTS recommended; supports 1–5 cameras |
| Small Form Factor / Mini PC | Intel NUC (i5/i7, N100/N150/N305), Beelink SER5/SER6 (Ryzen 5/7), Dell OptiPlex Micro, Lenovo ThinkCentre Tiny, HP EliteDesk Mini | 16–32GB RAM; 512GB–1TB NVMe SSD; fanless options available; supports 1–10 cameras |
| Tower Server / Workstation | Dell PowerEdge T150/T350, HPE ProLiant ML30/ML110, Dell Precision, Lenovo ThinkStation (custom-built) | 32–64GB RAM; 2×1TB NVMe SSD (RAID1); ECC RAM; dual Gigabit Ethernet; supports 10–30+ cameras |

---

## 3. Displays & Signage Players

Screens and compute devices for playing targeted messages and videos at the door via the EyeNet Simple Player app.

| Device Type | Example Models | Notes |
|---|---|---|
| Android Tablet (all-in-one) | Samsung Galaxy Tab A9+ (11"), Lenovo Tab M10 Plus (10.6"), Amazon Fire HD 10 | 10–12"; 1920×1200 min; WiFi-only; built-in speakers; needs permanent USB-C power for 24/7; touchscreen |
| HDMI Monitor (15–24") | Dell/HP/Lenovo 19–22" business monitors, ViewSonic, ASUS, any HDMI display | Used with separate compute device (Raspberry Pi, Mini PC, or Android TV Box); VESA mountable |
| Android TV Box / Stick | NVIDIA Shield TV, Xiaomi Mi Box S, Amazon Fire TV Stick 4K, Chromecast with Google TV | Very low cost compute; Android-based; good video decoding; not designed for 24/7 operation |
| Commercial Signage Display | Samsung SMART Signage (QMC/QBC series), LG Digital Signage (UH5F/UL3G series), Philips Professional Display (D-Line) | 21.5–32"; 24/7 rated; built-in Android SoC; built-in speakers; commercial warranty; bright panels for well-lit areas |
| 7–10" HDMI Touchscreen | Official Raspberry Pi Touch Display 2, Waveshare IPS panels, similar small touchscreens | Used with Raspberry Pi for door edge unit; doubles as signage display and QR station |

---

## 4. Network Equipment

| Device Type | Example Models | Notes |
|---|---|---|
| Managed Gigabit Switch | Ubiquiti UniFi Switch Lite 8/16, TP-Link JetStream, Netgear ProSAFE, Cisco CBS series | VLAN support for traffic isolation; QoS for camera streams |
| PoE Switch | Ubiquiti UniFi Switch PoE 8/16, Cisco CBS350 PoE, Aruba Instant On 1930 PoE | Power + data over single cable for cameras; eliminates power cable runs |
| WiFi Access Point | Any standard enterprise or consumer WiFi AP | For WiFi-connected cameras, tablets, and mobile devices; Ethernet strongly recommended for platform and cameras |

---

## 5. Mobile Devices

| Device Type | Example Models | Notes |
|---|---|---|
| Android Tablet | Samsung Galaxy Tab A9+ (11"), Lenovo Tab M10 Plus (10.6") | Displays station QR for mobile-based Presence check-in; can also run camera for face detection; wall mount or kiosk stand |

---

> **Note:** This document groups hardware by device type only. For tiered pricing, deployment configurations, cost estimates, and full alternatives, see the [EyeNet Hardware Quote List](./eyenet-hardware-quote-list.md) and the [Hardware Options & Alternatives](./door-entrance-hardware.md) reference.