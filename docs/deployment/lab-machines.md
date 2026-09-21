# Lab machines inventory

**Status:** Active  
**Last updated:** 2026-09-21  
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

## Fleet status (vs GHCR)

**GHCR truth:** [`deployment/windows-installer/release-manifest.yml`](../../deployment/windows-installer/release-manifest.yml) for pin **`2.25.83`** (Mode D; last finalized **2026-09-21**).  
**Rule:** After every **Stage 3** on a named lab, update this table (pin, match state, date, short notes). Do not treat a matching *tag* as current — compare running `RepoDigests` (or amd64 child digests) to the manifest.

| Lab ID | Pin | Match GHCR? | Last Stage 3 | Notes |
|---|---|---|---|---|
| `lab-home-win-nickg` | `2.25.83` | **Yes** (gateway / discovery / cameras / frontend) | 2026-09-21 | Running index digests match finalized manifest. `ADVERTISE_HOST=192.168.1.71`. |
| `lab-work-u24-mini-8g` | `2.25.83` | **Yes** (gateway / discovery / cameras / frontend) | 2026-09-21 | Stage 3 re-pull after finalize; index digests match manifest. Repo `86e5d8a`. `ADVERTISE_HOST=192.168.9.14`. Discovery 11/11 healthy. |
| `lab-work-dual-64g` | — | — | — | Offline / unreachable from work `192.168.9.x` as of 2026-09-21. |

**How to refresh a row after Stage 3** (from the lab, or via SSH):

```bash
# pin + advertise
grep -E '^(RELEASE_TAG|ADVERTISE_HOST)=' .env   # or .env.windows

# compare key services to release-manifest.yml digests
for c in gateway discovery cameras frontend; do
  id=$(docker ps -q --filter name=ppl-meta-${c}- | head -1)
  [ -n "$id" ] || { echo "$c MISSING"; continue; }
  img=$(docker inspect "$id" --format '{{.Config.Image}}')
  dig=$(docker image inspect "$img" --format '{{index .RepoDigests 0}}')
  echo "$c  $dig"
done
```

---

## Sites

### Home

Single Windows laptop on the home LAN (`192.168.1.0/24`). Reachable when the operator is on the same Wi‑Fi/LAN, or remotely via **personal Tailscale** (default account — not the EyeNet product VPN) + OpenSSH / Windows App.

### Work

Professionally built local network with two labs on related office subnets:

- Ubuntu-only mini PC (undersized RAM on purpose) — currently on **`192.168.9.0/24`**
- Dual-boot Windows / Ubuntu 24 laptop (oversized RAM) — Windows session historically on **`192.168.11.0/24`**

Same office building; Mac on work Wi‑Fi is typically `192.168.9.x`. Remote access: enroll the lab in personal Tailscale (or stay on work LAN), then SSH (Linux) or Windows App / RDP (Windows).

---

## Host details

### `lab-home-win-nickg`

| Field | Value |
|---|---|
| Site | Home |
| OS | Windows (account **`nickg`**; hostname `DESKTOP-VDM2JKF`) |
| Tailscale name | `homenetwork` (personal Tailscale / default account) |
| LAN | `192.168.1.71` (SSH host alias `desktop-vdm2jkf`) |
| Tailscale IP | `100.73.31.71` (SSH host alias **`lab-home-win-nickg`**) |
| Access (LAN) | `ssh desktop-vdm2jkf` or Windows App → `192.168.1.71` |
| Access (remote) | Personal Tailscale up on Mac **and** on nickg → `ssh lab-home-win-nickg` (or Windows App → `100.73.31.71`). Do **not** use `192.168.1.71` off-LAN. |
| Product path | Windows installer + WSL2 distro **`eyenet`** (Docker Engine CE preferred) |
| Install dir | `C:\ppl-meta-platform` (WSL: `/mnt/c/ppl-meta-platform`) |
| Source / Stage 2 checkout | `C:\Users\nickg\ppl-meta-code-clean` (WSL: `/mnt/c/Users/nickg/ppl-meta-code-clean`) |
| Stage 2 builder? | **Optional** — only if ≥16 GB RAM policy can be met for builds and free disk ≥12 GB; prefer `lab-work-dual-64g` when available. Proven for selective Stage 2 (e.g. frontend `2.25.83`) over Tailscale. |
| Notes | Two Windows user profiles may exist; OpenSSH already enabled; do not dual-boot this host unless disk headroom is re-planned |

#### Connectivity (verified 2026-09-19 … 2026-09-21)

Three different address families — do not mix them:

