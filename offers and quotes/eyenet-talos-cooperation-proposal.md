# Cooperation Proposal

## EyeNet × Talos Group — Middleware Integration Partnership

| | |
|---|---|
| **Document Type** | Cooperation Proposal (Draft) |
| **Parties** | EyeNet (on-premises edge computer-vision platform) & Talos Group (eHealth / IoMT / Telemedicine ecosystems) |
| **Status** | For discussion |
| **Version** | 0.1 |

---

## 1. Executive Summary

EyeNet and Talos Group propose a strategic technology cooperation focused on the **joint design, development, and commercialization of an integration middleware** that connects:

- **EyeNet** on the one side — operating in **headless mode**, exposing its computer-vision capabilities (presence detection, gate/area monitoring, demographics, camera events, signage triggers) as machine-consumable services; and
- **Talos Group** on the other side — exposing its eHealth ecosystem capabilities (telemedicine, EMR/HIS via eWAVE MD, IoMT device data, No.A.H. platforms, ePokratis Health Cloud) through **REST APIs**.

The middleware will act as the intelligent bridge between the two platforms: it will host **connectors embedding business logic across both companies' systems**, expose **fully tokenized (secured) endpoints**, and publish every capability as an **MCP (Model Context Protocol) server — one per service** — enabling AI agents and third-party systems to consume integrated vision + health workflows securely and uniformly.

---

## 2. Background

### 2.1 EyeNet

EyeNet is an on-premises, edge-computing computer-vision platform for human activity monitoring and intelligent automation. Key characteristics relevant to this partnership:

- Runs fully **on-premises / over VPN** with zero cloud dependency for video or data.
- Headless architecture: all functionality exposed programmatically, no coupling to end-user applications.
- Application suite: Presence, Gate, Signage, Sentinel, Vradar — orchestrated by the Matrix layer.
- Operating modes: Spot, Gate, Area, Goggles, Drone.
- Deployed across offices, industrial sites, POS environments, and maritime fleets — a natural overlap with Talos's maritime and isolated-site verticals.

### 2.2 Talos Group

Talos Group (London, UK) is a premier provider of certified eHealth technologies (FDA-approved, CE-certified, ISO 9001/13485/27001), serving governments, maritime fleets, hospitals, and armed forces:

- **No.A.H. EMS & Maritime** — AI-powered telemedicine for ambulances and vessels.
- **eWAVE MD System** — end-to-end EMR/HIS for clinics and hospitals.
- **Epione AI Robot** — human-friendly AI nurse assistant.
- **MediStation Kiosk** — telemedicine kiosks for camps, hotels, municipalities, and isolated areas.
- **ePokratis Health Cloud** — personal health records and remote monitoring.
- **IoMT & Analytics** — medical sensors, wearables, and predictive eHealth intelligence.

### 2.3 The Opportunity

Both companies operate in physically distributed, security-sensitive, connectivity-constrained environments — and both serve overlapping markets (maritime, defense, critical infrastructure). Today their systems operate in silos: EyeNet *sees* what happens on site; Talos systems *care* for people on site. A middleware that fuses real-time visual situational awareness with health operations creates entirely new product categories neither party can offer alone.

---

## 3. Proposed Solution: The Integration Middleware

### 3.1 Concept

A dedicated middleware layer positioned between the two platforms:

```
+--------------------------- MIDDLEWARE ---------------------------+
|                                                                   |
|  +----------------+   +----------------------+   +-------------+  |
|  | EyeNet         |   | Connector /          |   | Talos       |  |
|  | Headless       |<->| Orchestration Logic  |<->| REST APIs   |  |
|  | Adapters       |   | (business rules)     |   | Connectors  |  |
|  +----------------+   +----------------------+   +-------------+  |
|                                                                   |
|  +---------------------------+  +------------------------------+  |
|  | Tokenization & Security   |  | MCP Server per Service       |  |
|  | Layer (authN/authZ, OAuth2|  | (AI-agent-ready tool         |  |
|  | / JWT, scoped tokens)     |  |  exposure, one MCP/server)   |  |
|  +---------------------------+  +------------------------------+  |
+-------------------------------------------------------------------+
        ^                                                    ^
        |                                                    |
   EyeNet Platform                                    Talos Systems
   (headless, on-prem)                          (TMA / eWAVE / IoMT)
```

### 3.2 Core Components

1. **EyeNet Headless Connectors**
   - Consume EyeNet events and data streams: presence counts, gate crossings, area occupancy, camera events, demographic analytics, alert states.
   - Abstract EyeNet's internal APIs behind stable middleware contracts so EyeNet version upgrades remain transparent to Talos.

