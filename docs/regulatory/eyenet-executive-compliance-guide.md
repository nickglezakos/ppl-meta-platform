# EyeNet Executive Compliance Guide

**Product:** EyeNet Vision / PPL Meta Platform  
**Audience:** owners, distributors, DPOs, CISOs, and sales  
**Date:** 17 September 2026  
**Status:** Informational executive map — not legal advice

**Web version:** [`eyenet-executive-compliance-guide.html`](eyenet-executive-compliance-guide.html)

**Companion sources**

- Jurisdiction and use-case law: [`docs/product/legal/Συνοπτική_Νομοθεσία_Προσωπικών_Δεδομένων_Ελλάδα_ΕΕ_ΗΠΑ.md`](../product/legal/Συνοπτική_Νομοθεσία_Προσωπικών_Δεδομένων_Ελλάδα_ΕΕ_ΗΠΑ.md)
- Official FR/GR source index: [`docs/regulatory/france-greece-gdpr-cybersecurity-guidelines.md`](france-greece-gdpr-cybersecurity-guidelines.md)

> Neither France nor Greece publishes a whitelist of “GDPR-compliant software.” Compliance is a **controller duty** (the customer) plus **processor duties** (EyeNet as vendor / installer). This guide shows how current platform controls map onto those duties.

---

## 1. Intro — what EyeNet is from a compliance point of view

EyeNet is an **on-premises computer-vision and operations platform**. A local installation processes camera, presence, and automation events at the customer site. Authority (licence and identity control plane) and Headscale (Matrix VPN mesh) sit on the internet only as coordination services. After first enrollment, leaf devices prefer **LAN**, then fall back to the **private mesh** (`100.64.x.x`). There is no requirement to send video to a public cloud.

That architecture is a strong privacy-by-design baseline. It is not a certificate. The legal risk still depends on **which module is switched on**, **what it infers**, and **where it is used**.

### 1.1 Roles

| Actor | Typical GDPR role | What they decide |
|---|---|---|
| Customer (owner of the site) | **Controller** | Purpose, legal basis, notices, DPIA, retention, who may see footage |
| EyeNet / distributor / installer | **Processor** (or joint controller if they set purposes) | How the software processes data, security of the product, support access |
| Authority service (`authority.eyenet-vision.com`) | Processor for licence / mesh identity metadata | Installation UUID, owner email, application key, VPN node tags — not video |
| Headscale VPN (`vpn.eyenet-vision.com`) | Processor for connectivity metadata | Mesh IPs, tags, enrollment keys — not video |
| Data subject | Employee, visitor, customer, passer-by | Rights of access, erasure, objection, restriction |

### 1.2 Privacy-by-design properties already in the product

| Property | Why it matters |
|---|---|
| Local / edge processing | Reduces cross-border transfers and cloud exposure |
| Identification **off by default** | Face match is an explicit trigger / presence mode, not a silent default |
| Modular enablement | Signage, presence, matching, plates, abandoned-object, and VPN can be left off |
| Fine-grained local RBAC | Node capabilities (`cameras:view`, `auth.roles.create`, …) limit who sees what |
| Machine application keys | Licence keys are `lic_<32 hex>`, bound 1:1 to owner email + installation UUID |
| Scoped mesh credentials | Platform uses `application_key`; devices use enrollment `auth_key` + HMAC `api_token` |
| LAN-first, mesh-on-demand | Remote access is a tunnel, not a standing video uplink |
| Audit trails | Presence decisions, trigger firings, Authority governance actions, user-action logs |

### 1.3 What still sits with the customer

- Legal basis and balancing test (especially workplaces and public-facing cameras)
- DPIA before high-risk go-live (Greece Decision 65/2018; CNIL / EDPB video guidelines)
- Physical signage and privacy notices
- Retention policy per data class
- Processor contracts (DPA) with EyeNet and any webhook/SaaS destinations
- Human review before adverse automated decisions
- NIS2 registration if the **customer** is an essential / important entity (Greece: Law 5160/2024; France: transposition still pending as of this date)

