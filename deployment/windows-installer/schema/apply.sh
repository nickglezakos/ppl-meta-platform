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
  # Windows Notepad / PowerShell often write CRLF; bash cannot source that.
  [[ -f ./.env ]] && sed -i 's/\r$//' ./.env || true
  [[ -f ./.env.windows ]] && sed -i 's/\r$//' ./.env.windows || true
  if [[ -f ./.env ]]; then set -a; # shellcheck disable=SC1091
    . ./.env; set +a; fi
  if [[ -f ./.env.windows ]]; then set -a; # shellcheck disable=SC1091
    . ./.env.windows; set +a; fi
  POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
  POSTGRES_DB="${POSTGRES_DB:-ppl_db}"
  docker_() {
    if docker info >/dev/null 2>&1; then docker "$@"; else sg docker -c "docker $(printf '%q ' "$@")"; fi
  }

  # Pack migrations expect app-created base tables (face_detections, individuals).
  # Wait while the stack is up; skip wait if APPLY_WAIT_APP_TABLES=0.
  if [[ "${APPLY_WAIT_APP_TABLES:-1}" != "0" ]]; then
    echo "Waiting for app base tables face_detections + individuals (up to 240s)..."
    ready=0
    for _ in $(seq 1 120); do
      got=$(docker_ exec "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('face_detections','individuals')" \
        2>/dev/null | tr -d '[:space:]' || echo 0)
      if [[ "$got" == "2" ]]; then
        ready=1
        break
      fi
      sleep 2
    done
    if [[ "$ready" != 1 ]]; then
      echo "WARN: app base tables incomplete (need face_detections + individuals) — pack may fail" >&2
    else
      echo "OK: face_detections + individuals present"
    fi
  fi

  # App ORM sometimes creates a wrong-shaped schema_migrations; pack needs version/description/checksum.
  docker_ exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='public' AND table_name='schema_migrations'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='schema_migrations' AND column_name='description'
  ) THEN
    RAISE NOTICE 'Dropping app-shaped schema_migrations (missing description)';
    DROP TABLE schema_migrations CASCADE;
  END IF;
END $$;
SQL

  apply_pack_pass() {
    local stop_on_error="$1"  # 0 or 1
    local label="$2"
    echo "=== Standalone schema pack apply ($label, ON_ERROR_STOP=$stop_on_error) ($SCHEMA_PACK_DIR) ==="
    while IFS= read -r -d '' f; do
      base="$(basename "$f")"
      case "$base" in ._*) continue ;; esac
      echo "  -> $base"
      if ! docker_ exec -i "$POSTGRES_CONTAINER" \
        psql -v "ON_ERROR_STOP=$stop_on_error" -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$f" >/dev/null; then
        if [[ "$stop_on_error" == "1" ]]; then
          echo "ERROR: schema file failed: $base" >&2
          return 1
        fi
        echo "  WARN: $base had SQL errors (continuing soft pass)" >&2
      fi
    done < <(find "$SCHEMA_PACK_DIR" -maxdepth 1 -name '*.sql' ! -name '._*' -print0 | sort -z)
    return 0
  }

  # Pack file order is not a pure DAG (e.g. 007 mvr_people FK → individuals from 009).
  # Two soft passes: first creates individuals/tracking; second creates mvr_people + dependents.
  # verify.sh is the hard gate for Stage 3.
  apply_pack_pass 0 "pass-1"
  apply_pack_pass 0 "pass-2"
  bash "$HERE/verify.sh"
fi
