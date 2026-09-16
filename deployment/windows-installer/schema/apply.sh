#!/usr/bin/env bash
# Windows/Lima installer entrypoint — always applies the vendored schema pack.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SCHEMA_PACK_DIR="${SCHEMA_PACK_DIR:-$HERE/pack}"
export REQUIRE_VERIFY="${REQUIRE_VERIFY:-1}"

# Prefer sibling verify; fall back to mac-lima copy if present in monorepo.
if [[ -f "$HERE/verify.sh" ]]; then
  :
elif [[ -f "$HERE/../../mac-lima/verify-codebase-schema.sh" ]]; then
  cp -f "$HERE/../../mac-lima/verify-codebase-schema.sh" "$HERE/verify.sh"
fi

# Apply via mac-lima script when in monorepo; else local apply-from-pack.
APPLY_MAC="$HERE/../../mac-lima/apply-codebase-schema.sh"
if [[ -f "$APPLY_MAC" ]]; then
  bash "$APPLY_MAC"
else
  # Standalone installer: apply pack SQL only + verify
  POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ppl-postgres}"
  if [[ -f ./.env ]]; then set -a; . ./.env; set +a; fi
  if [[ -f ./.env.windows ]]; then set -a; . ./.env.windows; set +a; fi
  POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
  POSTGRES_DB="${POSTGRES_DB:-ppl_db}"
  docker_() {
    if docker info >/dev/null 2>&1; then docker "$@"; else sg docker -c "docker $(printf '%q ' "$@")"; fi
  }
  echo "=== Standalone schema pack apply ($SCHEMA_PACK_DIR) ==="
  while IFS= read -r -d '' f; do
    echo "  -> $(basename "$f")"
    docker_ exec -i "$POSTGRES_CONTAINER" \
      psql -v ON_ERROR_STOP=0 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$f" >/dev/null 2>&1 || true
  done < <(find "$SCHEMA_PACK_DIR" -maxdepth 1 -name '*.sql' -print0 | sort -z)
  bash "$HERE/verify.sh"
fi
