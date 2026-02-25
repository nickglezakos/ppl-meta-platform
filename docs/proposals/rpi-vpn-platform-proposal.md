# Proposal: RPi VPN Gateway App for PPL Meta Platform

## Executive Summary
Build a Raspberry Pi 5 app that runs a Tailscale-compatible VPN client and acts as the secure gateway for all PPL Meta Platform services. The app owns VPN routing, service exposure, and health routing so the platform is reachable only through the VPN. This proposal outlines scope, architecture, security controls, deployment, and delivery plan.

**Key Insight**: The Tailscale client is open-source and works with both Tailscale's managed coordination servers AND self-hosted Headscale servers. RPi setup is identical for both - only the backend server changes. This means:
- ✅ Deploy Tailscale client on RPi **now** (15 minutes)
- ✅ Switch to Headscale backend **later** (one command line flag change)
- ✅ Zero code changes on RPi when migrating

## Goals
- Provide a VPN-first access path for the full PPL Meta Platform.
- Ensure all platform traffic traverses the Tailscale network.
- Deliver a repeatable, secure, and remotely manageable RPi 5 deployment.
- Keep platform services isolated from the public LAN unless explicitly allowed.

## Non-Goals
- Replacing existing platform service code.
- Supporting non-WireGuard VPNs in the first release (OpenVPN, etc.).
- Full HA/failover across multiple RPi devices (can be phase 2).
- Building custom VPN clients (use proven Tailscale open-source client).

## Target Environment
- Hardware: Raspberry Pi 5 (8GB preferred)
- OS: Raspberry Pi OS (64-bit)
- Network: Ethernet or stable Wi-Fi with static LAN IP
- VPN: Tailscale client (open-source), works with:
  - **Phase 1 (Now)**: Tailscale coordination servers (managed, free tier)
  - **Phase 2 (Later)**: Headscale coordination server (self-hosted, zero cost)
  - **Migration**: Change `--login-server` flag only, no RPi code changes

## Scope (App Responsibilities)
- Install and manage Tailscale client (start/stop/health).
- Enforce VPN-only routing for platform services.
- Host platform services locally and expose them via VPN.
- Provide a single control plane (CLI or UI) for:
  - device registration
  - health checks
  - service start/stop
  - diagnostics and logs

## High-Level Architecture
1. **VPN Layer: Tailscale Routing Modes**
   
   Tailscale offers two primary modes for the RPi:
   
   ### Option A: Host-Only Mode (Simpler)
   - The RPi joins Tailscale as a normal device.
   - **What you get**: The RPi gets a Tailscale IP (e.g., `100.64.1.5`).
   - **Who can access it**: Anyone in your Tailscale network (subject to ACLs).
   - **What it exposes**: Only services running on the RPi itself.
   - **Use case**: The RPi hosts all platform services directly.
   
   ### Option B: Subnet Router Mode (More Flexible)
   - The RPi advertises itself as a gateway for other devices on your local LAN.
   - **What you get**: Devices on Tailscale can reach the RPi's entire LAN subnet (e.g., `192.168.1.0/24`).
   - **Who can access it**: Anyone in Tailscale can reach other devices behind the RPi (cameras, edge devices).
   - **What it exposes**: The RPi + any other devices on its physical network.
   - **Use case**: The RPi is a VPN gateway into an entire deployment site with multiple local devices.
   
   **Example scenario (Subnet Router)**:
   - Your RPi is at `192.168.1.77` and has Tailscale IP `100.64.1.5`.
   - Local IP cameras are at `192.168.1.80`, `192.168.1.81`.
   - With subnet routing enabled, remote users on Tailscale can connect to `192.168.1.80` through the RPi.
   - Without it, only services *on the RPi* are accessible.
   
   **Recommendation**: Start with **Host-Only Mode**. Enable subnet routing only if you need to reach other local devices (cameras, sensors) over VPN.

2. **Gateway Layer (Dynamic Routing)**
   - Traefik reverse proxy (chosen for dynamic config).
   - Configuration via:
     - Docker labels (services self-register routes).
     - File provider (runtime port updates without restarts).
   - Bound to Tailscale interface only (`--bind=100.64.x.x`).
   - Firewall rules block all inbound LAN traffic to platform ports.
   - Port changes propagate via Docker Compose env vars + labels.

