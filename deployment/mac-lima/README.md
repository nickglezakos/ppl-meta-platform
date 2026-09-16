# EyeNet on Mac via Lima (Apple Silicon)

Ubuntu 24.04 aarch64 guest with Docker Engine. Platform images are `linux/amd64` and run under Rosetta/QEMU.

## One-time create

```bash
brew install lima
# Quit Docker Desktop first so 8 GiB RAM is available for the guest
osascript -e 'quit app "Docker"'
cd deployment/mac-lima
limactl start --name=eyenet --tty=false ./eyenet.yaml
```

## Deploy EyeNet

```bash
# On the Mac host (required before frontend image build):
cd ppl-meta-frontend && flutter build web --release

# Inside Lima (script auto re-runs under `sg docker` if the socket is not writable).
# Pass the Mac LAN IP so discovery advertises a phone-reachable address:
ADVERTISE_HOST="$(ipconfig getifaddr en0)"
limactl shell eyenet -- env ADVERTISE_HOST="$ADVERTISE_HOST" \
  bash /Users/nickgklezakos/Documents/ppl-meta-code/deployment/mac-lima/setup-eyenet-in-vm.sh
```

`setup-eyenet-in-vm.sh` **rebuilds local amd64 images by default** (`BUILD_LOCAL=1`) and **requires** the codebase schema pack:

```bash
# Refresh pack from repo migrations (run on Mac host when migrations change)
bash deployment/mac-lima/sync-schema-pack.sh

# Deploy in Lima — applies schema/pack + verify (fails install if mismatch)
ADVERTISE_HOST="$(ipconfig getifaddr en0)" \
  limactl shell eyenet -- env ADVERTISE_HOST="$ADVERTISE_HOST" \
  bash /Users/nickgklezakos/Documents/ppl-meta-code/deployment/mac-lima/setup-eyenet-in-vm.sh

# Anytime check
limactl shell eyenet -- bash /Users/nickgklezakos/Documents/ppl-meta-code/deployment/mac-lima/verify-codebase-schema.sh
```

Postgres image is **`pgvector/pgvector:pg15`**. Minimal stubs under `sql/archive-stubs/` are **not** applied.

### Mobile / LAN discovery

Lima `eyenet.yaml` publishes discovery (and related ports) on **`0.0.0.0`**, not only `127.0.0.1`. After changing port forwards, recreate or restart the VM:

```bash
limactl stop eyenet
limactl start --name=eyenet --tty=false ./deployment/mac-lima/eyenet.yaml
# or, for an existing instance, merge portForwards into ~/.lima/eyenet/lima.yaml then:
limactl stop eyenet && limactl start eyenet
```

On the phone, point discovery at **`http://<Mac-LAN-IP>:8006`** (same value as `ADVERTISE_HOST`), never a Docker `172.18.x` address.
## Daily use

```bash
limactl start eyenet
limactl shell eyenet -- bash -lc 'cd ~/eyenet-platform && docker compose --project-name pplmeta --env-file .env -f docker-compose.yml up -d'
limactl stop eyenet
```

## Bootstrap

1. In Authority admin (`https://authority.eyenet-vision.com/admin`), create an invite / installation key for a **new** install.
2. Open `http://127.0.0.1:3000/bootstrap` and complete owner setup with that key (fresh postgres → empty local users until this runs).
3. VPN (optional after bootstrap): enroll from Node, then on the guest:
   `sudo tailscale up --login-server https://vpn.eyenet-vision.com --auth-key …`

Env file lives at `~/eyenet-platform/.env` inside the guest (`INSTALLATION_UUID` / `APPLICATION_KEY` start empty).

## Known gaps on published `2.25.81`

Prefer `BUILD_LOCAL=1` (default in `setup-eyenet-in-vm.sh`) so Lima uses rebuilt images that include:

- **vision** — OpenCV `<5`, `dlib-bin`, `two_stage` face detection
- **media** — ffmpeg + stream-token H.264 remux (ORM/schema MediaType fix)
- **cameras** — camera status WS handshake fix (no HTTP 403 on empty token)
- **frontend** — wait for auth token before status WebSocket; don’t crash cameras page on WS errors

Published registry tags alone still need those rebuilds after pull.
## Notes

- Guest: Ubuntu 24.04 aarch64, 8 GiB RAM, 24 GiB disk, Rosetta for `linux/amd64` images.
- Quit Docker Desktop before starting the VM so memory is available.
- Multipass needs an interactive macOS password; Lima was used instead.
