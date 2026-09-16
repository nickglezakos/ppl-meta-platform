#!/usr/bin/env bash
# Apply codebase Postgres schema for EyeNet installer (Lima / Windows).
#
# Prefer the vendored pack (always matches last sync from repo):
#   deployment/windows-installer/schema/pack/
# Fall back to live monorepo paths when pack is missing and REPO_ROOT is present.
#
#   bash deployment/mac-lima/apply-codebase-schema.sh
#   SCHEMA_PACK_DIR=... bash deployment/windows-installer/schema/apply.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# mac-lima → repo root is ../..
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/eyenet-platform}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ppl-postgres}"
REQUIRE_VERIFY="${REQUIRE_VERIFY:-1}"

# Pack locations (installer first, then next to this script's sibling windows-installer)
PACK_CANDIDATES=(
  "${SCHEMA_PACK_DIR:-}"
  "$INSTALL_DIR/schema/pack"
  "$REPO_ROOT/deployment/windows-installer/schema/pack"
  "$SCRIPT_DIR/../windows-installer/schema/pack"
)

docker_() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sg docker -c "docker $(printf '%q ' "$@")"
  fi
}

if [[ -f "$INSTALL_DIR/.env" ]]; then
  set -a; # shellcheck disable=SC1090
  . "$INSTALL_DIR/.env"; set +a
elif [[ -f ./.env ]]; then
  set -a; . ./.env; set +a
elif [[ -f ./.env.windows ]]; then
  set -a; . ./.env.windows; set +a
fi

POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
POSTGRES_DB="${POSTGRES_DB:-ppl_db}"

psql_file() {
  local f="$1"
  local label
  label="$(basename "$f")"
  [[ -f "$f" ]] || { echo "  SKIP missing: $label"; return 0; }
  echo "  -> $label"
  docker_ exec -i "$POSTGRES_CONTAINER" \
    psql -v ON_ERROR_STOP=0 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$f" \
    >/tmp/eyenet-schema-apply.log 2>&1 || true
  if grep -Eiq 'ERROR:' /tmp/eyenet-schema-apply.log; then
    grep -E 'ERROR:' /tmp/eyenet-schema-apply.log | head -12 | sed 's/^/     /'
  fi
}

resolve_pack() {
  local d
  for d in "${PACK_CANDIDATES[@]}"; do
    [[ -n "$d" ]] || continue
    if [[ -d "$d" ]] && compgen -G "$d/*.sql" >/dev/null 2>&1; then
      echo "$d"
      return 0
    fi
  done
  return 1
}

echo "=== EyeNet codebase schema apply ==="
echo "repo=$REPO_ROOT db=$POSTGRES_DB container=$POSTGRES_CONTAINER"

PACK=""
if PACK="$(resolve_pack)"; then
  echo "Using schema pack: $PACK"
  # Sorted: 000_preflight first, then numbered migrations
  while IFS= read -r -d '' f; do
    psql_file "$f"
  done < <(find "$PACK" -maxdepth 1 -name '*.sql' -print0 | sort -z)
else
  echo "WARNING: schema pack missing — sync with:"
  echo "  bash $REPO_ROOT/deployment/mac-lima/sync-schema-pack.sh"
  echo "Falling back to live monorepo migration paths..."
  # Delegate to legacy ordered paths via re-invoking sync then pack, or inline.
  if [[ -x "$REPO_ROOT/deployment/mac-lima/sync-schema-pack.sh" ]]; then
    bash "$REPO_ROOT/deployment/mac-lima/sync-schema-pack.sh"
    PACK="$REPO_ROOT/deployment/windows-installer/schema/pack"
    while IFS= read -r -d '' f; do
      psql_file "$f"
    done < <(find "$PACK" -maxdepth 1 -name '*.sql' -print0 | sort -z)
  else
    echo "FATAL: no schema pack and cannot sync."
    exit 1
  fi
fi

VERIFY="$REPO_ROOT/deployment/mac-lima/verify-codebase-schema.sh"
if [[ ! -f "$VERIFY" ]]; then
  VERIFY="$SCRIPT_DIR/verify-codebase-schema.sh"
fi
if [[ ! -f "$VERIFY" ]]; then
  # Installer-bundled copy
  VERIFY="$(cd "$(dirname "$PACK")/.." && pwd)/verify.sh"
fi

if [[ "$REQUIRE_VERIFY" == "1" ]]; then
  echo
  bash "$VERIFY"
else
  echo "(REQUIRE_VERIFY=0 — skipped)"
fi