---

## 2. Jurisdiction snapshot

| Topic | Greece | France | Rest of EU | USA |
|---|---|---|---|---|
| Privacy law | GDPR + **Ν. 4624/2019** | GDPR + *Loi Informatique et Libertés* | GDPR | State laws (CPRA, BIPA, …) — no federal GDPR equivalent |
| Privacy authority | **ΑΠΔΠΧ (HDPA)** | **CNIL** | National DPA + EDPB | State AGs / private litigation |
| Video guidance | HDPA Directive **1/2011** + EDPB **3/2019** | CNIL *caméras augmentées* | EDPB 3/2019 | Notice / biometric consent varies by state |
| Face identification | Art. 9 biometric; DPIA almost always | Art. 9; CNIL treats facial recognition as prohibited by default | Art. 9 | BIPA-class statutes; high litigation risk |
| Cyber hygiene | NCSA Handbook (18 families) | ANSSI 42 measures + EBIOS RM | NIS2 + ENISA | Sectoral / contractual |
| Binding cyber list | **ΚΥΑ 1689/2025 — 22 requirements** (NIS2 in force) | NIS2 transposition **not finished** (Sep 2026); prepare to ANSSI pack | NIS2 | Not NIS2 |
| Official “approved software” list | None for GDPR | ANSSI qualified catalogue / SecNumCloud (**cyber**, not GDPR) | EUCC / common criteria | FedRAMP etc. (out of scope here) |

For EyeNet video analytics, both EU DPAs treat **anonymous / on-device detection** more favourably than **identification**. Facial recognition cannot be “ticked compliant” by citing on-prem deployment.

---

## 3. Executive risk map by module

Legend: **Low / Med / High** is legal-risk if the module is enabled in production. **Default** is the recommended privacy-by-default preset.

| Module | What it does | Personal data | Default | Risk if enabled | DPIA |
|---|---|---|---|---|---|
| Instant detection (overlay) | Live people/object boxes, optional age/gender | Image frames in memory; Redis TTL ~5 min; optional VMeta persist | Detection on; **identification off** | Med (High if persisted + identified) | Yes if systematic / workplace |
| Presence `qr_only` | Check-in via station/owner QR | User, device, installation, session metadata | Available | **Low–Med** (workplace attendance) | Usually yes in GR/EU workplaces |
| Presence `camera_only` | Face match to presence group | Short front-camera bursts + embeddings / group match | Off unless chosen | **High** (biometric) | **Required** |
| Presence `qr_plus_camera` | QR + face for verified grant | QR identity + biometric confirmation | Off unless chosen | **High** | **Required** |
| Triggers `demographic` | Live age/gender/count rules | Inferred demographics | Off | **High** (profiling) | Required for public / signage targeting |
| Triggers `ppl_match` / `vprofile_match` | Live match to known people | Face embeddings, group membership | Off | **High** (Art. 9) | **Required** |
| Triggers `search` | Lookback match on recorded video | Historical face search | Off | **High** | **Required** |
| Triggers `search_demographic` | Lookback aggregate demographics | Historical inferred attributes | Off | **High** | Required |
| Triggers `body_posture` | Fall / horizontal / upright | Body boxes, not identity | Off | Med | Yes in care / workplace safety |
| Triggers `motion` (alias `velocity`) | Speed / class / ROI transit | Track kinematics | Off | Med | If used to profile people |
| Triggers `left_object` | Abandoned bag / object | Object + optional nearby body | Off | **Low–Med** | Usually proportionate for security |
| Triggers `vehicle_plate` | Vehicle + optional OCR plate | Plate text = personal data in EU | Off; OCR optional | **High** if OCR on | Required when plates stored |
| Authority + bootstrap | Licence, owner, roles | Owner email, keys, installation ID | Required for install | Low (identity, not video) | No, unless logs mix with video |
| Matrix VPN mesh | Private remote path | Mesh IPs, tags, hostnames | LAN-first | Low if video stays on mesh | Network DPIA only if remote viewing of identifiable video |
| Mobile camera APK | Soft camera + mesh client | Live frames, device identity | Enrolled device | **High** in public/mixed space | **Required** (wearable / mobile) |
| Digital signage targeting | Content switch on audience | Aggregate demographics | Aggregate-only | **High** if individual targeting | Required |
| Webhooks / third-party actions | Push event payloads off-box | Whatever the action includes | Minimised payload | **High** | DPA + allowlist required |