| Path | Address | Who / what |
|---|---|---|
| Home Wi‑Fi / LAN | **`192.168.1.71`** | Phones, cameras, browsers on the same physical network. Set `ADVERTISE_HOST=192.168.1.71` in `.env.windows`. UI `http://192.168.1.71:3000`, gateway `:8080`, discovery `:8006`. |
| Operator personal Tailscale | **`100.73.31.71`** (`homenetwork`) | Operator Mac off-LAN: SSH / RDP / HTTP to the stack when Windows Tailscale is online. |
| EyeNet product VPN (Headscale) | **`100.64.0.x`** (was `100.64.0.24` when last enrolled) | Enrolled phones/cameras via `vpn.eyenet-vision.com`. Separate from personal Tailscale; re-check with `tailscale ip -4` inside WSL after enroll. |

**WSL / LAN publish (required for phones on Wi‑Fi):**

- Stack binds inside WSL; Windows `127.0.0.1` is forwarded into the distro, but the **physical NIC** is not unless portproxy is installed.
- Installer / admin: elevated `publish-lan-ports.ps1` (logon task `EyeNetLanPublish`) so `192.168.1.71:<ports>` → `127.0.0.1:<ports>`.
- Discovery must advertise the Windows LAN IP, **not** Docker `172.18.x` / WSL eth0.
- Scheduled discovery re-register: `EyeNetDiscoveryReregister`.

**Stage 2 over Tailscale (practical notes):**

- Prefer **one service per SSH** (`scripts/stage2_one.sh`) or **tmux** — long idle Tailscale SSH sessions drop.
- Flutter web build: use **Windows** `C:\Users\nickg\flutter\bin\flutter.bat` (the SDK on `C:` is Windows-only; WSL cannot run it). Docker image build/push runs in WSL `eyenet`.
- Free disk on `C:` is often tight (~20 GB); prune builder cache before multi-image Stage 2.
- Mac only drives SSH; the lab needs its own internet for base pulls and **GHCR push**.

---

### `lab-work-u24-mini-8g`

| Field | Value |
|---|---|
| Site | Work LAN (`192.168.9.0/24`) |
| OS | **Ubuntu 24.04 only** (no Windows) |
| Hostname | `eyenet-server` |
| RAM | **8 GB** (intentional — below product ≥16 GB gate; host reports ~7.7 Gi) |
| LAN | `192.168.9.14` (SSH host alias **`eyenet-server`**) |
| SSH user | `eyenet` |
| Access (LAN) | From work Wi‑Fi / LAN: `ssh eyenet-server` (or `ssh eyenet@192.168.9.14`) |
| Access (remote) | Personal Tailscale **not enrolled** on this box as of 2026-09-21 (`tailscale` present but logged out). Until enrolled, reach it only from the work LAN. |
| Product path | `deployment/ubuntu/install-eyenet-ubuntu.sh` |
| Install / clone | `~/ppl-meta-platform` (also referenced historically as `~/eyenet-platform`) |
| Stage 2 builder? | **No** — undersized for twelve-image build + Flutter; use for **install/runtime behavior under memory pressure** only |
| Purpose | Document OOM, installer RAM checks, degraded UX, and what we tell customers who are under 16 GB |
| Notes | Full stack often running for soak; pin may lag GHCR (check `~/ppl-meta-platform/VERSION`). Expect failures or heavy swapping; capture findings in [UBUNTU-LAB-FOLLOWUPS.md](../../deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md) / CHANGELOG Notes |

**Quick check (operator on work LAN):**

```bash
ssh eyenet-server 'hostname; free -h | head -2; cat ~/ppl-meta-platform/VERSION; docker ps --format "{{.Names}}" | head'
# UI when stack is up: http://192.168.9.14:3000
```

---

### `lab-work-dual-64g`

| Field | Value |
|---|---|
| Site | Work LAN |
| OS | **Dual-boot:** Windows 10/11 amd64 **or** Ubuntu 24.04 (reboot to switch) |
| RAM | **64 GB** |
| Windows LAN (historical) | `192.168.11.29` (SSH host alias `windows-lab`, user `user`) — confirm after each boot |
| Ubuntu LAN | Fill in when Ubuntu is booted (`hostname -I`); may be on `192.168.9.0/24` or `192.168.11.0/24` depending on Wi‑Fi |
| Access (LAN) | Windows session: Windows App / RDP → LAN IP (or `ssh windows-lab` if OpenSSH is up). Ubuntu session: `ssh <user>@<lan-ip>` |
| Access (remote) | Tailscale → same (RDP or SSH depending on which OS is booted) — enroll when bringing this host online remotely |
| Product path (Windows) | WSL `eyenet` + Windows installer |
| Product path (Ubuntu) | Native Docker CE + Ubuntu installer |
| Stage 2 builder? | **Yes — preferred.** Boot Windows+WSL or Ubuntu; run Stage 2 scripts from [platform-release-cicd.md](./platform-release-cicd.md) |
| Notes | Only one OS active at a time. For Stage 2, prefer whichever boot has Docker + Flutter + ≥12 GB free disk ready. As of 2026-09-21, `192.168.11.29` was unreachable from work `192.168.9.x` Wi‑Fi — power on / join the right subnet / confirm Ubuntu IP before assuming it is available. |

