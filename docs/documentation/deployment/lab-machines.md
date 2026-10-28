# Lab machines inventory

**Status:** Active  
**Last updated:** 2026-10-20  
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
| **`lab-work-dual-64g`** | Work LAN | Dual-boot Windows + Ubuntu 24.04 | Laptop, **16 GB RAM** (lab ID keeps historical “64g” name) | Primary work lab; Stage 3 soak |
| **`lab-work-eyenet2`** | Work LAN | Ubuntu 24.04 only | Laptop / desktop, **16 GB RAM**, hostname `eyenet2` | Second Ubuntu soak / install path |
| **`lab-work-win-eynetdell`** | Work LAN | Windows only | Dell PC, hostname `EYNETDELL`, **32 GB RAM** | **Preferred Stage 2** (WSL `eyenet` + Docker) + Windows soak; LAN SSH `Administrator@192.168.9.11` |

Use these **lab IDs** in chat, CHANGELOG notes, and agent instructions (e.g. *“Stage 2 on lab-work-dual-64g”*).

---

## Fleet status (vs GHCR)

**GHCR truth:** [`deployment/windows-installer/release-manifest.yml`](../../deployment/windows-installer/release-manifest.yml) for pin **`2.25.104`** (Mode D; last finalized **2026-10-28** — gateway `bd78deff018b…`, frontend `885b9752a71a…`, vmeta `75e7f374d7cb…`, cameras `ad18861f371f…`; vision retagged `fdc1f5f847c0…`).  
**Rule:** After every **Stage 3** on a named lab, update this table (pin, match state, date, short notes). Do not treat a matching *tag* as current — compare **running container Image ID** (and ideally `main.dart.js` sha256) to the manifest. Tag RepoDigests alone can lie if the container was not recreated.

| Lab ID | Pin | Match GHCR? | Last Stage 3 | Notes |
|---|---|---|---|---|
| `lab-home-win-nickg` | `2.25.83` | **Yes** (frontend `3afac7f6…`, vmeta `28dc8f0a…`) | 2026-09-21 | Overlay frame-dim fallback + FaceNet MVR embedding fix. Offline during 2.25.104 Stage 3. |
| `lab-work-u24-mini-8g` | `2.25.83` | **Yes** (frontend `3afac7f6…`, vmeta `28dc8f0a…`) | 2026-09-21 | Same; hard-refresh UI once. Offline during 2.25.104 Stage 3. |
| `lab-work-dual-64g` | `2.25.104` | **Yes** (gateway `bd78deff018b…`, frontend `885b9752a71a…`, cameras `ad18861f371f…`, vmeta `75e7f374d7cb…`) | 2026-10-28 | Ubuntu `eyenet-demo` @ `192.168.9.13` / Tailscale `100.101.128.40`; wiki zip in-place (`RELEASE_TAG=2.25.104`); schema verify OK; discovery 11/11; UI/gw/media 200. |
| `lab-work-eyenet2` | `2.25.93` | **Yes** (fresh Ubuntu Stage 3) | 2026-09-29 | Hostname `eyenet2` @ `192.168.9.8` / Tailscale `100.116.59.7`; empty UUID/key → `/bootstrap`. Offline during 2.25.104 Stage 3. |
| `lab-work-win-eynetdell` | `2.25.104` | **Yes** (gateway `bd78deff018b…`, frontend `885b9752a71a…`, cameras `ad18861f371f…`, vmeta `75e7f374d7cb…`) | 2026-10-28 | Wiki zip in-place on WSL `eyenet` / `C:\ppl-meta-platform`; `ADVERTISE_HOST=192.168.9.11` / Tailscale `100.114.224.54`; schema verify OK; discovery 11/11; UI/gw/media 200. |

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

Professionally built local network with labs on related office subnets:

- Ubuntu-only mini PC (undersized RAM on purpose) — currently on **`192.168.9.0/24`**
- Dual-boot Windows / Ubuntu 24 laptop (oversized RAM) — Windows session historically on **`192.168.11.0/24`**
- Windows-only Dell (`EYNETDELL` / Tailscale `eynetdell`) — work LAN + personal Tailscale `100.114.224.54`