---

## 4. Presence

Presence is the new attendance / verification product. It orchestrates QR, camera, policy, and automation without replacing Node, Cameras, or Triggers.

### 4.1 Modes

| Mode | Assurance | Biometric? | Recommended legal basis (EU) | EyeNet control |
|---|---|---|---|---|
| `qr_only` | Simple check-in | No | Employment contract / legitimate interest for site access, with notice | Station QR or owner identity QR; session timeout; max attempts |
| `camera_only` | Presence match | **Yes** | Art. 9 exception + necessity; alternative non-biometric method | Instant detection on reserved presence camera; group policy |
| `qr_plus_camera` | Verified presence | **Yes** | Same as camera_only; QR is the identity leg, camera is confirmation | QR-to-camera transition window; retry; grant/deny/fail |

Policy outputs: `granted`, `denied`, `retry_required`, `failed`. Downstream trigger types used today:

| Presence outcome | Default `trigger_type` | Default `action_type` |
|---|---|---|
| Granted `qr_only` | `presence_check_in` | `presence_log` |
| Granted `camera_only` | `presence_match` | `presence_grant` |
| Granted `qr_plus_camera` | `presence_verified_match` | `presence_grant` |

### 4.2 Data that stays in Presence vs data that does not

| Store | Contents | Exposed on Presence API? |
|---|---|---|
| Presence session / grant | User, device, mode, decision, reason, policy source, timestamps | Yes |
| Decision history / traces | Why granted, which policy, linked trigger/action UUIDs | Yes (role-gated) |
| Analytics | By user / device / installation / mode / grant type | Yes (prefer aggregate for extra-EU export) |
| Instant-detection path | Front-camera burst frames, bboxes, optional embeddings | **No** — processed by Cameras / Vision / VMeta |
| QR payload | `installation_uuid`, device, actor, token; optional licence **reference** fields | Challenge only; **must not** be treated as licence activation |

**Product rule:** Presence APIs return outcomes, not face images. That is necessary but not sufficient. If `camera_only` or `qr_plus_camera` is on, Art. 9 still applies because matching uses biometric data in the vision stack.

### 4.3 Presence vs previous use-case law note

Maps onto §3.3 *Room & Gate Protection* and §3.4 *Sentinel* of the Greek/EU/US legal summary:

| Legal note requirement | Presence support |
|---|---|
| Least-intrusive alternative before biometrics | `qr_only` is the alternative; keep it as default |
| Workplace proportionality | Session timeout, max attempts, group policy, time windows |
| Human oversight of adverse outcomes | `denied` / `failed` should notify a person, not lock a door alone |
| Traceability | Full session trace, policy source, audit log of actions |
| US BIPA-class risk | Do not enable camera modes in Illinois-like states without signed biometric policy |

---

## 5. Triggers — current types

Trigger modes in the media service (`trigger_mode`):

`demographic` · `ppl_match` · `search` · `search_demographic` · `vprofile_match` · `body_posture` · `motion` (alias `velocity`) · `left_object` · `vehicle_plate`

Plus Presence-provisioned types above.

### 5.1 Compliance table by trigger type

