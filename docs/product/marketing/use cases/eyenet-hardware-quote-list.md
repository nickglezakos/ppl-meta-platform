# EyeNet Hardware Quote List — Door Entrance Use Case

> **Purpose:** Sorted hardware requirements list for the [Door Entrance Use Case](./door-entrance-use-case.md). Extracted from the full [Hardware Options & Alternatives](./door-entrance-hardware.md) reference. All prices indicative in EUR.

---

## 1. Door Camera

Captures video of people approaching/entering the door; feeds Instant Detection and Presence.

| Tier | Device Type | Example Models | Est. Cost | Notes |
|---|---|---|---|---|
| Budget | USB Webcam (UVC) | Logitech C920 / C922 / Brio, Microsoft LifeCam, any 1080p UVC webcam | €40–120 | 1080p recommended; USB cable limited to ~5m |
| Compact | Raspberry Pi + USB Camera or Pi Camera Module 3 | Raspberry Pi 4 (4GB) or Pi 5 (4/8GB) + USB webcam / Camera Module 3 (12MP) | €80–150 | Fanless, fits above door frame; SD card reliability concern |
| Mid-Range | RTSP IP Camera | TP-Link Tapo C110 / C210 / C310, Hikvision DS-2CD2xxx series, Dahua Lite series, Amcrest, Reolink | €60–250 | PoE preferred; outdoor-rated models available |
| Portable | Android Phone as Soft Camera | Samsung Galaxy A series, Google Pixel, Xiaomi (any mid-range+ Android) | €0 (existing) | WiFi-only; needs USB power for permanent install; battery dependency |
| Premium | Enterprise IP Camera | Hikvision DeepinView series, Dahua WizMind series, Axis P-series, Bosch FLEXIDOME | €300–1,000+ | 4MP–8MP; IR night vision; WDR; vandal-resistant; PoE+ |

---

## 2. Door Screen + Signage Player

Small display near the door playing targeted messages/videos via the EyeNet Simple Player app.

| Tier | Display | Compute | Example Models | Est. Cost | Notes |
|---|---|---|---|---|---|
| Budget | Android Tablet (all-in-one) | Built-in | Samsung Galaxy Tab A9+ (11"), Lenovo Tab M10 Plus (10.6"), Amazon Fire HD 10 | €150–300 | 10–12"; 1920×1200 min; WiFi-only; needs permanent USB-C power |
| Compact | 15–24" HDMI Monitor + Raspberry Pi | Raspberry Pi 4 (4GB) or Pi 5 (4GB) | Dell/HP/Lenovo 19–22" business monitors, ViewSonic, ASUS | €180–350 | Modular; Pi runs Linux + Simple Player; VESA mountable |
| Mid-Range | 15–24" HDMI Monitor + Mini PC | Intel NUC (N100/N150), Beelink Mini S, Dell OptiPlex Micro, Lenovo ThinkCentre Tiny, HP EliteDesk Mini | Same monitor brands as above | €250–500 | x86; Windows or Linux; SSD storage; VESA bracket available |
| Android Box | 15–24" HDMI Monitor + Android TV Box | NVIDIA Shield TV, Xiaomi Mi Box S, Amazon Fire TV Stick 4K, Chromecast with Google TV | Same monitor brands as above | €150–300 | Very low cost compute; not designed for 24/7 operation |
| Premium | Commercial Signage Display (all-in-one) | Built-in Android SoC | Samsung SMART Signage (QMC/QBC series), LG Digital Signage (UH5F/UL3G series), Philips Professional Display (D-Line) | €400–1,200+ | 21.5–32"; 24/7 rated; built-in speakers; commercial warranty |

---

## 3. Platform Device

Runs the full EyeNet backend platform (all Docker-based services). Located in a secure IT room, not at the door.

| Tier | Device Type | Example Models | Est. Cost | Notes |
|---|---|---|---|---|
| Budget | Existing Business PC / Laptop (repurposed) | Any existing Intel i5/i7 (8th gen+) or AMD Ryzen 5/7, 16GB RAM, 500GB SSD | €0 (existing) | Supports 1–5 cameras; not recommended as a dedicated server |
| Mid-Range | Small Form Factor / Mini PC | Intel NUC (i5/i7), Beelink SER5/SER6 (Ryzen 5/7), Dell OptiPlex Micro, Lenovo ThinkCentre Tiny, HP EliteDesk Mini | €350–700 | 16–32GB RAM; 512GB–1TB NVMe SSD; fanless options available; supports 1–10 cameras |
| Mid-High | Tower Server / Workstation | Dell PowerEdge T150/T350, HPE ProLiant ML30/ML110, Dell Precision, Lenovo ThinkStation (custom-built) | €1,200–3,000 | 32–64GB RAM; 2×1TB NVMe SSD (RAID1); ECC RAM; supports 10–30+ cameras |
| Edge | Multiple Raspberry Pi 5 devices (distributed) | Raspberry Pi 5 (8GB) ×3+ | €200–400 total | Experimental/dev only; 1–3 cameras max; complex to manage |

---

## 4. Staff Mobile Device

Staff use their own or company-provided mobile devices with the EyeNet mobile app for QR-based Presence check-in.