2. **Talos REST API Connectors**
   - Wrap Talos services (EMR/HIS records, IoMT vitals feeds, telemedicine session management, kiosk status, crew health records) behind uniform adapter interfaces.
   - Handle mapping between Talos data models (patients, encounters, devices) and middleware domain objects.

3. **Connector Logic & Orchestration Engine**
   - Configurable business rules spanning both systems, e.g.:
     - A man-overboard or gate anomaly detected by EyeNet triggers a No.A.H. maritime telemedicine consult workflow.
     - Occupancy/presence data from EyeNet enriches hospital ward staffing logic in eWAVE MD.
     - Epione robot dispatch based on real-time room-level presence from EyeNet Area mode.
     - MediStation kiosk sessions initiate automatically when specific individuals enter defined zones.
   - Event-driven core (publish/subscribe) plus synchronous request/response paths.

4. **Middleware Dashboard & Connectors Framework**
   - The middleware ships with its own **administration & operations dashboard** that visualizes and manages all **connectors between the systems and services of both sides**: EyeNet applications on one side, Talos services (EMR/HIS, IoMT feeds, telemedicine sessions, kiosks) on the other.
   - Each connector carries **its own embedded logic**, modeled on the **triggers & actions module of the EyeNet platform** — i.e., event-based trigger definitions, condition evaluation, and action dispatch — so interoperability rules are configured, executed, and monitored at the connector level.
   - This design keeps **system-to-system interoperability fully decoupled from the MCP servers**: the connectors guarantee that both platforms interoperate directly regardless of AI-agent usage, while the MCP layer is an additional, optional consumption channel. Adding, modifying, or removing an MCP server never affects live connector logic — and vice versa.

4. **Tokenization & Security Layer**
   - **Every endpoint tokenized**: no direct system-to-system calls; all traffic passes through authenticated, scoped tokens (OAuth 2.0 / JWT).
   - Per-client, per-service, per-scope token issuance with short TTLs and audit logging — aligned with Talos's ISO 27001 posture and healthcare-grade compliance requirements.
   - Full data-flow audit trail; support for fully offline/on-premises operation consistent with EyeNet's zero-cloud principle.

5. **MCP Server per Service**
   - Each middleware service is published as its own **MCP server**, exposing tools/resources in a standardized, agent-ready interface.
   - Examples: `mcp-presence`, `mcp-gate-events`, `mcp-patient-vitals`, `mcp-telemedicine-session`, `mcp-kiosk-dispatch`.
   - Benefits: AI assistants and agentic workflows (clinical copilots, operations dashboards, fleet command centers) can discover and invoke cross-platform capabilities without bespoke integrations; new services plug in without changing the contract model.

---

## 4. Illustrative Use Cases

| Use Case | EyeNet Role | Talos Role | Middleware Logic |
|---|---|---|---|
| **Maritime crew safety** | Detects falls, absence, or restricted-area breaches on board via Gate/Area modes | Triggers No.A.H. Yacht telemedicine consultation & alerts shore-based physicians | Event correlation, severity scoring, automated case creation |
| **Smart ward / clinic** | Real-time room occupancy & patient movement analytics | eWAVE MD HIS staffing & bed management | Presence feeds → operational dashboards & alerts |
| **Epione robot orchestration** | Detects patient distress indicators / presence at care points | Epione dispatch & engagement routines | Zone-based dispatch rules with tokenized robot control |
| **Isolated sites / military camps** | Perimeter & gate monitoring, personnel counting | MediStation kiosk activation, ePokratis record updates | Fully offline-capable event pipeline over VPN |
| **Agentic command center** | Vision telemetry as MCP tools | Health ops as MCP tools | Unified agent-accessible service catalog |

---

## 5. Joint ML Model Development & R&D

### 5.1 Vision

Beyond integration, the cooperation includes the **joint development of dedicated machine-learning models** trained on the combined data acquired by the sensors of both systems. The fusion of:

- **machine-vision output** (presence, movement, gate/area events, demographics, visual activity patterns from EyeNet), and
- **telemedicine & inpatient sensory output** (vitals from IoMT devices/wearables, patient monitoring streams, EMR/HIS events, REST API events from Talos services)

creates a unique, previously unavailable dataset. New insights and opportunities emerge precisely at this intersection — correlations between physical behavior and physiological state, early-warning signals, and operational patterns that neither system can detect alone.