| Type | Family | Identifies a person? | Typical purpose | EU risk | Required settings | Customer must |
|---|---|---|---|---|---|---|
| `demographic` | Instant | No (inferred attributes) | Crowd / signage / occupancy | High if used to target or score people | Enable only needed age/gender fields; no individual history | Notice + DPIA; no sensitive-category targeting |
| `ppl_match` | Instant | **Yes** | Watchlist / known staff | High Art. 9 | Single group; similarity threshold; optional NOT mode | Legal basis, DPIA, short retention, human review |
| `vprofile_match` | Instant | **Yes**, multi-cam / multi-group | Cross-camera known-person | **Higher** (large-scale monitoring) | In-memory embeddings; 10 min refresh; `source_camera_id` | Same as match + justify multi-cam correlation |
| `search` | Lookback | **Yes**, on recordings | Retroactive find | High + purpose-limitation | Interval ≥ 30s; lookback `tracking_duration` | Separate purpose; auto-prune lookback window |
| `search_demographic` | Lookback | Indirect (aggregates from people records) | Historical occupancy mix | High | Multi-camera IDs; demographic conditions | Anonymisation thresholds; no re-identification |
| `body_posture` | Instant | No (body box + vote window) | Fall / safety | Med | `horizontal` / `upright`; 3–4 frame vote | Safety purpose; not performance scoring |
| `motion` | Instant | No unless combined with match | Loitering / rush / traffic / ROI approach | Med | ROI; cooldown; AND/OR conditions | Do not feed into individual scoring |
| `left_object` | Instant | No (COCO object; V2 uses nearby body) | Abandoned luggage | Low–Med | Allowlist; ROI; `T_stable`; V2 `require_person_left` | Security purpose; pin bbox not face crop by default |
| `vehicle_plate` | Instant | **Yes if OCR on** | Gate / parking | High with plates; Med vehicles-only | V1 vehicles; V2 `vehicle_plate_ocr_enabled` | Keep OCR **off** unless ANPR has a legal basis |
| Presence types | Policy | Depends on mode | Check-in / grant | See §4 | Linked actions; payload minimisation | Same as Presence mode |

### 5.2 Cross-cutting trigger controls (from the 2026 legal matrix)

| Control from legal summary §9.3 / §11 | Platform status | How to set it |
|---|---|---|
| Identification off by default | **Supported** | Do not create `ppl_match` / `vprofile_match` / `search` until approved |
| Trigger approval + purpose log | **Partial** | Use change management; execution logs exist; add legal-basis field in ops process |
| Explainable rules | **Supported** | Named conditions; `last_match_info`; Presence reason codes |
| Human-in-the-loop for high impact | **Customer + Partial** | Do not bind match triggers to door-unlock / disciplinary actions without a person |
| Notification minimisation | **Supported** | Event ID / reason templates; avoid attaching crops/faces |
| Webhook allowlist + DPA | **Partial / Customer** | Authenticated actions exist; customer must contract and restrict endpoints |
| Historical window / auto-prune | **Partial** | Search lookback is configurable; customer must keep it short |
| Multi-cam correlation only when needed | **Supported** | `vprofile_match` is opt-in; keep single-camera `ppl_match` as default |

---

## 6. Authority, fine-grained keys, and local bootstrap

### 6.1 What changed

Authority is the **licence and hierarchy control plane**. Local Node remains the **account and RBAC** system. Bootstrap no longer invents a second local licence secret.

| Credential | Shape / issuer | Bound to | Used for | Must not be used for |
|---|---|---|---|---|
| Software licence = `application_key` | `lic_` + 32 hex, issued by Authority | Owner email + **one** `installation_uuid` | Activate, report state, check update, platform VPN enroll | Sharing across sites; putting in QR as a live secret |
| Bootstrap-admin (temporary) | `admin@authority.local` when `AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=true` | Authority workspace only | First privileged Authority setup | Production; must be disabled after setup |
| Local user JWT | Node | User + roles + **capabilities** | Day-to-day API | Licence activation |
| VPN `auth_key` | Headscale pre-auth via Authority | Node tags (`tag:platform` / `tag:client` / `tag:install-<hex>`) | One-time mesh join | API calls |
| Device `api_token` | HMAC(secret, `installation_uuid`) | That installation | Discovery / resolve-platform | Owner login |
| Invitation token | Authority | Role + branch | User-first onboarding of distributor / reseller / owner | Device enroll |

