# Lab machines inventory

**Status:** Active  
**Last updated:** 2026-09-19  
**Operator console:** developer Mac (Apple Silicon) — Stage 1 git, docs, RDP/SSH into labs; **not** the default Stage 2 image builder  
**Canonical release process:** [platform-release-cicd.md](./platform-release-cicd.md)  
**Operator guide (for dummies + glossary):** [eyenet-cicd-operator-guide.md](./eyenet-cicd-operator-guide.md)

This document names and describes the physical lab hosts used for EyeNet install testing and Stage 2 `linux/amd64` image builds. Keep hostnames stable; update IPs and Tailscale addresses when they change.

---

## Named hosts

| Lab ID | Site | OS | Hardware (summary) | Primary role |
|---|---|---|---|---|
| **`lab-home-win-nickg`** | Home | Windows (user `nickg`) | Windows laptop | Home Windows/WSL install path; optional Stage 2 builder when disk/RAM allow |
| **`lab-work-u24-mini-8g`** | Work LAN | Ubuntu 24.04 only | Mini PC, **8 GB RAM** | Stress / failure-mode lab: what happens **under** the 16 GB product threshold |
| **`lab-work-dual-64g`** | Work LAN | Dual-boot Windows + Ubuntu 24.04 | Laptop, **64 GB RAM** | Primary work lab: full-product Windows/WSL **or** native Ubuntu; preferred Stage 2 builder |

Use these **lab IDs** in chat, CHANGELOG notes, and agent instructions (e.g. *“Stage 2 on lab-work-dual-64g”*).

---

## Sites

### Home

Single Windows laptop on the home LAN. Reachable when the operator is on the same Wi‑Fi/LAN, or remotely via Tailscale/mesh + RDP.

### Work

Professionally built local network with two labs:

- Ubuntu-only mini PC (undersized RAM on purpose)
- Dual-boot Windows / Ubuntu 24 laptop (oversized RAM for comfortable full stack + Stage 2 builds)

Same office LAN; remote access via Tailscale/mesh then SSH (Linux) or Windows App / RDP (Windows).

---

## Host details

### `lab-home-win-nickg`

| Field | Value |
|---|---|
| Site | Home |
| OS | Windows (account **`nickg`**; hostname `DESKTOP-VDM2JKF`) |
| Tailscale name | `homenetwork` |
| LAN | `192.168.1.71` (SSH host alias `desktop-vdm2jkf`) |
| Tailscale IP | `100.73.31.71` (SSH host alias **`lab-home-win-nickg`**) |
| Access (LAN) | `ssh desktop-vdm2jkf` or Windows App → `192.168.1.71` |
| Access (remote) | Default Tailscale account → `ssh lab-home-win-nickg` (or Windows App → `100.73.31.71`) |
| Product path | Windows installer + WSL2 distro `eyenet` (Docker Engine CE preferred) |
| Stage 2 builder? | **Optional** — only if ≥16 GB RAM policy can be met for builds and free disk ≥12 GB; prefer `lab-work-dual-64g` when available |
| Notes | Two Windows user profiles may exist; OpenSSH already enabled; do not dual-boot this host unless disk headroom is re-planned |

### `lab-work-u24-mini-8g`

| Field | Value |
|---|---|
| Site | Work LAN |
| OS | **Ubuntu 24.04 only** (no Windows) |
| RAM | **8 GB** (intentional — below product ≥16 GB gate) |
| Access (LAN) | `ssh <user>@<lan-ip>` |
| Access (remote) | Tailscale → `ssh <user>@<mesh-ip>` |
| Product path | `deployment/ubuntu/install-eyenet-ubuntu.sh` |
| Stage 2 builder? | **No** — undersized for twelve-image build + Flutter; use for **install/runtime behavior under memory pressure** only |
| Purpose | Document OOM, installer RAM checks, degraded UX, and what we tell customers who are under 16 GB |
| Notes | Expect failures or heavy swapping; capture findings in Ubuntu lab follow-ups / CHANGELOG Notes |

### `lab-work-dual-64g`

