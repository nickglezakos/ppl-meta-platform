# Ubuntu lab EyeNet — day-to-day operator guide

**Status:** Active  
**Audience:** You (Mac) operating a native Ubuntu lab such as `lab-work-dual-64g` (`eyenet-demo`)  
**Install dir on lab:** `~/eyenet-platform`  
**Compose project:** `pplmeta`  
**Related:** [lab-machines.md](../deployment/lab-machines.md) · [platform-release-cicd.md](../deployment/platform-release-cicd.md) · [eyenet-cicd-operator-guide.md](../deployment/eyenet-cicd-operator-guide.md) · `artifacts/lab-fix-advertise-host.sh`

This guide covers **Mac vs lab roles**, lab **start / stop / health**, and **LAN IP changes**. Full Stage 1/2/3 release detail lives in the CICD docs.

---

## 1. Mac source vs lab VMs (how to use both)

Keep two environments. Do not mix their networking or discovery.

| Role | Where | What you run |
|------|--------|--------------|
| Day-to-day coding / UI / API debug | Mac | VS Code task **Start All Local Python Services** + Flutter on `:3000` |
| Ship source | Mac → GitHub | **Stage 1** — commit + push affected services |
| Build `linux/amd64` images | Lab PC (prefer `lab-work-dual-64g`) | **Stage 2** — Docker build + push to GHCR |
| Run product-like stack | Lab VM/PC (`~/eyenet-platform`) | **Stage 3** — installer pull from GHCR + tray |

Your Mac is Apple Silicon. Lab / customer images are **`linux/amd64` only**. Use a lab PC for Stage 2; do not treat the Mac as the default image builder.

### Daily flow

1. Edit and debug on the **Mac** with local Python services.
2. When the change should stick: **Stage 1** — push the affected services (and CHANGELOG when required).
3. When labs should get new containers: **Stage 2** on the amd64 lab builder.
4. When a named lab should run that pin: **Stage 3** install / upgrade on that lab.

### Keep environments separate

| | Mac local Python | Lab Docker / installer |
|--|------------------|------------------------|
| Service URLs | `127.0.0.1` / `localhost` via `scripts/load-local-python-runtime-env.sh` (VS Code local Python tasks) | Compose DNS (`ppl-meta-*`) |
| Discovery advertise | Mac LAN IP only if you need phones against the Mac | `ADVERTISE_HOST=<lab LAN IP>` in `~/eyenet-platform/.env` |
| UI | `http://localhost:3000` | `http://<lab-LAN-IP>:3000` |
| Discovery for phones | Mac `:8006` only when testing against Mac | Lab `:8006` |

Rules:

- Do **not** point Mac discovery at the lab, or lab `ADVERTISE_HOST` at the Mac.
- Do **not** expect compose hostnames (`ppl-meta-gateway`, …) to resolve on the Mac.
- A lab that “works” after `docker cp` or a one-off patch is **debug**, not a release. Lasting fixes go Stage 1 → Stage 2 → Stage 3.

### Optional: Lima on the Mac

[`deployment/mac-lima/`](../../../deployment/mac-lima/) is for a **Docker-shaped** smoke check on the Mac. It is optional.

- Use it when you want compose/installer behaviour close to the lab path before Stage 2.
- It does **not** replace Stage 2 on an amd64 lab, or Stage 3 on lab hosts.
- If Lima and local Python fight over the same ports, stop one stack before starting the other.

### Say this to the agent (or yourself)

| Goal | Phrase |
|------|--------|
| Code on Mac | “Start local Python services / fix this on Mac” |
| Ship source | “Stage 1 per platform-release-cicd.md” |
| Build images | “Stage 2 on lab-work-dual-64g for VERSION …” |
| Upgrade a lab | “Stage 3 / upgrade lab-work-dual-64g” (or named host) |
| Lab day-to-day | This guide (§2 onward) |

---

## 2. SSH into the lab

Confirm the lab is reachable and note its current IPs:

```bash
ssh eyenet@192.168.1.90 'hostname; systemctl is-active ssh; hostname -I'
```

Typical output:

```text
eyenet-demo
active
192.168.1.90 100.101.128.40 …
```

- First address is usually the **LAN** IP phones/tablets should use.
- `100.x.x.x` is **Tailscale** (optional remote path).
- If SSH fails with “Connection refused”, on the lab: `sudo systemctl enable --now ssh`.
- If it times out, check Wi‑Fi/subnet — the IP may have changed (see §5).

Interactive shell:

```bash
ssh eyenet@192.168.1.90
cd ~/eyenet-platform
```

**Note:** Cursor agent shells are often sandboxed and cannot reach private LAN IPs. Your Mac terminal can; approve **full network / all** if you want the agent to SSH for you.

---

## 3. Compose file used on this lab

Most Ubuntu installs use one of:

| File | When |
|------|------|
| `docker-compose.windows-installer.yml` | Copied from the shared installer pack (common) |
| `docker-compose.yml` | Some installs rename / symlink |

Check:

```bash
ls ~/eyenet-platform/docker-compose*.yml
```


In the commands below, set:

```bash
cd ~/eyenet-platform
COMPOSE=docker-compose.windows-installer.yml   # or docker-compose.yml
PROJECT=pplmeta
```

---

## 4. Start / stop / status

### Tray (optional)

If the host tray is installed (`~/eyenet-platform/tray/`), use the menu: **Start / Stop / Restart** and status (Active / Inactive / Degraded).

### CLI — start (or bring stack back up)

```bash
cd ~/eyenet-platform
docker compose --project-name pplmeta --env-file .env \
  -f docker-compose.windows-installer.yml up -d
```

### CLI — stop (containers stop; volumes / DB kept)