**Fine-grained** here means: one machine licence key per installation, plus capability-level local permissions, plus separate mesh/device tokens. There is no shared god-key that both unlocks video and enrolls phones.

### 6.2 Local installation bootstrap (target production path)

1. Start local backend services; frontend bootstrap collects platform connection if missing.
2. Persist `application_key` + durable `installation_uuid` (settings / installer). Saving settings **is not** activation.
3. First owner registers with the **approved owner email**.
4. Node calls Authority `POST /api/v1/installations/activate` with `application_key + owner_email + installation_uuid`.
5. Only after `approved=true` does Node grant local `owner, admin, user`.
6. Authority remains source of truth for `licence_status`, `owner_enabled`, warning / offline grace; Node caches and can enter safeguard.
7. Disable Authority bootstrap-admin.

Mismatch of email, unknown key, or reuse of the same key on a second UUID is **rejected**.

### 6.3 Authority / bootstrap compliance table

| Control | FR (CNIL/ANSSI) | GR (HDPA/NCSA) | EyeNet | Residual |
|---|---|---|---|---|
| Unique machine identity | ANSSI hygiene: inventory & auth | KYA: asset inventory | `installation_uuid` + `lic_` key | Do not reuse keys |
| Least privilege | CNIL fiches 3–5; ANSSI admin guide | Access control requirement | Node capabilities; Authority roles (admin / distributor / reseller / owner / support) | Enforce capabilities on every API (still tightening) |
| Privileged bootstrap closed | ANSSI secure admin | Access control | Bootstrap-admin flag default off | Operational discipline |
| Key not shown after bind | Password / secret handling | Security of processing | Licence lifecycle: key server-side after bootstrap | Frontend must not re-display key |
| Audit of who onboarded whom | Accountability | Accountability | Authority audit history; Node `user_actions` | Keep retention on audit logs |
| Offline grace | Continuity | Continuity / backups | `offline_grace_days` + warning then safeguard | Document customer SLA |
| Support access | CNIL processors; ANSSI | Supply chain / remote access | Just-in-time, customer-approved, session-logged (policy) | Do not leave standing remote admin |

---

## 7. Matrix VPN mesh (platform + mobile camera APKs)

The Matrix is the commercial overlay on a **Headscale / WireGuard mesh**. Each app is its own VPN node. Platforms do **not** share a database. Authority stores the only shared link: **which client is assigned to which platform**.

### 7.1 How a device finds home

Enrollment (one internet round-trip) returns:

- `platform_tailscale_ip` — stable mesh IP  
- `platform_local_ip` — current LAN IP  
- `platform_hostname`, `matrix_group_id`, `auth_key`, `api_token`

Steady-state host order on players / mobile APKs:

1. `platform_local_ip` (LAN)  
2. manual `backendIP`  
3. `vpn_platform_tailscale_ip` (remote)

If LAN dies, the leaf can pull a fresh LAN IP from the platform over the mesh and refresh Authority so other devices benefit.

### 7.2 Tags (identity vs role vs type)

| Tag | Meaning |
|---|---|
| `tag:install-<hex(uuid)>` | Immutable installation identity |
| `tag:platform` / `tag:client` / `tag:analytics` | Role (mutually exclusive) |
| `tag:camera` / `tag:signage` / future `tag:presence` | Device type |
| `tag:matrix-<uuid>` | Mesh membership |

ACLs should keep clients **hub-and-spoke** to their assigned platform. Cross-tenant mesh paths are a defect.

### 7.3 Mesh / mobile APK compliance table