### 5.2 Example Research Directions

- Prediction of patient deterioration combining vitals trends with mobility/activity patterns observed by vision.
- Fall-risk and post-operative recovery scoring fusing gait/movement analysis with biometric data.
- Crowd/density health analytics for wards, vessels, and isolated facilities.
- Anomaly detection across fused event streams (vision events × API events × device telemetry).
- Behavioral baselining for crew and patient safety in maritime environments.

### 5.3 R&D vs. Direct Development Split

It is explicitly recognized that parts of this work constitute **genuine R&D** while other parts can proceed as **direct development and application**, since some insights are expected to be evident from the outset:

- **Direct development track**: models addressing immediately evident insights (e.g., occupancy-driven alerting, presence-correlated kiosk activation, simple threshold/fusion rules) are developed and productized within the standard roadmap, delivering near-term value.
- **R&D track**: novel hypotheses requiring experimentation, dataset curation, model training, and clinical/domain validation are pursued as structured R&D activities, with jointly agreed success criteria, milestones, and potential co-funded research programs (e.g., national/EU funding instruments).
- Both tracks share the same data pipeline and governance framework established by the middleware, ensuring a smooth transition of validated R&D results into production connectors and MCP services.

### 5.4 Data Governance

All ML work will operate under strict data-governance rules consistent with GDPR, medical-device regulations, and both parties' certifications: anonymization/pseudonymization at the middleware boundary, on-premises processing aligned with EyeNet's zero-cloud principle, and explicit consent/role-based access for any patient-related data used in training or inference.

---

## 6. Cooperation Model

- **Joint development**: shared technical working group; EyeNet leads headless adapters and vision-domain connectors, Talos leads REST API connectors and healthcare compliance; joint ownership of the orchestration and MCP layers.
- **IP framework**: each party retains IP in its own platform; the middleware is jointly developed under a mutually agreed joint-IP or dual-license arrangement (to be detailed in the definitive agreement).
- **Go-to-market**: co-branded offering targeting maritime, healthcare, defense, and critical-infrastructure customers; joint pilots with existing clients of both parties.
- **Commercial structure**: revenue share or reseller/licensing model for the middleware and bundled solutions — subject to negotiation after the pilot phase.

---

## 7. Indicative Roadmap

| Phase | Duration | Deliverables |
|---|---|---|
| **1. Discovery & Architecture** | 4–6 weeks | API surface inventory (EyeNet headless, Talos REST); security/tokenization design; MCP schema definition |
| **2. MVP Pilot** | 8–10 weeks | Core connectors (1–2 EyeNet apps ↔ 1–2 Talos services); tokenization layer; first MCP servers; single joint pilot customer (maritime or clinic) |
| **3. Hardening & Compliance** | 6–8 weeks | Full audit logging, HA deployment, ISO 27001-aligned security review, performance validation |
| **4. ML Track Kick-off** | Parallel with 2–4 | Direct-development fusion models productized; R&D hypotheses defined, datasets curated, success criteria agreed |
| **5. Productization** | Ongoing | Connector marketplace, additional MCP services, validated ML models in production, co-branded GTM launch |

---

## 8. Mutual Benefits

**For EyeNet**
- Entry into regulated healthcare and eHealth markets through a certified partner (FDA/CE/ISO).
- New distribution channels via Talos's government, maritime, and defense client base.
- Standardized AI-agent exposure of the platform via MCP.

**For Talos Group**
- Adds real-time visual intelligence and physical situational awareness to its health ecosystems.
- Strengthens maritime and isolated-site offerings (No.A.H., MediStation) with safety/compliance automation.
- Differentiation through an agentic, MCP-based integration fabric ahead of market.

**Joint**
- Defensible combined product category: *vision-aware health operations*.
- Reusable middleware platform extensible beyond the two founding systems.

---

## 9. Next Steps

1. Sign NDA and nominate technical leads from both sides.
2. Joint discovery workshop: map EyeNet headless endpoints and Talos REST API surface; agree on scope of MVP.
3. Draft and execute a Memorandum of Understanding (MoU) covering IP, confidentiality, and pilot terms.
4. Kick off Phase 1 (Discovery & Architecture).

---

## 10. Contact

- **EyeNet**: [name, email, phone]
- **Talos Group**: 3rd Floor, 207 Regent St., London W1B 3HH, United Kingdom · www.talosgroup.eu

---

*This document is a non-binding proposal intended to initiate discussions. All commercial, legal, and IP terms are subject to a definitive agreement between the parties.*


