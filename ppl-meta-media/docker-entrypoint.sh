#!/bin/sh
# Ensure the media volume is writable by uid 1001 (app), then drop privileges.
# Fresh Docker named volumes are root:root; Media runs as non-root USER app.
set -eu

MEDIA_ROOT="${STORAGE_PATH:-/app/media}"

mkdir -p "$MEDIA_ROOT" /logs /tmp/ppl-meta-media-android-compat

if [ "$(id -u)" = "0" ]; then
  chown -R app:app "$MEDIA_ROOT" /logs /tmp/ppl-meta-media-android-compat
  # Drop to app before starting uvicorn (setpriv is util-linux on Debian slim).
  if command -v setpriv >/dev/null 2>&1; then
    exec setpriv --reuid=1001 --regid=1001 --init-groups -- "$@"
  fi
  if command -v runuser >/dev/null 2>&1; then
    exec runuser -u app -- "$@"
  fi
  echo "ERROR: cannot drop privileges (need setpriv or runuser)" >&2
  exit 1
fi

exec "$@"
