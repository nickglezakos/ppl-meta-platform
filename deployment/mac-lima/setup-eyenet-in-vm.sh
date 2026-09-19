#!/usr/bin/env bash
# Run inside the Lima guest: limactl shell eyenet -- bash /path/to/setup-eyenet-in-vm.sh
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/Users/nickgklezakos/Documents/ppl-meta-code}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/eyenet-platform}"
COMPOSE_SRC="$REPO_ROOT/deployment/windows-installer/docker-compose.windows-installer.yml"
ENV_SRC="$REPO_ROOT/deployment/windows-installer/.env.windows.template"
SQL_DIR="$REPO_ROOT/deployment/mac-lima/sql"
SCHEMA_APPLY="$REPO_ROOT/deployment/windows-installer/schema/apply.sh"
BUILD_LOCAL="${BUILD_LOCAL:-1}"

# Always talk to Docker via the docker group. Lima guest sessions often lack
# that group even when the user is (or will be) a member.
docker_() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sg docker -c "docker $(printf '%q ' "$@")"
  fi
}

compose_() {
  if docker info >/dev/null 2>&1; then
    docker compose "$@"
  else
    sg docker -c "docker compose $(printf '%q ' "$@")"
  fi
}

# Best-effort: persist docker group membership for future shells.
if getent group docker >/dev/null 2>&1 && ! id -nG 2>/dev/null | grep -qw docker; then
  echo "Adding $USER to docker group (needs sudo once)..."
  sudo usermod -aG docker "$USER" || true
fi

mkdir -p "$INSTALL_DIR"
cp -f "$COMPOSE_SRC" "$INSTALL_DIR/docker-compose.yml"

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  sed \
    -e 's|^INSTALL_ROOT=.*|INSTALL_ROOT='"$INSTALL_DIR"'|' \
    -e 's|^EYENET_TS_SOCKET_HOST=.*|EYENET_TS_SOCKET_HOST=/var/run/tailscale/tailscaled.sock|' \
    -e 's|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=eyenet-dev-change-me|' \
    "$ENV_SRC" > "$INSTALL_DIR/.env"
  if ! grep -q '^INSTALLATION_UUID=' "$INSTALL_DIR/.env"; then
    echo 'INSTALLATION_UUID=' >> "$INSTALL_DIR/.env"
  fi
  echo "Wrote $INSTALL_DIR/.env (edit APPLICATION_KEY / INSTALLATION_UUID as needed)"
else
  echo "Keeping existing $INSTALL_DIR/.env"
fi

# LAN/Tailscale IP that phones should use (Mac Wi-Fi IP, not Docker 172.x).
# Pass from the Mac host: ADVERTISE_HOST=$(ipconfig getifaddr en0) limactl shell …
if [[ -n "${ADVERTISE_HOST:-}" ]]; then
  if grep -q '^ADVERTISE_HOST=' "$INSTALL_DIR/.env"; then
    sed -i.bak "s|^ADVERTISE_HOST=.*|ADVERTISE_HOST=${ADVERTISE_HOST}|" "$INSTALL_DIR/.env"
  else
    echo "ADVERTISE_HOST=${ADVERTISE_HOST}" >> "$INSTALL_DIR/.env"
  fi
  echo "ADVERTISE_HOST=${ADVERTISE_HOST}"
elif ! grep -q '^ADVERTISE_HOST=.\+' "$INSTALL_DIR/.env" 2>/dev/null; then
  echo "WARNING: ADVERTISE_HOST is unset. Mobile onboarding will get Docker IPs."
  echo "  On the Mac host, re-run with: ADVERTISE_HOST=\$(ipconfig getifaddr en0) limactl shell eyenet -- bash $0"
fi

# shellcheck disable=SC1091
set -a
source "$INSTALL_DIR/.env"
set +a

REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
RELEASE_TAG="${RELEASE_TAG:-2.25.82}"

mkdir -p "$INSTALL_DIR/data"

if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo systemctl enable --now tailscaled || true
sudo mkdir -p /var/run/tailscale
if [[ ! -S /var/run/tailscale/tailscaled.sock ]]; then
  echo "Waiting for tailscaled.sock..."
  for _ in $(seq 1 20); do
    [[ -S /var/run/tailscale/tailscaled.sock ]] && break
    sleep 1
  done
fi

mkdir -p "$INSTALL_DIR/bin"
if [[ ! -x "$INSTALL_DIR/bin/tailscale" ]]; then
  VER="${TAILSCALE_AMD64_VER:-1.76.1}"
  curl -fsSL -o /tmp/ts.tgz "https://pkgs.tailscale.com/stable/tailscale_${VER}_amd64.tgz"
  tar -xzf /tmp/ts.tgz -C /tmp
  cp "/tmp/tailscale_${VER}_amd64/tailscale" "$INSTALL_DIR/bin/tailscale"
  chmod +x "$INSTALL_DIR/bin/tailscale"