| Control | Why | EyeNet | Gap to close |
|---|---|---|---|
| Encrypt in transit | GDPR Art. 32, ANSSI, NCSA | WireGuard mesh + TLS on services | Confirm all APKs use mesh HTTP client, not cleartext internet |
| LAN-first (data minimisation of remote path) | CNIL / HDPA video: don’t stream off-site by default | Designed; player `platformHost` order | Deploy node local-IP reporter; rebuild APKs |
| Unique device identity | Inventory | `tag:install-…` + discovery `tailscale_ip` | Android must publish tun IP (not `NetworkInterface.list()`) |
| Remote access logged | Support / NIS2 | Policy: JIT + session log | Productise support sessions |
| No video to Authority / Headscale | Purpose limitation | Only IPs, tags, keys | Never put frames on enroll or resolve APIs |
| Mobile / wearable DPIA | Legal summary §3.6, §7.6 | Soft-camera APK is a mobile source | Geo/time recording rules; pause capture |
| Wrong-hub risk | Tenant isolation | `tag:platform` must be the **on-prem** node | Mis-enrollment to Hetzner node is a live ops defect — treat as P1 |

### 7.4 Mobile camera APK specifically

The mobile camera app reuses login, discovery, camera registration, and feed submit. Presence mobile is designed to wrap the same stack. Compliance consequences:

- A phone is a **camera in public or mixed space** when streaming.
- Mesh membership lets a phone reach the platform from outside the building — that is remote processing, not “local only.”
- Default: stream only while on shift / in geofence / with an explicit start-stop control (legal summary wearable SOP).
- Presence bursts should stay short; do not keep a standing front-camera session.

---

## 8. Official checklist mapping

Status: **Met** (platform can satisfy if configured) · **Partial** · **Customer** · **N/A**

### 8.1 CNIL — four first steps (France GDPR)

| CNIL step | EyeNet contribution | Owner | Status |
|---|---|---|---|
| 1. Register of processing | Camera inventory, Presence modes, trigger list, VPN nodes, Authority entitlements as processing descriptions | Customer RoPA; EyeNet supplies data-flow facts | **Partial / Customer** |
| 2. Minimise / sort data | Identification off; QR-only Presence; plate OCR off; aggregate signage; Redis TTLs; search lookback | Joint | **Met** if defaults kept |
| 3. Inform people and honour rights | Signage + notices are customer; platform: RBAC, traces, export/delete via ops | Customer + support runbooks | **Partial** (no full DSAR portal yet) |
| 4. Secure + 72h breach notice | On-prem, mesh, keys, logs; customer incident process | Joint | **Partial** — product security **Met**; breach playbook **Customer** |

CNIL 2024 security guide (selected fiches):

| Fiche | Theme | EyeNet mapping | Status |
|---|---|---|---|
| 1 | Security governance | Authority licence lifecycle + owner/admin split | Partial |
| 3–5 | Auth / access rights | Node capabilities; no shared admin | Met / tightening |
| 6–7 | Workstations / mobile | Hardening is customer; APK mesh | Customer + Partial |
| 8–9 | Network / servers | LAN-first + WireGuard; local services | Met |
| 10 | Websites | Local UI; TLS | Partial (deployment) |
| 11 | Secure development | Internal CI for Authority/Node | Partial |
| 14 | Processors | DPA; webhooks allowlist | Customer |
| 16–17 | Logging / backup | Trigger execution logs; local DB/backup | Partial |
| 18–19 | Continuity / incidents | Offline grace; customer IR | Partial |
| 21 | Crypto | TLS, WireGuard, file encryption policy | Partial |
| 22 | Cloud | Not required; Authority/VPN are coordination only | Met as non-cloud video |
| 23 | Mobile apps | Camera + Presence APKs | Partial (mobile DPIA) |
| 24 | AI | Instant detection, demographics, match | Customer DPIA |
| 25 | APIs | Scoped keys, capability checks | Partial |

### 8.2 HDPA — ten steps (Greece GDPR)

