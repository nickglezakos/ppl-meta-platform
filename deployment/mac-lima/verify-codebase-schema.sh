#!/usr/bin/env bash
# Verify installer/Lima Postgres matches codebase schema invariants.
# Exit 0 = OK, exit 1 = mismatch.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/Users/nickgklezakos/Documents/ppl-meta-code}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/eyenet-platform}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ppl-postgres}"

docker_() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sg docker -c "docker $(printf '%q ' "$@")"
  fi
}

if [[ -f "$INSTALL_DIR/.env" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$INSTALL_DIR/.env"; set +a
elif [[ -f ./.env ]]; then
  set -a; . ./.env; set +a
elif [[ -f ./.env.windows ]]; then
  set -a; . ./.env.windows; set +a
fi

POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
POSTGRES_DB="${POSTGRES_DB:-ppl_db}"

fail=0
check() {
  local name="$1"
  local sql="$2"
  local expect="$3"
  local got
  got="$(docker_ exec -i "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$sql" 2>/dev/null | tr -d '\r' | head -1)"
  if [[ "$got" == "$expect" ]]; then
    echo "OK  $name = $got"
  else
    echo "FAIL $name: got='$got' expected='$expect'"
    fail=1
  fi
}

echo "=== verify codebase schema ($POSTGRES_DB @ $POSTGRES_CONTAINER) ==="

check "ext.vector" \
  "SELECT COUNT(*) FROM pg_extension WHERE extname='vector'" "1"
check "ext.uuid-ossp" \
  "SELECT COUNT(*) FROM pg_extension WHERE extname='uuid-ossp'" "1"
check "mvr_people.face_embedding udt" \
  "SELECT udt_name FROM information_schema.columns WHERE table_name='mvr_people' AND column_name='face_embedding'" \
  "vector"
check "face_detections.session_uuid" \
  "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='face_detections' AND column_name='session_uuid'" \
  "1"
check "individuals.gender_estimate" \
  "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='individuals' AND column_name='gender_estimate'" \
  "1"
check "individuals.created_by_session" \
  "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='individuals' AND column_name='created_by_session'" \
  "1"
check "person_objects.representative_faces" \
  "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='person_objects' AND column_name='representative_faces'" \
  "1"
check "table.tracking_sessions" \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='tracking_sessions'" \
  "1"
check "table.mvr_people" \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='mvr_people'" \
  "1"
check "table.face_detection_sessions" \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='face_detection_sessions'" \
  "1"
check "table.session_individuals" \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='session_individuals'" \
  "1"

if [[ "$fail" -ne 0 ]]; then
  echo
  echo "Schema does NOT match codebase invariants."
  exit 1
fi
echo
echo "Schema matches codebase invariants."
exit 0
