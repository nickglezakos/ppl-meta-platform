#!/usr/bin/env bash
# Native Ubuntu 24.04 lab install: Docker CE + public GHCR images + schema pack.
# Run on the Ubuntu host as a sudo-capable user:
#   bash install-eyenet-ubuntu.sh
set -euo pipefail

ADVERTISE_HOST="${ADVERTISE_HOST:-$(ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | head -1)}"
RELEASE_TAG="${RELEASE_TAG:-2.25.83}"
REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/eyenet-platform}"
REPO_DIR="${REPO_DIR:-$HOME/ppl-meta-platform}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/nickglezakos/ppl-meta-platform.git}"

echo "==> Host: $(hostname)  user=$(whoami)  ADVERTISE_HOST=${ADVERTISE_HOST}"
echo "==> Release: ${REGISTRY} @ ${RELEASE_TAG}"

if ! sudo -n true 2>/dev/null; then
  echo "Sudo password required once for Docker / packages..."
  sudo -v
fi

# --- Docker CE ---
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker CE..."
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
  fi
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" || true

docker_() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

compose_() {
  if docker info >/dev/null 2>&1; then
    docker compose "$@"
  else
    sudo docker compose "$@"
  fi
}

echo "==> Docker: $(docker_ --version)"
echo "==> Compose: $(compose_ version)"

# --- Repo (installer + schema pack) ---
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "==> Cloning ${GITHUB_REPO} -> ${REPO_DIR}"
  git clone --depth 1 "$GITHUB_REPO" "$REPO_DIR"
else
  echo "==> Updating ${REPO_DIR}"
  git -C "$REPO_DIR" fetch --depth 1 origin main
  git -C "$REPO_DIR" checkout main
  git -C "$REPO_DIR" pull --ff-only origin main || true
fi

COMPOSE_SRC="$REPO_DIR/deployment/windows-installer/docker-compose.windows-installer.yml"
ENV_SRC="$REPO_DIR/deployment/windows-installer/.env.windows.template"
SCHEMA_APPLY="$REPO_DIR/deployment/windows-installer/schema/apply.sh"
SCHEMA_PACK="$REPO_DIR/deployment/windows-installer/schema/pack.tar.gz"

[[ -f "$COMPOSE_SRC" ]] || { echo "FATAL: missing $COMPOSE_SRC"; exit 1; }
[[ -f "$SCHEMA_PACK" ]] || { echo "FATAL: missing schema pack $SCHEMA_PACK"; exit 1; }

mkdir -p "$INSTALL_DIR/data"
cp -f "$COMPOSE_SRC" "$INSTALL_DIR/docker-compose.yml"

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  sed \
    -e "s|^INSTALL_ROOT=.*|INSTALL_ROOT=${INSTALL_DIR}|" \
    -e "s|^EYENET_TS_SOCKET_HOST=.*|EYENET_TS_SOCKET_HOST=/var/run/tailscale/tailscaled.sock|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=eyenet-dev-change-me|" \
    -e "s|^ADVERTISE_HOST=.*|ADVERTISE_HOST=${ADVERTISE_HOST}|" \
    -e "s|^RELEASE_TAG=.*|RELEASE_TAG=${RELEASE_TAG}|" \
    -e "s|^REGISTRY=.*|REGISTRY=${REGISTRY}|" \
    "$ENV_SRC" > "$INSTALL_DIR/.env"
  grep -q '^INSTALLATION_UUID=' "$INSTALL_DIR/.env" || echo 'INSTALLATION_UUID=' >> "$INSTALL_DIR/.env"
  echo "Wrote $INSTALL_DIR/.env"
else
  if grep -q '^ADVERTISE_HOST=' "$INSTALL_DIR/.env"; then
    sed -i.bak "s|^ADVERTISE_HOST=.*|ADVERTISE_HOST=${ADVERTISE_HOST}|" "$INSTALL_DIR/.env"
  else
    echo "ADVERTISE_HOST=${ADVERTISE_HOST}" >> "$INSTALL_DIR/.env"
  fi
  echo "Keeping existing $INSTALL_DIR/.env (ADVERTISE_HOST refreshed)"
fi

# Optional: Tailscale (best-effort; stack works without it for LAN)
if ! command -v tailscale >/dev/null 2>&1; then
  echo "==> Installing Tailscale (optional VPN client)..."
  curl -fsSL https://tailscale.com/install.sh | sudo sh || true
fi
sudo systemctl enable --now tailscaled 2>/dev/null || true

cd "$INSTALL_DIR"
echo "==> Pulling published images..."
compose_ --project-name pplmeta --env-file .env -f docker-compose.yml pull

echo "==> Starting stack..."
compose_ --project-name pplmeta --env-file .env -f docker-compose.yml up -d

# Media runs as uid 1001; fresh Docker volumes are root:root (upload Permission denied).
PERMS_SRC="$REPO_DIR/deployment/windows-installer/ensure-media-volume-perms.sh"
if [[ -f "$PERMS_SRC" ]]; then
  bash "$PERMS_SRC" || echo "WARN: media volume perms fix failed (non-fatal)"
else
  echo "WARN: ensure-media-volume-perms.sh missing — Media uploads may hit Permission denied"
fi

echo "==> Waiting for Postgres..."
for _ in $(seq 1 60); do
  if compose_ --project-name pplmeta --env-file .env -f docker-compose.yml exec -T postgres \
    pg_isready -U pplmeta -d ppl_db >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> Applying schema pack (+ verify)..."
