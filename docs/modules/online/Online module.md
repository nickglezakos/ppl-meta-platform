# Online Module — Proposal

> **Status**: Draft / High-Level Proposal  
> **Scope**: Cloud service (Hetzner VPS) + local installation counterpart  
> **Codename**: eyenet-online  

---

## 1. Purpose

The Online Module is the cloud counterpart to every local eyenet (ppl-meta) installation. It runs on a Hetzner Cloud VPS and provides four capabilities that local installations cannot handle on their own:

| # | Capability | Summary |
|---|---|---|
| 1 | **Installation Lifecycle** | Register, identify, and track every local installation by UUID |
| 2 | **Product & Subscriptions** | Treat each installation as a product instance with plans, modules, add-ons, and owner billing |
| 3 | **Hosted VPN (Headscale)** | Central Headscale server that all local installations connect to for remote access |
| 4 | **Owner Portal** | Headless backend + Cloudflare-hosted frontend for owners to manage their installation, subscriptions, and view reports |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hetzner Cloud VPS                             │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  eyenet-online   │  │    Headscale     │  │  PostgreSQL  │  │
│  │  (headless API)  │  │  VPN Server      │  │  (online DB) │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────────┘  │
│           │                     │                                │
│           │  ┌──────────────────┴──────────┐                    │
│           │  │  External Services           │                    │
│           │  │  • Adapty (subscriptions)    │                    │
│           │  │  • Stripe (payments)         │                    │
│           │  │  • Audienceful (CRM)         │                    │
│           │  └─────────────────────────────-┘                    │
└───────────┼─────────────────────┼───────────────────────────────┘
            │ HTTPS               │ WireGuard (VPN)
            │                     │
     ┌──────┴──────┐        ┌────┴─────────────────────┐
     │  Cloudflare │        │  Local Installation(s)   │
     │  Frontend   │        │  ┌─────────────────────┐ │
     │  (HTML/JS)  │        │  │ ppl-meta-node       │ │
     │             │        │  │ ppl-meta-gateway     │ │
     │  Owner      │        │  │ ppl-meta-cameras     │ │
     │  Dashboard  │        │  │ ...all services      │ │
     └─────────────┘        │  └─────────────────────┘ │
                            └──────────────────────────┘
```

---

## 3. Capability 1 — Installation Lifecycle

Every local ppl-meta installation is uniquely identified and tracked by the online service.

### 3.1 Core Concepts

- Each installation has a UUID (`INSTALLATION_ID`) and a human-readable name (`TENANT_NAME`), following the same pattern used in the Communications Service
- The online service is the **source of truth** for installation registration — a local installation must register with the online service to become "active"
- Installation status lifecycle: `pending` → `active` → `suspended` → `deactivated`

### 3.2 Registration Flow (High Level)

```
Local Install                         eyenet-online
     │                                      │
     │  POST /api/v1/installations/register  │
     │  { tenant_name, platform_version,     │
     │    hardware_fingerprint }              │
     ├─────────────────────────────────────→ │
     │                                      │
     │  { installation_id: UUID,            │
     │    status: "pending",                │
     │    api_key: "..." }                  │
     │ ←─────────────────────────────────────┤
     │                                      │
     │  (owner activates via portal)        │
     │                                      │
     │  Webhook or poll: status → "active"  │
     │ ←─────────────────────────────────────┤
```

### 3.3 Data Tracked Per Installation

| Field | Description |
|---|---|
| `installation_id` | UUID (primary identifier) |
| `tenant_name` | Human-readable name |
| `owner_user_id` | The user who owns this installation |
| `status` | `pending`, `active`, `suspended`, `deactivated` |
| `platform_version` | Installed version of ppl-meta |
| `hardware_fingerprint` | Optional machine/device identifier |
| `last_heartbeat` | Last time the installation phoned home |
| `vpn_node_id` | Headscale node ID (if enrolled) |
| `subscription_id` | Link to active subscription |
| `registered_at` | Registration timestamp |

### 3.4 Open Questions

- [ ] Heartbeat frequency and what data gets sent (version, service status, device count?)
- [ ] Grace period before `suspended` → `deactivated`
- [ ] Should the local installation degrade gracefully or hard-lock when deactivated?

---

## 4. Capability 2 — Products & Subscriptions

Each installation is treated as a product instance with a subscription plan, optional modules, and add-ons.

### 4.1 Service Stack

| Service | Role |
|---|---|
| **Adapty** | Product catalog, subscription packages, entitlement management, paywall logic |
| **Stripe** | Payment processing, invoicing, billing portal |
| **Audienceful** | CRM — owner user profiles, engagement tracking, email campaigns, lifecycle comms |

### 4.2 Product Structure (High Level)

```
Platform Subscription (Core)
├── Plan Tiers (e.g., Starter / Professional / Enterprise)
│   └── Defines: max cameras, max users, retention period, base features
│
├── Modules (purchasable capabilities)
│   ├── Instant Detection
│   ├── Analytics & Demographics
│   ├── Signage Integration
│   ├── Communications (email/webhook/push)
│   ├── VPN Remote Access
│   └── ...future modules
│
└── Add-Ons (usage-based or quantity-based)
    ├── Extra Cameras (per unit)
    ├── Extended Retention (per month)
    ├── Priority Support
    └── ...future add-ons