---

## Roles vs release stages

| Lab ID | Stage 1 (git) | Stage 2 (GHCR build) | Install / soak test |
|---|---|---|---|
| Operator Mac | **Yes** (usual) | No (default) | No |
| `lab-home-win-nickg` | Rarely | Optional (Tailscale OK) | Windows/WSL customer path |
| `lab-work-u24-mini-8g` | No | **No** | Ubuntu under-threshold |
| `lab-work-dual-64g` | Rarely | **Preferred** | Full Windows **or** full Ubuntu (after reboot) |

Agent wording examples:

- *“Stage 2 on lab-work-dual-64g (Ubuntu boot).”*  
- *“Stage 2 on lab-work-dual-64g (Windows/WSL).”*  
- *“Upgrade lab-home-win-nickg after Stage 2.”*  
- *“Reproduce under-RAM behavior on lab-work-u24-mini-8g.”*
- *“SSH eyenet-server / lab-work-u24-mini-8g from work LAN.”*

---

## Access cheat sheet

### LAN (same site as the machine)

| Target | Tool |
|---|---|
| `lab-home-win-nickg` | `ssh desktop-vdm2jkf` or Windows App → `192.168.1.71` |
| `lab-work-u24-mini-8g` | `ssh eyenet-server` → `192.168.9.14` (user `eyenet`) |
| `lab-work-dual-64g` (Windows booted) | Windows App → work LAN IP / `ssh windows-lab` if `192.168.11.29` is up |
| `lab-work-dual-64g` (Ubuntu booted) | `ssh user@work-lan-ip` (record IP when known) |

### Access (remote)

1. Bring up **personal Tailscale** (default account — not EyeNet product VPN) on the Mac.  
2. Confirm the lab appears: `tailscale status` / `tailscale ping <lab>`.  
3. Connect with the **same tool as LAN**, but use the **mesh IP** (`100.x`), not `192.168.x.x`.

Known remote SSH aliases today:

| Lab ID | SSH alias | Mesh IP |
|---|---|---|
| `lab-home-win-nickg` | `lab-home-win-nickg` | `100.73.31.71` |
| `lab-work-u24-mini-8g` | *(none yet — enroll Tailscale, then add Host)* | — |
| `lab-work-dual-64g` | *(none yet)* | — |

For **Stage 2 builds**, do not leave a single SSH open for hours: use **tmux** on the builder, or **one image per SSH** (`scripts/stage2_one.sh`) as in [platform-release-cicd.md](./platform-release-cicd.md).

VPN/mesh and Windows App are complementary: mesh gets you onto the network; RDP/SSH is the session.

Do **not** expose RDP or SSH to the public internet without the mesh/VPN.

**Personal Tailscale vs EyeNet product VPN:** personal Tailscale is for *operator* reachability to lab PCs. EyeNet Headscale (`vpn.eyenet-vision.com`, `100.64.0.0/10` on the product mesh) is for *customer devices* talking to an enrolled installation. Both can be online on nickg at once; they are different control planes.

---

## Fill in when known

Update this table as you stabilize addresses (do not put passwords here):

| Lab ID | Hostname | LAN IP | Tailscale / mesh IP | SSH user | Notes |
|---|---|---|---|---|---|
| `lab-home-win-nickg` | `DESKTOP-VDM2JKF` | `192.168.1.71` | `100.73.31.71` (`homenetwork`) | `nickg` | `ssh lab-home-win-nickg` / `ssh desktop-vdm2jkf`; product `ADVERTISE_HOST=192.168.1.71` |
| `lab-work-u24-mini-8g` | `eyenet-server` | `192.168.9.14` | *(logged out — enroll for remote)* | `eyenet` | `ssh eyenet-server`; 8 GB soak; not Stage 2 |
| `lab-work-dual-64g` | | Win hist. `192.168.11.29` | | Win: `user` | Dual-boot; confirm which OS + subnet after boot |

Historical / other boxes (not in the named set above) may still appear in older notes (e.g. `kvalvis-pc` at older Tailscale `100.64.0.23`). Prefer the lab IDs in this document going forward; migrate aliases here when you rename hosts.

---

## Related

- Release CI/CD: [platform-release-cicd.md](./platform-release-cicd.md)  
- Windows via Tailscale walkthrough: [windows-via-tailscale-eyenet-images.md](./windows-via-tailscale-eyenet-images.md)  
- Ubuntu lab bug list: [`deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md`](../../deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md)  
- WSL full-product runtime: [windows-wsl-docker-engine-full-product.md](./windows-wsl-docker-engine-full-product.md)