```bash
docker compose --project-name pplmeta --env-file .env \
  -f docker-compose.windows-installer.yml stop
```

### CLI — down (remove containers; volumes kept unless you add `-v`)

```bash
docker compose --project-name pplmeta --env-file .env \
  -f docker-compose.windows-installer.yml down
```

Do **not** use `-v` unless you intend to wipe Postgres/media data.

### CLI — status

```bash
docker compose --project-name pplmeta --env-file .env \
  -f docker-compose.windows-installer.yml ps

docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}' | head -30
```

### After hibernate / reboot (same LAN IP)

Containers may already be up (`restart: unless-stopped`). If discovery looks thin on `/network`:

```bash
cd ~/eyenet-platform
bash ./reregister-discovery-services.sh
```

---

## 5. Health checks

From the lab (or via SSH):

```bash
curl -sS -o /dev/null -w "ui:%{http_code}\n"        --max-time 8 http://127.0.0.1:3000/
curl -sS -o /dev/null -w "gw:%{http_code}\n"        --max-time 8 http://127.0.0.1:8080/health
curl -sS -o /dev/null -w "media:%{http_code}\n"     --max-time 8 http://127.0.0.1:8000/health
curl -sS -o /dev/null -w "discovery:%{http_code}\n" --max-time 8 http://127.0.0.1:8006/health
curl -sS -o /dev/null -w "node:%{http_code}\n"      --max-time 8 http://127.0.0.1:8001/health
```

Expect `200` (UI may be `200` on `/`).

From your Mac (use the lab’s **current** LAN IP):

```bash
open http://192.168.1.90:3000
curl -sS -o /dev/null -w "gw:%{http_code}\n" http://192.168.1.90:8080/health
```

Pin in env:

```bash
grep -E '^(RELEASE_TAG|ADVERTISE_HOST|REGISTRY)=' ~/eyenet-platform/.env
```

---

## 6. When you change host network (LAN IP changes)

**Do this only when the lab’s reachable IP changes** (e.g. work `192.168.9.13` → home `192.168.1.90`).  
Same IP after reboot → skip this section; use §4 “after hibernate” if needed.

### Why it matters

| Piece | Effect of stale IP |
|-------|-------------------|
| `ADVERTISE_HOST` in `.env` | Discovery / service URLs advertise the wrong address to phones |
| `ppl-meta-node` | `TrustedHostMiddleware` allow-list is fixed at process start → LAN login can return **HTTP 400 `Invalid host header`** (not a password error) |
| Discovery / gateway | Clients still resolve old host / wrong service URLs |

### Recommended: one script from the Mac

From the repo on your Mac:

```bash
chmod +x artifacts/lab-fix-advertise-host.sh
./artifacts/lab-fix-advertise-host.sh eyenet@NEW_IP NEW_IP
```

Example:

```bash
./artifacts/lab-fix-advertise-host.sh eyenet@192.168.1.90 192.168.1.90
```

The script:

1. Sets `ADVERTISE_HOST` in `~/eyenet-platform/.env`
2. Force-recreates **node**, **discovery**, and **gateway**
3. Runs discovery reregister when available
4. Prints health curls

### Manual equivalent (on the lab)

```bash
cd ~/eyenet-platform
# replace with the new LAN IP
sed -i.bak -e 's/^ADVERTISE_HOST=.*/ADVERTISE_HOST=192.168.1.90/' .env
grep ADVERTISE_HOST .env

docker compose -p pplmeta -f docker-compose.windows-installer.yml --env-file .env \
  up -d --force-recreate --no-deps \
  ppl-meta-node ppl-meta-discovery ppl-meta-gateway

bash ./reregister-discovery-services.sh
```

### Verify after IP change

```bash
# Must NOT say "Invalid host header"
curl -sS -w "\nHTTP:%{http_code}\n" -X POST http://NEW_IP:8001/api/v1/users/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=you@example.com&password=YOUR_PASSWORD'
```

- `200` + `access_token` → good  
- `400` + `"Incorrect email or password"` → real auth issue  
- `400` + `Invalid host header` → node still needs recreate with new `ADVERTISE_HOST`

Point mobile camera / signage discovery at `http://NEW_IP:8006`.

---

## 7. Quick cheat sheet

| Goal | Command / place |
|------|-----------------|
| Mac code / debug | Local Python task + Flutter `:3000` |
| Ship source | Stage 1 — [platform-release-cicd.md](../deployment/platform-release-cicd.md) |
| Build images | Stage 2 on amd64 lab |
| Upgrade lab stack | Stage 3 installer / tray |
| SSH | `ssh eyenet@<LAN_IP>` |
| Start | `cd ~/eyenet-platform && docker compose -p pplmeta --env-file .env -f docker-compose.windows-installer.yml up -d` |
| Stop | `… stop` |
| Status | `… ps` |
| Health | `curl` UI `:3000`, gw `:8080/health`, media `:8000/health`, discovery `:8006/health`, node `:8001/health` |
| Same IP after sleep | `bash ~/eyenet-platform/reregister-discovery-services.sh` |
| New LAN IP | `./artifacts/lab-fix-advertise-host.sh eyenet@NEW_IP NEW_IP` |

---

## 8. What this guide is not

- Full **Stage 1 / 2 / 3** procedure: [platform-release-cicd.md](../deployment/platform-release-cicd.md) · [eyenet-cicd-operator-guide.md](../deployment/eyenet-cicd-operator-guide.md)
- Lab inventory / Tailscale Host aliases: [lab-machines.md](../deployment/lab-machines.md)
- Mac Lima VM setup: [`deployment/mac-lima/README.md`](../../../deployment/mac-lima/README.md)
- VPN mesh enroll: guides under `docs/documentation/guides/authority/` and `headscaleVPN/`