INSTALL_DIR="$INSTALL_DIR" SCHEMA_PACK_DIR="$REPO_DIR/deployment/windows-installer/schema/pack" \
  bash "$SCHEMA_APPLY"
SCHEMA_VERIFY="$REPO_DIR/deployment/windows-installer/schema/verify.sh"
if [[ -f "$SCHEMA_VERIFY" ]]; then
  INSTALL_DIR="$INSTALL_DIR" bash "$SCHEMA_VERIFY"
fi

REREG="$REPO_DIR/deployment/windows-installer/reregister-discovery-services.sh"
[[ -f "$REREG" ]] || REREG="$REPO_DIR/deployment/mac-lima/reregister-discovery-services.sh"
if [[ -f "$REREG" ]]; then
  echo "==> Re-registering services with discovery..."
  cp -f "$REREG" "$INSTALL_DIR/reregister-discovery-services.sh"
  chmod +x "$INSTALL_DIR/reregister-discovery-services.sh"
  ( cd "$INSTALL_DIR" && bash reregister-discovery-services.sh ) || echo "WARN: discovery reregister failed (non-fatal)"
else
  echo "WARN: reregister-discovery-services.sh missing — mobile discovery may be incomplete"
fi

TIMER_SRC="$REPO_DIR/deployment/ubuntu/install-discovery-reregister-timer.sh"
if [[ -f "$TIMER_SRC" ]]; then
  echo "==> Installing required discovery re-register systemd timer..."
  if command -v systemctl >/dev/null 2>&1; then
    if [[ "$(id -u)" -eq 0 ]]; then
      INSTALL_DIR="$INSTALL_DIR" bash "$TIMER_SRC" || echo "WARN: discovery re-register timer install failed"
    elif command -v sudo >/dev/null 2>&1; then
      sudo env INSTALL_DIR="$INSTALL_DIR" bash "$TIMER_SRC" || echo "WARN: discovery re-register timer install failed (need sudo)"
    else
      echo "WARN: run as root/sudo to install required discovery re-register timer:"
      echo "  sudo INSTALL_DIR=$INSTALL_DIR bash $TIMER_SRC"
    fi
  fi
fi

compose_ --project-name pplmeta --env-file .env -f docker-compose.yml ps

# --- Host tray (soft-fail if GitHub Release asset missing) ---
echo "==> Installing EyeNet tray (host control)..."
TRAY_DIR="$INSTALL_DIR/tray"
mkdir -p "$TRAY_DIR"
TRAY_TAG="v${RELEASE_TAG}"
TRAY_ASSET="eyenet-tray-linux-amd64-${RELEASE_TAG}.tar.gz"
TRAY_URL="https://github.com/nickglezakos/ppl-meta-platform/releases/download/${TRAY_TAG}/${TRAY_ASSET}"
TRAY_CFG="$TRAY_DIR/tray.json"
if curl -fsSL "$TRAY_URL" -o "$TRAY_DIR/$TRAY_ASSET"; then
  tar -xzf "$TRAY_DIR/$TRAY_ASSET" -C "$TRAY_DIR"
  TRAY_BIN="$TRAY_DIR/eyenet-tray"
  chmod +x "$TRAY_BIN" 2>/dev/null || true
  # Prefer binary named eyenet-tray; accept versioned name from tarball
  if [[ ! -x "$TRAY_BIN" ]]; then
    found="$(find "$TRAY_DIR" -maxdepth 1 -type f -name 'eyenet-tray*' ! -name '*.tar.gz' | head -1 || true)"
    if [[ -n "$found" ]]; then
      mv -f "$found" "$TRAY_BIN"
      chmod +x "$TRAY_BIN"
    fi
  fi
  cat >"$TRAY_CFG" <<EOF
{
  "install_dir": "${INSTALL_DIR}",
  "mode": "native",
  "wsl_distro": "eyenet",
  "project": "pplmeta",
  "compose_file": "docker-compose.yml",
  "env_file": ".env",
  "ui_url": "http://127.0.0.1:3000",
  "version": "${RELEASE_TAG}",
  "reregister_script": "${REPO_DIR}/deployment/windows-installer/reregister-discovery-services.sh"
}
EOF
  if [[ -x "$TRAY_BIN" ]]; then
    if [[ -f "$REPO_DIR/deployment/tray/scripts/install-autostart-ubuntu.sh" ]]; then
      bash "$REPO_DIR/deployment/tray/scripts/install-autostart-ubuntu.sh" "$TRAY_BIN" "$TRAY_CFG" || true
    else
      mkdir -p "$HOME/.config/autostart"
      cat >"$HOME/.config/autostart/eyenet-tray.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=EyeNet Tray
Exec=${TRAY_BIN} ${TRAY_CFG}
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
      nohup "$TRAY_BIN" "$TRAY_CFG" >/dev/null 2>&1 &
    fi
    echo "Tray installed under $TRAY_DIR"
  else
    echo "WARN: tray binary missing after extract"
  fi
else
  echo "WARN: tray download skipped (Release asset may not exist yet): $TRAY_URL"
fi

echo
echo "Verify ADVERTISE_HOST is this machine's LAN IP (phones use it):"
echo "  ip -4 addr show scope global"
echo
echo "UI:        http://${ADVERTISE_HOST}:3000"
echo "Gateway:   http://${ADVERTISE_HOST}:8080"
echo "Discovery: http://${ADVERTISE_HOST}:8006"
echo "Bootstrap: http://${ADVERTISE_HOST}:3000/bootstrap"
echo "Network:   http://${ADVERTISE_HOST}:3000/network"
echo
echo "Done. If 'docker' says permission denied later, log out/in or run: newgrp docker"