| # | HDPA step | EyeNet | Status |
|---|---|---|---|
| 1 | Awareness and risk strategy | This guide + legal summary | Customer |
| 2 | Record of processing | Same as CNIL step 1 | Partial / Customer |
| 3 | Lawfulness and rights | Feature flags per jurisdiction | Customer |
| 4 | Consent review | Prefer non-consent bases for security cameras; Presence camera modes may need Art. 9 exception, not “click-wrap” | Customer |
| 5 | Policies and rights procedures | Traces support investigation; erasure is ops | Partial |
| 6 | DPIA | Mandatory for match, Presence camera, search, plates, mobile camera, systematic video (Decision 65/2018) | **Customer — blocker** |
| 7 | DPO | Customer appointment when required | Customer |
| 8 | Breach detection / HDPA notify | Logs exist; notify is customer | Partial |
| 9 | Lead authority if multi-state | Authority hierarchy is commercial, not one-stop-shop | Customer |
| 10 | Transfers outside EU | Default: no video transfer. Mesh metadata to Authority/Headscale: keep in EU (Hetzner). No US subprocessors for video | **Met** if no US webhooks |

HDPA video: Directive 1/2011 + EDPB 3/2019 — no prior licence, but signage, purpose, minimisation, ROI, retention remain mandatory. `left_object` and count-only instant detection fit this better than `ppl_match`.

### 8.3 ANSSI hygiene (France cyber) — condensed

| ANSSI theme (from 42 measures) | EyeNet | Status |
|---|---|---|
| Know the SI / inventory | Cameras, Presence reservations, VPN node list | Partial |
| Authenticate users and admins | JWT + capabilities; machine `lic_` keys | Met |
| Separate privileges | Authority roles + local RBAC | Met |
| Update / patch | Authority check-update + installer channel | Partial |
| Network filtering / VPN | Mesh ACLs, LAN-first | Partial (ACL must not be allow-all) |
| Log and detect | Trigger / Presence / Authority audit | Partial |
| Backup | Local installation backups | Customer |
| Incident | Customer + vendor support | Customer |

### 8.4 Greece NIS2 / KYA 1689/2025 (if customer is in scope)