| Field | Value |
|---|---|
| Site | Work LAN |
| OS | **Dual-boot:** Windows 10/11 amd64 **or** Ubuntu 24.04 (reboot to switch) |
| RAM | **64 GB** |
| Access (LAN) | Windows session: Windows App / RDP → LAN IP. Ubuntu session: SSH → LAN IP |
| Access (remote) | Tailscale → same (RDP or SSH depending on which OS is booted) |
| Product path (Windows) | WSL `eyenet` + Windows installer |
| Product path (Ubuntu) | Native Docker CE + Ubuntu installer |
| Stage 2 builder? | **Yes — preferred.** Boot Windows+WSL or Ubuntu; run Stage 2 scripts from [platform-release-cicd.md](./platform-release-cicd.md) |
| Notes | Only one OS active at a time. For Stage 2, prefer whichever boot has Docker + Flutter + ≥12 GB free disk ready |

---

## Roles vs release stages

| Lab ID | Stage 1 (git) | Stage 2 (GHCR build) | Install / soak test |
|---|---|---|---|
| Operator Mac | **Yes** (usual) | No (default) | No |
| `lab-home-win-nickg` | Rarely | Optional | Windows/WSL customer path |
| `lab-work-u24-mini-8g` | No | **No** | Ubuntu under-threshold |
| `lab-work-dual-64g` | Rarely | **Preferred** | Full Windows **or** full Ubuntu (after reboot) |

Agent wording examples:

- *“Stage 2 on lab-work-dual-64g (Ubuntu boot).”*  
- *“Stage 2 on lab-work-dual-64g (Windows/WSL).”*  
- *“Upgrade lab-home-win-nickg after Stage 2.”*  
- *“Reproduce under-RAM behavior on lab-work-u24-mini-8g.”*

---

## Access cheat sheet

### LAN (same site as the machine)

| Target | Tool |
|---|---|
| `lab-home-win-nickg` | Windows App → home LAN IP |
| `lab-work-u24-mini-8g` | `ssh user@work-lan-ip` |
| `lab-work-dual-64g` (Windows booted) | Windows App → work LAN IP |
| `lab-work-dual-64g` (Ubuntu booted) | `ssh user@work-lan-ip` |

### Access (remote)

1. Bring up **Tailscale** (default account — not EyeNet product VPN) on the Mac.  
2. Confirm the lab appears: `tailscale status` / `tailscale ping <lab>`.  
3. Connect with the **same tool as LAN**, but use the **mesh IP** (`100.x`), not `192.168.x.x`.

For **Stage 2 builds**, do not leave a single SSH open for hours: use **tmux** on the builder, or **one image per SSH** (`scripts/stage2_one.sh`) as in [platform-release-cicd.md](./platform-release-cicd.md).

VPN/mesh and Windows App are complementary: mesh gets you onto the network; RDP/SSH is the session.

Do **not** expose RDP or SSH to the public internet without the mesh/VPN.

---

## Fill in when known

Update this table as you stabilize addresses (do not put passwords here):

| Lab ID | Hostname | LAN IP | Tailscale / mesh IP | SSH user | Notes |
|---|---|---|---|---|---|
| `lab-home-win-nickg` | `DESKTOP-VDM2JKF` | `192.168.1.71` | `100.73.31.71` (`homenetwork`) | `nickg` | `ssh lab-home-win-nickg` / `ssh desktop-vdm2jkf` |
| `lab-work-u24-mini-8g` | | | | | 8 GB RAM |
| `lab-work-dual-64g` | | | | | Dual-boot; record which OS is usually left booted |

Historical / other boxes (not in the named set above) may still appear in older notes (e.g. `eyenet-server`, `kvalvis-pc`). Prefer the lab IDs in this document going forward; migrate aliases here when you rename hosts.

---

## Related

- Release CI/CD: [platform-release-cicd.md](./platform-release-cicd.md)  
- Windows via Tailscale walkthrough: [windows-via-tailscale-eyenet-images.md](./windows-via-tailscale-eyenet-images.md)  
- Ubuntu lab bug list: [`deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md`](../../deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md)  
- WSL full-product runtime: [windows-wsl-docker-engine-full-product.md](./windows-wsl-docker-engine-full-product.md)