```

### 4.3 Owner–Installation Binding

- Every installation must have an **owner user** (email + password or SSO)
- The owner user exists in both:
  - **eyenet-online** — for subscription management, billing, portal access
  - **Local ppl-meta-node** — as the admin user of the local installation
- Owner data must **sync** between online and local, specifically:
  - Subscription status / active entitlements → local node
  - Installation health / usage data → online service

### 4.4 Entitlement Enforcement (High Level)

```
eyenet-online                          Local Installation
     │                                        │
     │  Adapty: subscription changed           │
     │  (new plan / module added / expired)    │
     ├─ compute entitlements ─────────────────→│
     │  { modules: [...], limits: {...} }      │
     │                                        │
     │                       ppl-meta-node     │
     │                       stores & enforces │
     │                       entitlements      │
```

### 4.5 Open Questions

- [ ] Push (webhook from online → local via VPN) vs. pull (local polls online) for entitlement sync?
- [ ] How are entitlements cached locally when the installation is offline?
- [ ] Adapty server-side vs. client-side SDK — which integration pattern?
- [ ] Stripe Customer ↔ Owner User mapping: 1:1 or 1:many (one user owning multiple installations)?
- [ ] Audienceful contact sync trigger: on registration, on subscription change, or both?

---

## 5. Capability 3 — Hosted Headscale VPN

The online service hosts a Headscale instance that serves as the coordination server for all local installations.

### 5.1 Role of Headscale on the VPS

| Function | Description |
|---|---|
| **Coordination server** | Manages WireGuard keys, node registration, NAT traversal |
| **Device registry** | Tracks all VPN-enrolled nodes across all installations |
| **ACL enforcement** | Isolates installations from each other on the VPN mesh |
| **DERP relay** | Provides relay for clients behind restrictive NATs |

### 5.2 Relationship to Local VPN

Per the [Headscale VPN Implementation Roadmap](../VPN/implementation-roadmap-headscale-vpn.md), each local installation enrolls its devices (cameras, gateways, edge nodes) into the VPN. The online-hosted Headscale is the central server these devices connect to.

### 5.3 Multi-Tenant Isolation

- Each installation gets its own **Headscale user/namespace**
- ACL policies ensure installations cannot see each other's devices
- The online service manages namespace creation as part of installation registration

### 5.4 Integration with Installation Lifecycle

| Event | VPN Action |
|---|---|
| Installation registered | Create Headscale namespace |
| Installation activated | Issue first auth keys |
| Installation suspended | Disable namespace (devices lose connectivity) |
| Installation deactivated | Delete namespace and all node keys |

### 5.5 Open Questions

- [ ] Single Headscale instance or per-region? (Start with single)
- [ ] DERP relay placement — Hetzner only or additional regions?
- [ ] Auth key lifetime and rotation policy
- [ ] Should VPN access be a module (paid) or included in all plans?

---

## 6. Capability 4 — Owner Portal

A minimal web portal for installation owners to manage their account, subscriptions, and view basic reports.

### 6.1 Architecture

| Component | Technology | Hosting |
|---|---|---|
| **Backend** | Headless API (Python/FastAPI or Node.js) | Hetzner VPS |
| **Frontend** | Static HTML/JS SPA | Cloudflare Pages |
| **Auth** | JWT-based, owner email + password | Backend issues tokens |
| **CDN / DDoS** | Cloudflare | Automatic |

### 6.2 Portal Sections (High Level)

```
Owner Portal
├── Dashboard
│   ├── Installation status (online/offline, last heartbeat)
│   ├── Subscription summary (plan, modules, renewal date)
│   └── Quick stats (cameras connected, VPN devices online)
│
├── Subscription Management
│   ├── Current plan details
│   ├── Upgrade / downgrade plan
│   ├── Add / remove modules and add-ons
│   └── Billing history & invoices (Stripe portal link)
│
├── Installation Details
│   ├── Installation ID, version, registered date
│   ├── VPN status and enrolled devices
│   └── Service health overview
│
├── Reports (Minimal)
│   ├── Uptime history
│   ├── Usage summary (cameras, detections, communications sent)
│   └── Subscription usage vs. limits
│
└── Account
    ├── Profile (email, name, password)
    ├── API keys for programmatic access
    └── Support / contact