Same office building; Mac on work Wi‑Fi is typically `192.168.9.x`. Remote access: enroll the lab in personal Tailscale (or stay on work LAN), then SSH (Linux) or Windows App / RDP (Windows). For `lab-work-win-eynetdell`, use the reverse-tunnel SSH path documented below (direct Tailscale → Windows host TCP is broken as of 2026-10-20).

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
| Site | Work LAN (`192.168.9.0/24` when on work Wi‑Fi) |
| OS | **Dual-boot:** Windows 10/11 amd64 **or** Ubuntu 24.04 (reboot to switch) |
| RAM | **16 GB** (operator-confirmed 2026-10-27; lab ID still `lab-work-dual-64g`) |
| Hostname (Ubuntu) | `eyenet-demo` |
| Windows LAN (historical) | `192.168.11.29` (SSH host alias `windows-lab`, user `user`) — confirm after each boot |
| Ubuntu LAN | **`192.168.9.13`** (also seen as `10.171.48.228`); set `ADVERTISE_HOST` to current LAN IP |
| Access (LAN) | Windows: Windows App / RDP → LAN IP (or `ssh windows-lab`). Ubuntu: `ssh eyenet@192.168.9.13` |
| Access (remote) | Tailscale `100.101.128.40` when mesh is up |
| Install dir (Ubuntu) | `~/eyenet-platform` (user `eyenet`) |
| Product path (Windows) | WSL `eyenet` + Windows installer |
| Product path (Ubuntu) | Native Docker CE + `deployment/ubuntu/install-eyenet-ubuntu.sh` |
| Stage 2 builder? | Light / selective only (**16 GB**); full Mode D (esp. vmeta/frontend) needs headroom — prefer a host with ≥24 GB visible to Docker/WSL |
| Notes | Only one OS active at a time. Use for Stage 3 soak / wiki-install validation. GHCR pull can hit stub-resolver timeouts — retry `docker compose pull`. If schema verify fails on first apply, drop app-created `schema_migrations` (wrong shape vs pack) and re-run `schema/apply.sh`. |

---

### `lab-work-eyenet2`

| Field | Value |
|---|---|
| Site | Work LAN (`192.168.9.0/24`) |
| OS | **Ubuntu 24.04 only** |
| Hostname | `eyenet2` |
| RAM | **16 GB** (operator-corrected 2026-10-27) |
| LAN | **`192.168.9.8`** (`wlo1`) |
| Tailscale | **`100.116.59.7`** (personal Tailscale; hostname `eyenet2`) |
| SSH user | `eyenet` (Mac key `eyenet-mac-to-kvalvis`; passwordless sudo configured 2026-09-29) |
| Access (LAN) | `ssh eyenet@192.168.9.8` |
| Access (remote) | `ssh eyenet@100.116.59.7` |
| Install dir | `~/eyenet-platform` |
| Repo clone | `~/ppl-meta-platform` |
| Product path | Native Docker CE + `deployment/ubuntu/install-eyenet-ubuntu.sh` |
| Stage 2 builder? | **No** — prefer `lab-work-win-eynetdell` (32 GB) |
| Notes | Stage 3 soak / Ubuntu path. Prior pin **2.25.93** (2026-09-29). `ADVERTISE_HOST=192.168.9.8`. UI `http://192.168.9.8:3000`. |

---

### `lab-work-win-eynetdell`

