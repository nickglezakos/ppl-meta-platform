#!/usr/bin/env bash
# Pack customer Ubuntu installer zip for wiki.eyenet-vision.com downloads.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
NAME="eyenet-ubuntu-${VERSION}"
OUT_DIR="${OUT_DIR:-$ROOT/artifacts/$NAME}"
ZIP_PATH="${ZIP_PATH:-$ROOT/artifacts/${NAME}.zip}"
WIN="$ROOT/deployment/windows-installer"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/schema" "$OUT_DIR/tray"

cp -f "$ROOT/deployment/ubuntu/install-eyenet-ubuntu.sh" "$OUT_DIR/"
cp -f "$ROOT/deployment/ubuntu/install-discovery-reregister-timer.sh" "$OUT_DIR/"
cp -f "$WIN/docker-compose.windows-installer.yml" "$OUT_DIR/docker-compose.yml"
cp -f "$WIN/.env.windows.template" "$OUT_DIR/.env.windows.template"
cp -f "$WIN/ensure-media-volume-perms.sh" "$OUT_DIR/"
cp -f "$WIN/reregister-discovery-services.sh" "$OUT_DIR/"
cp -f "$WIN/schema/apply.sh" "$OUT_DIR/schema/"
cp -f "$WIN/schema/verify.sh" "$OUT_DIR/schema/"
cp -f "$WIN/schema/pack.tar.gz" "$OUT_DIR/schema/"
# Standalone apply.sh uses SCHEMA_PACK_DIR/pack SQL files when present.
if [[ -d "$WIN/schema/pack" ]]; then
  mkdir -p "$OUT_DIR/schema/pack"
  cp -a "$WIN/schema/pack/." "$OUT_DIR/schema/pack/"
fi
cp -f "$ROOT/deployment/tray/scripts/install-autostart-ubuntu.sh" "$OUT_DIR/"

# Optional: include linux tray tarball if already built for this pin.
for cand in \
  "$ROOT/artifacts/eyenet-tray-linux-amd64-${VERSION}.tar.gz" \
  "$ROOT/deployment/tray/eyenet-tray-linux-amd64-${VERSION}.tar.gz"
do
  if [[ -f "$cand" ]]; then
    cp -f "$cand" "$OUT_DIR/tray/"
    echo "Bundled tray: $(basename "$cand")"
    break
  fi
done

cat >"$OUT_DIR/README.txt" <<EOF
EyeNet Platform — Ubuntu installer (${VERSION})

Requirements
- Ubuntu 24.04 amd64 (or compatible)
- At least 16 GB RAM
- Internet access to pull images from ghcr.io
- A sudo-capable user

Install

1. Unzip this folder (e.g. ~/Downloads/${NAME}).
2. Open a terminal in that folder and run:
     bash install-eyenet-ubuntu.sh
   Optional: pin the LAN IP phones should use:
     ADVERTISE_HOST=192.168.x.y bash install-eyenet-ubuntu.sh
3. When Docker group membership is new, log out/in (or run: newgrp docker).
4. Open http://localhost:3000 and complete /bootstrap with your approved
   owner email and lic_… application key from Authority.

EyeNet tray
- Desktop AppIndicator (Start / Stop / Restart / Open UI) when the linux
  tray archive is included or available from GitHub Releases.

Support
- User guide: https://wiki.eyenet-vision.com/owners-admins/
EOF

chmod +x "$OUT_DIR/install-eyenet-ubuntu.sh" \
  "$OUT_DIR/install-discovery-reregister-timer.sh" \
  "$OUT_DIR/ensure-media-volume-perms.sh" \
  "$OUT_DIR/reregister-discovery-services.sh" \
  "$OUT_DIR/schema/apply.sh" \
  "$OUT_DIR/schema/verify.sh" \
  "$OUT_DIR/install-autostart-ubuntu.sh"

rm -f "$ZIP_PATH"
(
  cd "$(dirname "$OUT_DIR")"
  zip -ry "$(basename "$ZIP_PATH")" "$(basename "$OUT_DIR")"
)
(
  cd "$(dirname "$ZIP_PATH")"
  shasum -a 256 "$(basename "$ZIP_PATH")" | awk '{print $1 "  " $2}' > "$(basename "$ZIP_PATH").sha256"
)

echo "Packed $ZIP_PATH"
cat "${ZIP_PATH}.sha256"