fi

cat > "$INSTALL_DIR/docker-compose.override.yml" <<EOF
services:
  ppl-meta-node:
    volumes:
      - ${INSTALL_DIR}/bin/tailscale:/usr/local/bin/tailscale:ro
      - ${INSTALL_DIR}/bin/tailscale:/usr/bin/tailscale:ro
EOF

cd "$INSTALL_DIR"

if [[ "$BUILD_LOCAL" == "1" ]]; then
  echo "Building durable local images (opencv<5, dlib, ffmpeg, stream-token, WS auth, discovery advertise)..."
  docker_ build --platform linux/amd64 \
    -f "$REPO_ROOT/ppl-meta-vision/docker/Dockerfile" \
    -t "${REGISTRY}/ppl-meta-vision-protected:${RELEASE_TAG}" \
    "$REPO_ROOT/ppl-meta-vision"

  docker_ build --platform linux/amd64 \
    -t "${REGISTRY}/ppl-meta-media:${RELEASE_TAG}" \
    "$REPO_ROOT/ppl-meta-media"

  docker_ build --platform linux/amd64 \
    -t "${REGISTRY}/ppl-meta-cameras:${RELEASE_TAG}" \
    "$REPO_ROOT/ppl-meta-cameras"

  docker_ build --platform linux/amd64 \
    -t "${REGISTRY}/ppl-meta-discovery:${RELEASE_TAG}" \
    "$REPO_ROOT/ppl-meta-discovery"

  docker_ build --platform linux/amd64 \
    -t "${REGISTRY}/ppl-meta-node:${RELEASE_TAG}" \
    "$REPO_ROOT/ppl-meta-node"

  if [[ -f "$REPO_ROOT/ppl-meta-frontend/Dockerfile" ]]; then
    docker_ build --platform linux/amd64 \
      -t "${REGISTRY}/ppl-meta-frontend:${RELEASE_TAG}" \
      "$REPO_ROOT/ppl-meta-frontend"
  fi
else
  echo "Pulling published images (BUILD_LOCAL=0)..."
  compose_ --project-name pplmeta --env-file .env -f docker-compose.yml pull
fi

echo "Starting stack..."
compose_ --project-name pplmeta --env-file .env -f docker-compose.yml -f docker-compose.override.yml up -d

# Apply the same SQL the codebase ships (vendored pack synced from repo migrations).
# Fail the install if schema invariants do not match — never fall back to minimal stubs.
SCHEMA_APPLY="${SCHEMA_APPLY:-$REPO_ROOT/deployment/windows-installer/schema/apply.sh}"
if [[ ! -f "$SCHEMA_APPLY" ]]; then
  SCHEMA_APPLY="$REPO_ROOT/deployment/mac-lima/apply-codebase-schema.sh"
fi
if [[ ! -f "$SCHEMA_APPLY" ]]; then
  echo "FATAL: schema apply script missing. Run: bash deployment/mac-lima/sync-schema-pack.sh"
  exit 1
fi
echo "Applying codebase schema via $SCHEMA_APPLY ..."
# Give ORM create_all a moment after first up
sleep 5
bash "$SCHEMA_APPLY"
echo "Schema verify OK."

# Discovery registry is in-memory; seed it with compose DNS hosts so health
# checks work and ADVERTISE_HOST rewriting exposes LAN IPs to mobile clients.
if [[ -f "$REPO_ROOT/deployment/mac-lima/reregister-discovery-services.sh" ]]; then
  bash "$REPO_ROOT/deployment/mac-lima/reregister-discovery-services.sh" || true
fi

compose_ --project-name pplmeta --env-file .env -f docker-compose.yml -f docker-compose.override.yml ps
echo
ADV=$(grep -E '^ADVERTISE_HOST=' "$INSTALL_DIR/.env" | cut -d= -f2- || true)
ADV="${ADV:-127.0.0.1}"
echo "UI:        http://${ADV}:3000  (also http://127.0.0.1:3000 via Lima)"
echo "Gateway:   http://${ADV}:8080"
echo "Node:      http://${ADV}:8001"
echo "Discovery: http://${ADV}:8006   ← use this IP on the mobile camera"
echo "Bootstrap owner account at http://${ADV}:3000/bootstrap with your Authority installation key."
echo
echo "Local rebuilds are tagged as ${REGISTRY}/…:${RELEASE_TAG} so recreate keeps fixes."
echo "Set BUILD_LOCAL=0 to pull published images instead."
echo "Lima LAN publish requires hostIP 0.0.0.0 forwards (see deployment/mac-lima/eyenet.yaml)."