Law **5160/2024** is in force. Essential / important entities: register at [nis2register.cyber.gov.gr](https://nis2register.cyber.gov.gr/), apply the **22** national requirements, report incidents 24h / 72h / 1 month.

| KYA theme (as published) | How EyeNet helps a Greek NIS2 entity | Status |
|---|---|---|
| Policies | Customer ISMS; EyeNet supplies processing descriptions | Customer |
| Risk management | Local processing reduces cloud risk; EBIOS-style mapping possible | Customer |
| Asset inventory | Cameras, APKs, platforms, mesh nodes | Partial |
| Access control | RBAC + scoped keys + mesh tags | Met |
| Supply chain | Pin images; private registry; no random plugins | Partial |
| Incident response | Logs, traces, local retention of evidence | Partial |
| Backups | On-prem backup of Node/VMeta | Customer |
| Training | Not a product feature | Customer |

France NIS2: prepare the same controls; ANSSI registration comes when transposition lands.

---

## 9. Previous use-case matrix — still valid, with new rows

From the March 2026 legal summary §11, plus new 2026 modules.

| ID | Function | Restriction | Risk | Control | Available? | Owner |
|---|---|---|---|---|---|---|
| 1 | Real-time identification | Art. 9 / BIPA | High | Off by default; DPIA; short retention | Yes (`ppl_match`, Presence camera) | Legal + DPO + IT |
| 2 | Route / motion tracking | Behavioural profile | High / Med | Zone + time limits; auto-delete | Yes (`motion`, 3D routes) | DPO + IT |
| 3 | Demographics | Profiling | High | Aggregate only; no individual history | Yes | Legal + DPO |
| 4 | Webhooks | Third-country / processor | High | DPA, minimise, allowlist | Yes | Legal + IT |
| 5 | Cross-camera match | Large-scale monitoring | High | `vprofile_match` opt-in only | Yes | Legal + DPO + IT |
| 6 | Signage targeting | Discrimination | High | Broad segments; no sensitive classes | Yes | Legal + DPO + Ops |
| 11 | Attendance counting | Workplace monitoring | Med | Prefer QR Presence over face | Yes | DPO + Ops |
| **P1** | Presence QR-only | Workplace data | Med | Notice, retention, no secondary HR scoring | Yes | DPO + Ops |
| **P2** | Presence camera / verified | Biometric | High | Alternative method; DPIA; Art. 9 | Yes | Legal + DPO |
| **T1** | `left_object` | Security video | Low–Med | ROI; object-only; no face crop | Yes | Ops + DPO |
| **T2** | `vehicle_plate` OCR | Vehicle identification | High | OCR off by default | Yes | Legal + DPO |
| **T3** | Search on recordings | Purpose limitation | High | Short lookback; approval | Yes | DPO + IT |
| **A1** | Authority keys / bootstrap | Credential misuse | Med | `lic_` format; 1:1 bind; hide key after bind | Yes | IT |
| **V1** | Matrix VPN + APKs | Remote identifiable video | Med–High | LAN-first; ACL hub-and-spoke; mobile SOP | Partial deploy | IT + DPO |
| **V2** | Support over mesh | Unauthorised access | Med | JIT, customer approval, session log | Policy | IT + Ops |

Go-live gate from legal summary §8 still applies: jurisdiction check, DPIA where required, notices, retention/access/crypto/logs, named compliance owner, quarterly review.

---

## 10. Recommended production presets

| Environment | Enable | Keep off unless DPIA signed |
|---|---|---|
| Office / school attendance | Presence `qr_only`; count-only cameras; `left_object` if needed | Face Presence, `ppl_match`, search, demographics targeting |
| Gate / logistics | `left_object`; vehicle **without** OCR; event alerts | Plate OCR, vprofile multi-cam, webhooks to non-EU SaaS |
| Retail signage | Aggregate dwell / count | Individual targeting, age/gender at person level |
| Security operations | Instant detection overlay; posture/fall; human-ack actions | Auto-unlock, disciplinary use of match, standing mobile stream |
| NIS2 operator | Full audit logs, mesh ACLs, backup, IR runbook | Any unidentified processor / plugin |

---

## 11. Open product / ops items that affect the claim

These are engineering or deployment facts, not legal theory:

1. Rebuild mobile camera / player APKs with LAN-first `platformHost` and publish real mesh IPs.  
2. Deploy Node `report_platform_local_ip` so tokens stop returning `platform_local_ip: null`.  
3. Enroll the **on-prem** box as `tag:platform` — never the Hetzner Authority node.  
4. Turn off `AUTHORITY_BOOTSTRAP_ADMIN_ENABLED` after first setup.  
5. Do not put `application_key` in QR payloads as a live secret (reference-only if already local).  
6. Add an operational “legal basis / DPIA ID” field to trigger and Presence policy records (process today; product later).  
7. Publish a DSAR / erasure runbook for VMeta individuals, Presence sessions, and trigger logs.  
8. Keep webhook and communications actions on an allowlist with payload minimisation.

Until (1)–(3) are done, treat **remote APK access** as not production-ready from a security-evidence standpoint.

---

## 12. How to use this guide in a sale or audit

1. Start from **§1–3**: architecture, roles, which modules are actually on.  
2. Fill the customer RoPA from **§4–7** (Presence, triggers, keys, mesh).  
3. Tick **§8** against CNIL, HDPA, ANSSI, and KYA as applicable.  
4. Attach the March 2026 use-case checklists (legal summary §7) for the specific pitch.  
5. Do not claim “GDPR certified.” Claim: **on-prem, identification off by default, scoped keys, LAN-first mesh, customer-controlled DPIA.**

---

## 13. Document control

| Item | Value |
|---|---|
| Version | 1.0 |
| Date | 17 September 2026 |
| Replaces | n/a (first executive overlay on the March 2026 legal summary) |
| Next review | When Presence camera modes, trigger types, or mesh ACLs change, or when France publishes NIS2 transposition |