| Field | Value |
|---|---|
| Site | Work LAN (`192.168.9.0/24`) |
| OS | **Windows only** (account **`administrator`**; hostname `EYNETDELL`) |
| RAM | **32 GB** (operator-confirmed 2026-10-27) — **preferred Stage 2 builder** |
| Tailscale name | `eynetdell` (personal Tailscale / default account; MagicDNS `eynetdell.tailc2d351.ts.net`) |
| Tailscale IP | **`100.114.224.54`** |
| SSH user | `administrator` (`eynetdell\administrator`) |
| Access (LAN) | **`ssh Administrator@192.168.9.11`** (proven 2026-10-27); OpenSSH on `0.0.0.0:22` |
| Access (remote) | Reverse tunnel still valid if off-LAN (see below). Mesh IP alone may not accept SSH. |
| Stage 2 builder? | **Yes — preferred** (32 GB host). Builds run in WSL distro **`eyenet`**. Give WSL enough RAM via `%UserProfile%\.wslconfig` (e.g. `memory=24GB`) then `wsl --shutdown` — default WSL often caps ~8 Gi and will OOM Mode D. |
| Product path | Windows installer + WSL2 distro **`eyenet`** (Docker Engine CE); wiki zip install path proven 2026-10-20 |
| Install dir | `C:\ppl-meta-platform` (WSL: `/mnt/c/ppl-meta-platform`); Stage 2 clone also at `/home/eyenet/ppl-meta-platform` |
| Product LAN / ADVERTISE_HOST | Confirm with `ipconfig` (historically `192.168.1.105`; work LAN also seen as `192.168.9.11`) |
| Notes | Stage 2 for **2.25.104+** targets this host. Stage 3 from [wiki First install](https://wiki.eyenet-vision.com/owners-admins/) zip. |

#### Prerequisites (remote SSH)

1. **Personal Tailscale** up on the operator Mac **and** on `EYNETDELL` (`tailscale status` shows `eynetdell` online).
2. **OpenSSH Server** installed and running on Windows:
   ```powershell
   Get-Service sshd   # must be Running
   netstat -ano | findstr ":22"   # LISTENING on 0.0.0.0:22
   ```
3. **Operator Mac accepts SSH** (Remote Login / `sshd` listening on `:22`, reachable at the Mac’s Tailscale IP — currently `100.102.56.67`).
4. **Reverse tunnel** started **on Windows** (keep this session alive):
   ```powershell
   ssh -N -R 2201:127.0.0.1:22 <mac-user>@100.102.56.67
   ```
5. Optional but recommended: key-based auth Mac↔Windows both directions so the tunnel and operator SSH are non-interactive.

#### How to SSH (operator Mac)

With the reverse tunnel up:

```bash
ssh -p 2201 administrator@127.0.0.1
```

Quick check:

```bash
ssh -p 2201 administrator@127.0.0.1 'hostname & whoami'
# expect: EYNETDELL / eynetdell\administrator
```

#### Broken path (do not use until fixed)

```bash
ssh administrator@100.114.224.54   # times out — host TCP not delivered over Tailscale
ssh administrator@eynetdell        # same
```

If the tunnel drops, re-run the `ssh -N -R 2201:…` command on Windows before retrying from the Mac.

---

## Roles vs release stages

| Lab ID | Stage 1 (git) | Stage 2 (GHCR build) | Install / soak test |
|---|---|---|---|
| Operator Mac | **Yes** (usual) | No (default) | No |
| `lab-home-win-nickg` | Rarely | Optional (Tailscale OK) | Windows/WSL customer path |
| `lab-work-u24-mini-8g` | No | **No** | Ubuntu under-threshold |
| `lab-work-dual-64g` | Rarely | No (16 GB) | Full Windows **or** full Ubuntu soak / Stage 3 |
| `lab-work-eyenet2` | Rarely | No (16 GB) | Ubuntu soak |
| `lab-work-win-eynetdell` | No | **Preferred** (32 GB WSL) | Stage 2 builds + Windows soak |

Agent wording examples:

- *“Stage 2 on lab-work-win-eynetdell (WSL eyenet).”*
- *“Stage 2 on lab-work-dual-64g — light only; prefer eyenetdell.”*
- *“Upgrade lab-home-win-nickg after Stage 2.”*  
- *“Reproduce under-RAM behavior on lab-work-u24-mini-8g.”*
- *“SSH eyenet-server / lab-work-u24-mini-8g from work LAN.”*
- *“Upgrade / soak lab-work-eyenet2 (eyenet2).”*
- *“SSH lab-work-win-eynetdell via reverse tunnel (`ssh -p 2201 administrator@127.0.0.1`).”*

---

## Access cheat sheet

### LAN (same site as the machine)

| Target | Tool |
|---|---|
| `lab-home-win-nickg` | `ssh desktop-vdm2jkf` or Windows App → `192.168.1.71` |
| `lab-work-u24-mini-8g` | `ssh eyenet-server` → `192.168.9.14` (user `eyenet`) |
| `lab-work-dual-64g` (Windows booted) | Windows App → work LAN IP / `ssh windows-lab` if `192.168.11.29` is up |
| `lab-work-dual-64g` (Ubuntu booted) | `ssh eyenet@192.168.9.13` (hostname `eyenet-demo`; confirm IP after each boot) |
| `lab-work-eyenet2` | `ssh eyenet@192.168.9.8` (hostname `eyenet2`) |
| `lab-work-win-eynetdell` | `ssh Administrator@192.168.9.11` |

### Access (remote)

1. Bring up **personal Tailscale** (default account — not EyeNet product VPN) on the Mac.  
2. Confirm the lab appears: `tailscale status` / `tailscale ping <lab>`.  
3. Connect with the **same tool as LAN**, but use the **mesh IP** (`100.x`), not `192.168.x.x`.  
   **Exception — `lab-work-win-eynetdell`:** after Tailscale is up, start the reverse tunnel on Windows, then SSH to `127.0.0.1:2201` (see host details). Mesh IP alone is not enough for SSH today.

Known remote SSH aliases today:

| Lab ID | SSH alias | Mesh IP |
|---|---|---|
| `lab-home-win-nickg` | `lab-home-win-nickg` | `100.73.31.71` |
| `lab-work-u24-mini-8g` | *(none yet — enroll Tailscale, then add Host)* | — |
| `lab-work-dual-64g` | *(optional Host)* | `100.101.128.40` (`eyenet-demo`) |
| `lab-work-eyenet2` | *(optional Host)* | `100.116.59.7` (`eyenet2`) |
| `lab-work-win-eynetdell` | *(none — use reverse tunnel)* | `100.114.224.54` (`eynetdell`) → then `ssh -p 2201 administrator@127.0.0.1` |

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
| `lab-work-dual-64g` | `eyenet-demo` (Ubuntu) | Ubuntu `192.168.9.13` (confirm after boot; hist. `10.171.48.228` / Win `192.168.11.29`) | `100.101.128.40` | Ubuntu: `eyenet` / Win: `user` | **16 GB** — Stage 3 soak; product `ADVERTISE_HOST` = current LAN IP |
| `lab-work-eyenet2` | `eyenet2` | `192.168.9.8` | `100.116.59.7` | `eyenet` | **16 GB** soak; `ADVERTISE_HOST=192.168.9.8` |
| `lab-work-win-eynetdell` | `EYNETDELL` | `192.168.9.11` (also hist. `192.168.1.105`) | `100.114.224.54` (`eynetdell`) | `administrator` | **32 GB** preferred Stage 2. LAN: `ssh Administrator@192.168.9.11`. WSL `.wslconfig` memory≥24GB for Mode D. |

Historical / other boxes (not in the named set above) may still appear in older notes (e.g. `kvalvis-pc` at older Tailscale `100.64.0.23`). Prefer the lab IDs in this document going forward; migrate aliases here when you rename hosts.

---

## Related

- Release CI/CD: [platform-release-cicd.md](./platform-release-cicd.md)  
- Windows via Tailscale walkthrough: [windows-via-tailscale-eyenet-images.md](./windows-via-tailscale-eyenet-images.md)  
- Ubuntu lab bug list: [`deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md`](../../deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md)  
- WSL full-product runtime: [windows-wsl-docker-engine-full-product.md](./windows-wsl-docker-engine-full-product.md)