3. **Platform Services (Docker Stack)**
   - All services run in Docker Compose with versioned images.
   - Service discovery via Docker DNS on internal bridge network.
   - Ports exposed to host only when needed (Traefik handles ingress).
   - Health checks defined in Compose for orchestration.

4. **Management App (Fleet Control)**
   - Python management CLI bundled as Docker service.
   - Capabilities:
     - Service start/stop/restart with dynamic port binding.
     - Health checks and diagnostics over VPN.
     - Configuration updates (env vars, ports) via API.
     - Log aggregation and export.
   - Health dashboard exposed via Traefik on VPN only.

## Security and Compliance Controls
- Tailscale ACLs restrict access to the device and specific ports.
- Host firewall (ufw or nftables) denies public LAN access.
- Services bind to loopback or internal Docker network.
- Encrypted secrets stored via OS keyring or env file with strict perms.
- Audit logs for VPN connections and management actions.

## Deployment Plan (Docker Fleet Strategy)
1. **Base Image Preparation**
   - Raspberry Pi OS 64-bit Lite, hardened defaults.
   - Pre-installed: Docker, Docker Compose, Tailscale.
   - SSH keys only, firewall locked down.
   - Fleet provisioning script for device enrollment.

2. **VPN Client Enrollment (Phase-Agnostic)**
   
   **Phase 1 (Immediate - Tailscale Backend)**:
   ```bash
   # Install Tailscale client on RPi
   curl -fsSL https://tailscale.com/install.sh | sh
   
   # Enroll to Tailscale network
   sudo tailscale up --authkey=<key-from-gateway-api>
   
   # Enable subnet routing for WiFi cameras
   sudo tailscale up --advertise-routes=192.168.1.0/24
   ```
   
   **Phase 2 (Later - Headscale Backend)**:
   ```bash
   # Same Tailscale client, just point to your Headscale server
   sudo tailscale up \
     --login-server=https://vpn.your-domain.com:50443 \
     --authkey=<key-from-gateway-api> \
     --advertise-routes=192.168.1.0/24
   ```
   
   **Key Point**: Only the `--login-server` flag changes. No reinstall, no code changes on RPi.

3. **Docker Stack Deployment**
   - Single `docker-compose.yml` with all platform services + Traefik.
   - Environment-specific config via `.env` files.
   - Images pulled from private registry (or built locally).
   - Services include:
     - Gateway (ppl-meta-gateway)
     - Node (ppl-meta-node)
     - Media (ppl-meta-media)
     - Vision (ppl-meta-vision)
     - Cameras (ppl-meta-cameras)
     - Communications (ppl-meta-communications)
     - Orchestrator (ppl-meta-orchestrator)
     - VMeta (ppl-meta-vmeta)
     - Traefik (reverse proxy)
     - Management API (fleet control service)

4. **Dynamic Port Configuration**
   - Ports defined in `.env` file per deployment.
   - Traefik labels auto-update routing rules on container restart.
   - Script to update `.env`, rebuild affected services, zero downtime.

5. **Fleet Management Tooling**
   - Centralized control plane (Portainer, custom dashboard, or SSH-based).
   - Remote updates via:
     - Docker image updates (pull + restart).
     - Compose file updates via Git pull + reload.
   - Remote health checks and log scraping over VPN.

6. **Rollout Process**
   - Flash RPi with base image.
   - Boot, auto-enroll to Tailscale.
   - Run provisioning script: pulls repo, sets env, starts stack.
   - Device registers with central management (optional).
   - Validation: health check all services, verify VPN-only access.

## Operational Workflows
### Initial Provisioning (Zero-Touch)
1. Flash custom image to SD card with provisioning script.
2. Boot RPi, connects to network (Wi-Fi or Ethernet).
3. Auto-enroll to Tailscale via ephemeral key.
4. Pull Docker images, start platform stack.
5. Device reports to central inventory (optional).

### Port Reconfiguration (Dynamic)
1. Update `.env` file with new port values.
2. Run `docker compose up -d` (only affected services restart).
3. Traefik auto-detects new ports via labels.
4. Health checks confirm services reachable on new ports.
5. No downtime for unaffected services.

### Service Updates (Rolling)
1. Push new image to registry or Git repo.
2. Trigger update command (via management API or SSH).
3. Pull new image, restart service with health check.
4. Rollback on failure (keep previous image tagged).

