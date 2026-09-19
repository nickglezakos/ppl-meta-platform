#!/usr/bin/env bash
# Thin wrapper — canonical script ships with the Windows/Ubuntu installer bundle.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL="$HERE/../windows-installer/reregister-discovery-services.sh"
if [[ ! -f "$CANONICAL" ]]; then
  echo "FATAL: missing $CANONICAL" >&2
  exit 1
fi
exec bash "$CANONICAL" "$@"
