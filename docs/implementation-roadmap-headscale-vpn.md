# Implementation Roadmap: Headscale VPN Integration

**Goal**: Integrate Headscale VPN server into ppl-meta-gateway service to provide zero-cost, self-hosted VPN for all platform devices.

**Timeline**: 2-3 weeks  
**Business Rationale**: Avoid customer objection to "platform + separate VPN subscription." Provide complete, self-contained solution.

---

## Compatibility / Will Anything Break?

Short answer: **it doesn’t have to**. If we implement Headscale as an *optional* capability (feature-flagged) and avoid changing existing ports/routing, the current Gateway + other services keep working while VPN work is in-progress.

### Keep Development Non-Breaking (Default Approach)

- **Feature flag everything**: default `VPN_PROVIDER=none` (or equivalent) so Gateway runs normally if Headscale isn’t configured.
- **Additive API only**: introduce new endpoints under `/api/v1/vpn/*` without changing existing auth flows or existing routes.
- **Do not require VPN for service-to-service traffic**: keep current local networking (direct ports and/or Nginx proxy) as-is; VPN is for *device enrollment/remote connectivity*.
- **Run Headscale in parallel**: it can be up as a container without being “used” until the provider is enabled.

### What *Can* Break Existing Services (Avoid Until Final Cutover)

- Changing Nginx / gateway routing so internal services are only reachable via VPN
- Changing ports/hostnames that existing clients use (e.g., moving `/api` to a new base URL)
- Applying production firewall rules (UFW/security groups) that block currently-used service ports
- Making Headscale a hard dependency at startup (Gateway fails to boot if Headscale is down)

### Recommended Rollout Strategy

1. Ship Headscale + provider code behind env flags (no behavioral change).
2. Enable VPN only in dev/test first.
3. Pilot on a small set of devices.
4. Only then consider “VPN-first” networking policies (if desired), with a documented rollback.

---

## Week 1: Core Integration (Days 1-5)

### Day 1: Headscale Server Setup

**Tasks**:
- [ ] Add Headscale container to `ppl-meta-gateway/docker-compose.yml`
- [ ] Create `config/headscale/config.yaml` with base configuration
- [ ] Configure network bridge between gateway and Headscale
- [ ] Set up persistent volumes for Headscale database

**Files to Create**:
```
ppl-meta-gateway/
├── docker-compose.yml (modify)
├── config/
│   └── headscale/
│       └── config.yaml (new)
└── .env (add HEADSCALE vars)
```

**Test**: 
```bash
cd ppl-meta-gateway
docker compose up -d headscale
docker compose logs -f headscale
# Should see: "Headscale started"
```

---

### Day 2: Gateway VPN Abstraction Layer

**Tasks**:
- [ ] Create `shared/networking/vpn_provider.py` (abstract base class)
- [ ] Implement `HeadscaleProvider` class in gateway service
- [ ] Add factory function `load_vpn_provider()` for runtime selection
- [ ] Update gateway `.env` with Headscale API URL and credentials

**Files to Create**:
```
shared/
└── networking/
    └── vpn_provider.py (new)

ppl-meta-gateway/
└── src/
    └── services/
        └── headscale_provider.py (new)
```