```

### 6.3 Backend API Scope (Initial)

| Area | Endpoints |
|---|---|
| **Auth** | `POST /auth/login`, `POST /auth/register`, `POST /auth/refresh` |
| **Installations** | `GET /installations`, `GET /installations/{id}`, `POST /installations/register` |
| **Subscriptions** | `GET /subscriptions/{installation_id}`, `POST /subscriptions/change-plan` |
| **VPN** | `GET /vpn/devices/{installation_id}`, `POST /vpn/enroll` |
| **Reports** | `GET /reports/{installation_id}/summary`, `GET /reports/{installation_id}/uptime` |
| **Account** | `GET /account`, `PUT /account`, `POST /account/api-keys` |

### 6.4 Open Questions

- [ ] Frontend framework: vanilla JS, or lightweight (Alpine.js, Preact)?
- [ ] Backend language: Python (FastAPI) to match platform, or Node.js?
- [ ] Cloudflare Workers for any server-side logic, or pure static frontend?
- [ ] How much reporting data does the local installation push to online?

---

## 7. Data Flow Summary

```
                    ┌─────────────────────┐
                    │   Owner (Browser)   │
                    └──────────┬──────────┘
                               │ HTTPS
                    ┌──────────▼──────────┐
                    │  Cloudflare Pages   │
                    │  (Static Frontend)  │
                    └──────────┬──────────┘
                               │ API calls
                    ┌──────────▼──────────┐
                    │  eyenet-online API  │◄──── Adapty webhooks
                    │  (Hetzner VPS)      │◄──── Stripe webhooks
                    └──┬─────┬─────┬──────┘
                       │     │     │
              ┌────────┘     │     └────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Adapty   │  │ Stripe   │  │Audienceful│
        │(products)│  │(payments)│  │  (CRM)    │
        └──────────┘  └──────────┘  └──────────┘
                             │
                    ┌────────▼────────┐
                    │    Headscale    │
                    │   (VPN Server)  │
                    └────────┬────────┘
                             │ WireGuard tunnel
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │Install A │  │Install B │  │Install C │
        │(local)   │  │(local)   │  │(local)   │
        └──────────┘  └──────────┘  └──────────┘
```

---

## 8. Technology Stack Summary

| Component | Technology | Notes |
|---|---|---|
| Cloud VPS | Hetzner Cloud | Single VPS to start, vertical scaling |
| Online API | Python / FastAPI (TBD) | Headless backend |
| Database | PostgreSQL | Installations, users, subscriptions cache |
| VPN Server | Headscale | Self-hosted WireGuard coordination |
| Frontend | HTML / JS (static) | Hosted on Cloudflare Pages |
| CDN / Proxy | Cloudflare | DNS, TLS, DDoS protection |
| Subscriptions | Adapty | Product catalog, entitlements, paywalls |
| Payments | Stripe | Billing, invoices, customer portal |
| CRM | Audienceful | Owner lifecycle, email campaigns |

---

## 9. Implementation Phases (High Level)

### Phase 1 — Foundation

- Set up Hetzner VPS with Headscale + PostgreSQL
- Build installation registration API (UUID lifecycle)
- Owner user registration and authentication
- Basic Cloudflare frontend: login + installation status

### Phase 2 — Subscriptions

- Integrate Adapty for product catalog and entitlement management
- Connect Stripe for payment processing
- Build entitlement sync to local installations (via VPN or HTTPS)
- Owner portal: subscription management screens

### Phase 3 — VPN Integration

- Connect Headscale to installation lifecycle (auto-namespace creation)
- ACL policy generation per installation
- VPN device management in owner portal
- Auth key provisioning flow

### Phase 4 — CRM & Reports

- Audienceful integration for owner contact management
- Local → online telemetry pipeline (heartbeat + usage data)
- Owner portal: reports and usage dashboards
- Automated lifecycle emails (trial ending, renewal, etc.)

---

## 10. Open Decisions

| # | Decision | Options | Notes |
|---|---|---|---|
| 1 | Backend language | Python (FastAPI) / Node.js | FastAPI aligns with existing platform |
| 2 | Frontend framework | Vanilla JS / Alpine.js / Preact | Keep lightweight for Cloudflare Pages |
| 3 | Entitlement sync | Push (webhook via VPN) / Pull (local polls) | Push is real-time but needs VPN up |
| 4 | VPN as module or core | Included in all plans / Paid module | Affects pricing model |
| 5 | Single or multi-VPS | One VPS / Regional VPSes | Start single, scale later |
| 6 | Offline grace period | Hours / Days / Unlimited | What happens when local can't reach online? |
| 7 | Owner:Installation | 1:1 / 1:many | Can one owner manage multiple sites? |

---

*This is a living document. Each section will be expanded with detailed specs as we work through the decisions together.*