### Fleet-Wide Operations
- **Health monitoring**: Poll all devices via Tailscale, aggregate status.
- **Log collection**: Stream logs to central SIEM over VPN.
- **Config push**: Update `.env` or Compose files via Git + webhook.
- **Emergency kill**: Remote command to stop all services or revoke Tailscale access.

## Risks and Mitigations
- **Resource constraints on RPi**: 
  - Mitigation: Profile services, use Alpine-based images, tune memory limits, enable zram.
- **VPN dependency**: 
  - Mitigation: Secure fallback LAN access via hardware button or timeout flag.
- **Security misconfig**: 
  - Mitigation: Default deny firewall, automated config checks, ACL validation on boot.
- **Fleet update failures**: 
  - Mitigation: Health checks before/after updates, rollback scripts, staged rollouts.
- **Port conflicts during reconfig**: 
  - Mitigation: Validation script checks for conflicts before applying, atomic updates.
- **Docker image bloat**: 
  - Mitigation: Multi-stage builds, prune unused images, registry quota monitoring.

## Deliverables
- **RPi Base Image**: Hardened Raspberry Pi OS with Docker + Tailscale pre-installed.
- **Docker Compose Stack**: Complete platform services with Traefik ingress.
- **Dynamic Configuration System**: `.env`-based ports + Traefik auto-routing.
- **Fleet Management API**: Python service for remote control and diagnostics.
- **Tailscale ACL Templates**: Device tags and access policies for secure fleet.
- **Provisioning Scripts**: Zero-touch enrollment and stack deployment.
- **Deployment Playbooks**: Ansible or shell scripts for fleet rollout.
- **Documentation**:
  - Network architecture guide (host-only vs. subnet router).
  - Port reconfiguration procedures.
  - Fleet management workflows.
  - Troubleshooting and rollback guides.

## Timeline (Estimate)
- **Week 1**: Architecture finalization, VPN modes testing, firewall prototype, Traefik config.
- **Week 2**: Dockerize all platform services, dynamic port system, internal networking.
- **Week 3**: Fleet management API, health checks, log aggregation, update workflows.
- **Week 4**: Base image builds, provisioning automation, fleet rollout testing.
- **Week 5**: Documentation, security hardening, acceptance testing, pilot deployment.

## Phased Deployment Strategy

### Phase 1: Lab Setup (Now - 1 Hour)
**What to do on your RPi at the lab**:

1. **Install Tailscale Client**:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. **Enroll RPi to Tailscale Network**:
   - Option A: Use Tailscale's free tier initially
   - Option B: Get auth key from gateway API (once implemented)
   ```bash
   sudo tailscale up  # Follow OAuth flow in browser
   # Or with auth key:
   sudo tailscale up --authkey=<key>
   ```

3. **Enable Subnet Routing for WiFi Cameras**:
   ```bash
   # Enable IP forwarding
   echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   
   # Advertise your LAN subnet (adjust to match your network)
   sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-routes
   
   # In Tailscale admin panel, approve the route
   ```

4. **Verify WiFi Camera Access**:
   ```bash
   # From another Tailscale device, test camera access
   ping 192.168.1.80  # Your WiFi camera IP
   curl http://192.168.1.80/snapshot.jpg  # Test camera stream
   ```

**Time Investment**: 15-30 minutes  
**Cost**: $0 (Tailscale free tier: 100 devices, 3 users)  
**Result**: RPi + WiFi cameras accessible over VPN from anywhere

---

### Real-World Usage: Mobile Camera → Laptop → Digital Signage

Once Tailscale is running on all devices, here's the complete data flow:

```
┌─────────────────────────────────────────────────────────────┐
│                   TAILSCALE VPN MESH                         │
│                                                              │
│  Mobile Camera App (Anywhere)          Lab Laptop (Server)  │
│  ┌──────────────────┐                 ┌─────────────────┐  │
│  │ iPhone/Android   │  Video Stream   │ Compute Server  │  │
│  │ VPN: 100.64.1.30 │────────────────>│ VPN: 100.64.1.5 │  │
│  │                  │  ws://100.64.1.5│ • Gateway       │  │
│  └──────────────────┘       :8005     │ • Vision AI     │  │
│         ▲                              │ • Media Storage │  │
│         │                              └─────────────────┘  │
│         │                                      │            │
│    [Starbucks WiFi]                            │ Video      │
│    [Cellular Data]                             ▼            │
│    [Any Network]                                            │
│                                   ┌─────────────────────┐   │
│  WiFi Camera (Lab LAN Only)       │ Digital Signage RPi │   │
│  ┌──────────────────┐             │ VPN: 100.64.1.10    │   │
│  │ LAN: 192.168.1.80│◄────────────│ Requests video from:│   │
│  │ (via RPi bridge) │   Subnet    │ http://100.64.1.5   │   │
│  └──────────────────┘   Router    └─────────────────────┘   │
│                                             ▲                │
│                                             │                │
│                                       [Remote Store]         │
│                                       [Different City]       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Configuration in Your Apps**:

```dart
// Mobile Camera App (ppl_meta_mobile_camera)
// lib/config/api_config.dart
class ApiConfig {
  // Use Tailscale VPN IP of your lab laptop
  static const String BASE_URL = "http://100.64.1.5:8001";  // Gateway
  static const String CAMERA_WS = "ws://100.64.1.5:8005";   // Camera WebSocket
}

// Digital Signage App (ppl-meta-signage-simple-player)
// lib/config/api_config.dart
class ApiConfig {
  static const String BASE_URL = "http://100.64.1.5:8001";  // Gateway
  static const String MEDIA_URL = "http://100.64.1.5:8003"; // Media service
}
```

**Test Connectivity**:

```bash
# From mobile device (with Tailscale app running):
# Open browser, visit: http://100.64.1.5:8001/health
# Should see: {"status": "ok", "service": "gateway"}

# From RPi signage device:
curl http://100.64.1.5:8001/health
# Should see: {"status": "ok", "service": "gateway"}

# Test camera can reach laptop:
# In mobile camera app, start streaming
# Check laptop logs:
docker compose logs -f cameras
# Should see: "New camera connected: 100.64.1.30"
```

**What This Enables**:
- ✅ Mobile camera streams from coffee shop → laptop processes video → AI detects faces
- ✅ Digital signage at store displays video processed by laptop at your home/lab
- ✅ WiFi cameras on lab LAN accessible from mobile app via RPi bridge
- ✅ All communication encrypted, no ports exposed to internet
- ✅ Works anywhere with internet (cellular, WiFi, ethernet)

---

### Phase 2: Production Migration (Later - 0 Hours RPi Work)
**When you deploy Headscale (2-3 weeks gateway work)**:

1. **On Gateway Server** (one-time setup):
   - Deploy Headscale in Docker Compose
   - Get auth key from gateway API

2. **On RPi** (one command change):
   ```bash
   # Re-run tailscale up with new login server
   sudo tailscale up \
     --login-server=https://vpn.your-domain.com:50443 \
     --authkey=<key-from-your-gateway> \
     --advertise-routes=192.168.1.0/24
   ```

**Time Investment**: 2 minutes per RPi (can be automated)  
**Code Changes on RPi**: Zero  
**Result**: Same functionality, zero external costs

---

## Open Questions
1. ~~**Subnet Router**: Do you need VPN access to other local devices (cameras, sensors) or only the RPi services?~~
   - ✅ **ANSWERED**: Yes, use subnet router mode for WiFi cameras.

2. **LAN Access Exceptions**: Should any services remain accessible on the local network for debugging?
   - **Recommendation**: Emergency SSH on LAN with key-only auth, all else VPN-only.

3. **Fleet Management**: Centralized dashboard (Portainer, Ansible Tower) or CLI-based SSH control?
   - **Recommendation**: Docker + Portainer for UI-based fleet ops, SSH as backup.

4. **Image Registry**: Self-hosted (Harbor) or cloud (Docker Hub, GitHub Container Registry)?
   - **Recommendation**: GitHub Container Registry for versioning + CI/CD integration.

5. **Port Range Policy**: Should all devices use identical ports or site-specific assignments?
   - **Recommendation**: Identical ports per service type, Traefik handles internal routing.

6. ~~**VPN Backend**: Start with Tailscale or Headscale?~~
   - ✅ **ANSWERED**: Start with Tailscale now (fast), migrate to Headscale when gateway is ready (seamless).