**Code**:
See [deployment-architecture.md](deployment-architecture.md#week-1-headscale-server-setup--gateway-integration) for full implementation.

**Test**:
```python
# Quick test script
from shared.networking.vpn_provider import load_vpn_provider

vpn = load_vpn_provider()
devices = await vpn.list_devices()
print(f"Connected devices: {len(devices)}")
```

---

### Day 3: Gateway API Endpoints

**Tasks**:
- [ ] Create `ppl-meta-gateway/src/routes/vpn.py` with REST endpoints
- [ ] Implement VPN service layer with business logic
- [ ] Add admin-only auth checks for enrollment/revocation
- [ ] Wire up endpoints to gateway main app

**Endpoints to Implement**:
```
POST   /api/v1/vpn/devices/enroll      # Generate auth key for new device
GET    /api/v1/vpn/devices             # List all enrolled devices
DELETE /api/v1/vpn/devices/{id}        # Revoke device access
GET    /api/v1/vpn/devices/{id}/status # Check device connection status
GET    /api/v1/vpn/health              # VPN service health check
```

**Files to Create**:
```
ppl-meta-gateway/
└── src/
    ├── routes/
    │   └── vpn.py (new)
    └── services/
        └── vpn_service.py (new)
```

**Test**:
```bash
# Login
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@example.com&password=admin123' \
  | jq -r '.access_token')

# Enroll device
curl -X POST 'http://localhost:8001/api/v1/vpn/devices/enroll' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"device_type": "camera", "device_name": "test-camera", "tags": ["tag:camera"]}'

# Should return: {"auth_key": "...", "device_id": "...", "instructions": {...}}
```

---

### Day 4-5: Client Enrollment Testing

**Tasks**:
- [ ] Create device enrollment script for RPi/Linux
- [ ] Test enrollment from Raspberry Pi (edge camera)
- [ ] Test enrollment from desktop (macOS/Linux/Windows)
- [ ] Test enrollment from mobile (iOS/Android)
- [ ] Verify NAT traversal across different networks

**Files to Create**:
```
scripts/
├── enroll-device.sh (new)
└── test-vpn-connection.sh (new)
```

**Test Scenarios**:
1. **RPi on same LAN as server**: Should get direct connection
2. **Mobile on cellular**: Should traverse NAT via DERP relay
3. **Desktop on corporate WiFi**: Should work through firewall
4. **Edge camera at remote location**: Should connect and stay connected

**Success Criteria**:
- [ ] Device gets VPN IP (`100.64.x.x`)
- [ ] Device can ping server's VPN IP
- [ ] Device can reach gateway API via VPN
- [ ] Device shows "online" in gateway VPN status endpoint

---

## Week 2: Client Tools & Documentation (Days 6-10)

### Day 6: Automated Enrollment Scripts

**Tasks**:
- [ ] Polish `scripts/enroll-device.sh` for production use
- [ ] Create Windows PowerShell version (`enroll-device.ps1`)
- [ ] Add error handling and user-friendly messages
- [ ] Test scripts on all supported platforms

**Features**:
- Auto-detect OS and install Tailscale client if missing
- Interactive prompts for device name and type
- Automatic auth key retrieval from gateway
- Connection verification after enrollment

---

### Day 7: RPi Camera Image Integration

**Tasks**:
- [ ] Add Headscale enrollment to RPi camera provisioning script
- [ ] Update `ppl-meta-edge-camera` Docker Compose to auto-enroll on first boot
- [ ] Test zero-touch provisioning workflow
- [ ] Document RPi camera setup process

**Zero-Touch Workflow**:
1. Flash RPi SD card with custom image
2. Boot RPi (connects to WiFi via config)
3. RPi auto-enrolls to VPN using embedded auth key
4. Camera service starts and connects to platform
5. Admin sees new camera in dashboard

---

### Day 8-9: Documentation

**Create These Docs**:
- [ ] **Deployment Guide**: How to deploy platform with VPN
- [ ] **Device Enrollment Guide**: How to add cameras, clients, edge devices
- [ ] **Network Requirements**: Ports, firewall rules, DNS
- [ ] **Troubleshooting Guide**: Common issues and fixes
- [ ] **Migration Guide**: How to move from Tailscale (if needed)

**Files to Create**:
```
docs/
├── guides/
│   ├── vpn-deployment.md (new)
│   ├── device-enrollment.md (new)
│   └── vpn-troubleshooting.md (new)
└── deployment-architecture.md (already exists, update)
```

---

### Day 10: TLS & DNS Setup

**Tasks**:
- [ ] Configure domain for Headscale server (`vpn.your-domain.com`)
- [ ] Set up Let's Encrypt TLS certificates
- [ ] Update Headscale config to use HTTPS
- [ ] Test client enrollment with TLS
- [ ] Document DNS requirements for customers

**DNS Records Needed**:
```
vpn.your-domain.com      A      203.45.67.89  (server public IP)
*.ppl-meta.local         A      100.64.1.5    (VPN internal DNS)
```

---

## Week 3: Production Hardening (Days 11-15)

### Day 11: Security Hardening

**Tasks**:
- [ ] Generate and secure Headscale API key
- [ ] Configure firewall rules (only VPN ports exposed)
- [ ] Set up API key rotation schedule
- [ ] Implement audit logging for device enrollment/revocation
- [ ] Security review of VPN endpoints

**Firewall Rules**:
```bash
# Allow Headscale gRPC (for client connections)
ufw allow 50443/tcp

# Allow Headscale API (internal only, via VPN)
ufw allow from 100.64.0.0/10 to any port 8080

# Block direct access from internet
ufw deny 8080/tcp
```

---

### Day 12: Monitoring & Health Checks

**Tasks**:
- [ ] Add Headscale health check endpoint to gateway
- [ ] Implement device connection monitoring
- [ ] Set up alerts for VPN service downtime
- [ ] Create dashboard showing online/offline devices
- [ ] Add metrics (device count, connection latency)

**Metrics to Track**:
- Number of enrolled devices
- Number of online devices
- Connection success rate
- Average latency
- NAT traversal success rate

---

### Day 13: Backup & Disaster Recovery

**Tasks**:
- [ ] Implement Headscale database backup (SQLite)
- [ ] Create restore procedure
- [ ] Test backup/restore workflow
- [ ] Document disaster recovery process
- [ ] Set up automated daily backups

**Backup Script**:
```bash
#!/bin/bash
# backup-headscale.sh
BACKUP_DIR=/backups/headscale
DATE=$(date +%Y%m%d_%H%M%S)

docker exec ppl-meta-headscale \
  sqlite3 /var/lib/headscale/db.sqlite ".backup /tmp/backup.db"

docker cp ppl-meta-headscale:/tmp/backup.db \
  $BACKUP_DIR/headscale_$DATE.db

# Keep last 30 days
find $BACKUP_DIR -name "headscale_*.db" -mtime +30 -delete
```

---

### Day 14: Pilot Deployment

**Tasks**:
- [ ] Deploy full stack to test environment (cloud VM or test server)
- [ ] Enroll 5-10 test devices (mix of cameras, mobile, desktop)
- [ ] Test across different network conditions
- [ ] Invite beta users to test enrollment process
- [ ] Collect feedback and issues

**Test Checklist**:
- [ ] Device enrollment from mobile app
- [ ] Camera streaming over VPN
- [ ] Desktop client access to platform
- [ ] Multi-site deployment (2+ locations)
- [ ] Device revocation and re-enrollment
- [ ] VPN service restart/recovery

---

### Day 15: Customer Onboarding Package

**Tasks**:
- [ ] Create customer deployment package (Docker Compose + scripts)
- [ ] Write customer-facing setup guide
- [ ] Create video walkthrough of deployment
- [ ] Prepare support materials (FAQs, troubleshooting)
- [ ] Plan rollout to first 3-5 customers

**Deliverables**:
```
customer-deployment-package/
├── docker-compose.yml
├── .env.template
├── config/
│   ├── headscale/
│   └── gateway/
├── scripts/
│   ├── deploy.sh
│   ├── enroll-device.sh
│   └── health-check.sh
├── docs/
│   ├── SETUP.md
│   ├── DEVICES.md
│   └── TROUBLESHOOTING.md
└── README.md
```

---

## Success Criteria

### Technical
- [ ] Headscale running as part of gateway Docker Compose stack
- [ ] Device enrollment working via gateway API
- [ ] Clients can connect from any network (NAT traversal works)
- [ ] VPN service survives restarts (data persisted)
- [ ] Health monitoring and alerts functional

### Business
- [ ] Zero external VPN costs for customers
- [ ] Clear value proposition: "Complete, self-contained platform"
- [ ] Competitive advantage vs. platforms requiring Tailscale subscription
- [ ] Deployment process documented and repeatable
- [ ] Support materials ready for customer questions

### Customer Experience
- [ ] Device enrollment takes < 5 minutes
- [ ] Clear error messages and troubleshooting steps
- [ ] Works across diverse network environments
- [ ] No "hidden" third-party subscriptions
- [ ] Professional, polished deployment experience

---

## Post-Launch (Month 2+)

### Future Enhancements (When Needed)
- [ ] Web UI for device management (beyond API)
- [ ] ACL policy builder (visual editor)
- [ ] Multi-tenant support (separate VPN namespaces per customer)
- [ ] Custom DERP relay servers (reduce latency in specific regions)
- [ ] SSO integration (enroll devices via company IdP)
- [ ] Extract VPN service to independent `ppl-meta-vpn` microservice

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Headscale breaks in production | Keep Tailscale provider implementation as fallback |
| NAT traversal fails in specific networks | Document firewall requirements, provide troubleshooting |
| Customer struggles with deployment | Offer managed deployment service (professional services) |
| Headscale lacks features vs. Tailscale | Contribute to Headscale project or implement features |
| VPN becomes bottleneck | Profile and optimize, consider DERP relay placement |

---

## Resources & References

- [Headscale GitHub](https://github.com/juanfont/headscale)
- [Headscale Documentation](https://headscale.net/)
- [Tailscale Client Installation](https://tailscale.com/download)
- [WireGuard Protocol](https://www.wireguard.com/)
- PPL Meta Platform: [deployment-architecture.md](deployment-architecture.md)

---

## Team Assignments (If Multi-Person)

**Backend Engineer**:
- Days 1-3: Headscale setup, Gateway integration, API endpoints

**DevOps Engineer**:
- Days 4-5: Testing, TLS setup, Docker configuration
- Days 11-13: Security hardening, monitoring, backups

**Documentation/Support**:
- Days 6-10: Client scripts, user documentation, onboarding materials

**QA/Testing**:
- Days 14-15: Pilot deployment, cross-platform testing, feedback collection

---

**Next Steps**: Start with Day 1 setup. Each day builds on the previous, so follow the sequence. Good luck! 🚀