| Tier | Device | Example Models | Est. Cost per Staff | Notes |
|---|---|---|---|---|
| BYOD | Staff personal phone | Any Android 10+ or iOS 15+ smartphone with functional camera | €0 | Lowest cost; varied device quality; personal data separation concerns |
| Company Phone | Entry to mid-range Android smartphone | Samsung Galaxy A15/A25, Google Pixel 7a/8a, Xiaomi Redmi Note, Nokia G-series | €120–350 | Uniform hardware; MDM enrollment possible; dedicated work device |
| QR Badge / NFC | Printed badge or NFC card/fob | Laminated printed QR badge, NFC card/fob (reader required at station) | €1–5 | No mobile app needed; no battery; badges can be lost/stolen; no mobile-side face verification |

---

## 5. Network Infrastructure

Local LAN switch/router + optional VPN for remote management. All devices must be on the same network.

| Tier | Equipment | Example Models | Est. Cost | Notes |
|---|---|---|---|---|
| Budget | Existing office LAN | Customer's existing Gigabit Ethernet switch + WiFi AP | €0 | Shared bandwidth with office traffic; no isolation |
| Mid-Range | Managed Gigabit Switch + VLAN | Ubiquiti UniFi Switch Lite 8/16, TP-Link JetStream, Netgear ProSAFE, Cisco CBS series | €100–300 | Traffic isolation; QoS for camera streams; requires networking knowledge |
| Premium | Dedicated PoE Switch + Segregated Network | Ubiquiti UniFi Switch PoE 8/16, Cisco CBS350 PoE, Aruba Instant On 1930 PoE | €200–600+ | PoE eliminates camera power cables; maximum reliability; professional install recommended |

### VPN for Remote Management

| Option | Description | Cost |
|---|---|---|
| EyeNet VPN Mesh (Tailscale/Headscale) | Built-in; devices auto-join secure mesh | Included in EyeNet Matrix license |
| Third-party VPN | Customer's existing OpenVPN, WireGuard, or corporate VPN | Varies |
| No VPN | Local on-site management only | €0 |

---

## 6. QR Station Device (Optional)

Dedicated device at the door displaying the station QR code for mobile-based check-in flows.

| Tier | Approach | Example Models | Est. Cost | Notes |
|---|---|---|---|---|
| All-in-One | Android Tablet at door | Samsung Galaxy Tab A9+ (11"), Lenovo Tab M10 Plus (10.6") | €150–300 | Displays QR + optional camera; wall mount or kiosk stand |
| DIY | Small monitor + Raspberry Pi | 7–10" HDMI touchscreen + Raspberry Pi 4/5 | €120–200 | Configurable; can run camera + display from same device |
| Zero-Electronics | Printed QR code | Laminated printed QR affixed to wall/door frame | €1–5 | Zero maintenance; static (cannot rotate challenge data) |
| None | Camera-only or mobile-only flow | No station hardware | €0 | Face-detection-only or mobile-initiated presence; fully automated |

---

## 7. Recommended Deployment Configurations

### Pilot / Single Door (Minimal Budget)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Camera | USB Webcam (Logitech C920) | €80 |
| Door Screen + Player | Android Tablet (Samsung Galaxy Tab A9+) | €180 |
| Platform Device | Existing office PC (repurposed) | €0 |
| Staff Mobile | BYOD (staff personal phones) | €0 |
| Network | Existing office LAN | €0 |
| QR Station | Printed QR code | €2 |
| **Total** | | **~€262** |

### Single Door (Professional)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Camera | RTSP IP Camera (TP-Link Tapo C310) | €60 |
| Door Screen + Player | 19" Monitor + Raspberry Pi 5 | €300 |
| Platform Device | Mini PC (Beelink SER5, Ryzen 5) | €400 |
| Staff Mobile | BYOD (staff personal phones) | €0 |
| Network | Existing LAN (dedicated port) | €0 |
| QR Station | Android Tablet (Samsung Galaxy Tab A9+) | €180 |
| **Total** | | **~€940** |

### Single Door — Edge Unit + Separate Platform (Recommended)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Edge Unit | RPi CM5 (16–32GB) + Camera Module 3 Wide + NVMe SSD + 7–10" Touch Screen | €260–440 |
| Platform Device | Industrial fanless mini PC, 32GB RAM, 1TB NVMe SSD | €410–700 |
| Staff Mobile | BYOD (staff personal phones) | €0 |
| Network | Existing office Gigabit LAN (both devices wired via Ethernet) | €0 |
| VPN | EyeNet VPN Mesh (included in EyeNet Matrix license) | €0 |
| **Total** | | **~€670–1,140** |

### Multi-Door / Enterprise (Single Site, 4 Doors)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Cameras (×4) | RTSP IP Cameras (Hikvision/Dahua PoE) | €800 (€200 ×4) |
| Door Screens + Players (×4) | 22" Monitors + Raspberry Pi 5 (×4) | €1,200 (€300 ×4) |
| Platform Device | Tower Server (Dell PowerEdge T150) | €1,800 |
| Staff Mobile | Company phones or BYOD | €0–1,400 |
| Network | PoE Switch + Dedicated VLAN (Ubiquiti) | €400 |
| QR Stations (×4) | Android Tablets (Samsung Galaxy Tab A9+) | €720 (€180 ×4) |
| VPN | EyeNet VPN Mesh (included in EyeNet Matrix license) | €0 |
| **Total** | | **~€4,920–6,320** |

---

> **Note:** All prices are indicative and in euros. Hardware procurement, installation, and cabling are handled separately through vetted EyeNet hardware partners. This list covers hardware requirements only — software licensing is quoted separately.