#!/usr/bin/env bash
# Ensure compose volume media_data is writable by Media (uid/gid 1001).
# Belt-and-suspenders for installs that still run an older Media image
# without the docker-entrypoint chown. Safe to re-run.
set -euo pipefail

PROJECT="${COMPOSE_PROJECT_NAME:-pplmeta}"
VOL="${MEDIA_VOLUME_NAME:-${PROJECT}_media_data}"

docker_() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

if ! docker_ volume inspect "$VOL" >/dev/null 2>&1; then
  echo "WARN: volume $VOL not found — skip media perms (stack not up yet?)"
  exit 0
fi

echo "==> Ensuring $VOL owned by 1001:1001 (Media app user)..."
docker_ run --rm -v "${VOL}:/data" alpine:3.20 \
  sh -c 'chown -R 1001:1001 /data && chmod -R u+rwX /data && ls -lad /data'
echo "OK: $VOL writable by Media (uid 1001)"
