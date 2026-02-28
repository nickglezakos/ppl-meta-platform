#!/usr/bin/env bash
set -euo pipefail

NODE_URL="${NODE_URL:-http://localhost:8001}"
MEDIA_URL="${MEDIA_URL:-http://localhost:8000}"
VMETA_URL="${VMETA_URL:-http://localhost:8008}"
EMAIL="${EMAIL:-fresh.user@example.com}"
PASSWORD="${PASSWORD:-NewPassword234!}"
GROUP_ID="${GROUP_ID:-}"
CAMERA_ID="${CAMERA_ID:-}"
CANDIDATE_UUID="${CANDIDATE_UUID:-}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-30}"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

ARTIFACT_DIR="/tmp/ppl-match-acceptance-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARTIFACT_DIR"

TRIGGER_UUID=""

cleanup() {
  if [[ -n "$TRIGGER_UUID" ]]; then
    curl -sS -o /dev/null -X DELETE "$MEDIA_URL/api/v1/triggers/$TRIGGER_UUID" || true
  fi
}
trap cleanup EXIT

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --email <value>            Login email (default: $EMAIL)
  --password <value>         Login password
  --node-url <value>         Node URL (default: $NODE_URL)
  --media-url <value>        Media URL (default: $MEDIA_URL)
  --vmeta-url <value>        vmeta URL (default: $VMETA_URL)
  --group-id <value>         Existing individual group id (auto-discover if omitted)
  --camera-id <value>        Camera device id (auto-discover if omitted)
  --candidate-uuid <value>   Source MVR UUID for positive-path attempt
  --cooldown-seconds <value> Trigger cooldown for test trigger (default: $COOLDOWN_SECONDS)
  --help                     Show this help

Env vars are also supported: EMAIL PASSWORD NODE_URL MEDIA_URL VMETA_URL GROUP_ID CAMERA_ID CANDIDATE_UUID COOLDOWN_SECONDS
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --email) EMAIL="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --node-url) NODE_URL="$2"; shift 2 ;;
    --media-url) MEDIA_URL="$2"; shift 2 ;;
    --vmeta-url) VMETA_URL="$2"; shift 2 ;;
    --group-id) GROUP_ID="$2"; shift 2 ;;
    --camera-id) CAMERA_ID="$2"; shift 2 ;;
    --candidate-uuid) CANDIDATE_UUID="$2"; shift 2 ;;
    --cooldown-seconds) COOLDOWN_SECONDS="$2"; shift 2 ;;
    --help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

need_cmd curl
need_cmd jq

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "✅ PASS: $1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "❌ FAIL: $1"
}

skip() {
  SKIP_COUNT=$((SKIP_COUNT + 1))
  echo "⏭️  SKIP: $1"
}

echo "Artifacts: $ARTIFACT_DIR"

echo
echo "[1] Login"
LOGIN_JSON="$ARTIFACT_DIR/login.json"
curl -sS -X POST "$NODE_URL/api/v1/users/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=$EMAIL&password=$PASSWORD" > "$LOGIN_JSON"
TOKEN=$(jq -r '.access_token // empty' "$LOGIN_JSON")
if [[ -n "$TOKEN" ]]; then
  pass "Auth token acquired"
else
  fail "Auth token not returned"
  echo "Login response:"; cat "$LOGIN_JSON" | jq .
  exit 1
fi

echo
echo "[2] Resolve group"
if [[ -z "$GROUP_ID" ]]; then
  GROUPS_JSON="$ARTIFACT_DIR/groups.json"
  curl -sS "$VMETA_URL/api/v1/individual-groups?skip=0&limit=10" \
    -H "Authorization: Bearer $TOKEN" > "$GROUPS_JSON"
  GROUP_ID=$(jq -r '.groups[0].id // empty' "$GROUPS_JSON")
fi
if [[ -n "$GROUP_ID" ]]; then
  pass "Using group_id=$GROUP_ID"
else
  fail "No group found/provided"
  exit 1
fi

echo
echo "[3] Resolve camera"
if [[ -z "$CAMERA_ID" ]]; then
  LIST_TRIGGERS_JSON="$ARTIFACT_DIR/list_triggers.json"
  curl -sS "$MEDIA_URL/api/v1/triggers?page=1&page_size=1" > "$LIST_TRIGGERS_JSON"
  CAMERA_ID=$(jq -r '.triggers[0].camera_device_id // empty' "$LIST_TRIGGERS_JSON")
fi
if [[ -z "$CAMERA_ID" ]]; then
  CAMERA_ID="edge-camera-001"
fi
pass "Using camera_id=$CAMERA_ID"

echo
echo "[4] Create valid ppl_match trigger"
CREATE_PAYLOAD=$(jq -n \
  --arg name "acceptance-ppl-match-$(date +%s)" \
  --arg cam "$CAMERA_ID" \
  --arg gid "$GROUP_ID" \
  --argjson cooldown "$COOLDOWN_SECONDS" \
  '{
    name: $name,
    description: "Acceptance test trigger",
    trigger_mode: "ppl_match",
    demographic_conditions: [],
    time_span: "any",
    camera_device_id: $cam,
    camera_name: $cam,
    tracking_duration: "10 minutes",
    cooldown_seconds: $cooldown,
    is_active: true,
    ppl_match_group_id: $gid,
    ppl_match_similarity_threshold: 0.75,
    ppl_match_top_k: 1
  }')
CREATE_JSON="$ARTIFACT_DIR/create_trigger.json"
curl -sS -X POST "$MEDIA_URL/api/v1/triggers" \
  -H 'Content-Type: application/json' \
  -d "$CREATE_PAYLOAD" > "$CREATE_JSON"
TRIGGER_UUID=$(jq -r '.uuid // empty' "$CREATE_JSON")
if [[ -n "$TRIGGER_UUID" ]]; then
  pass "Created trigger uuid=$TRIGGER_UUID"
else
  fail "Create trigger failed"
  cat "$CREATE_JSON" | jq .
  if grep -q "column \"trigger_mode\"" "$CREATE_JSON"; then
    echo "Hint: run media migration for ppl-match fields before testing."
  fi
  exit 1
fi

echo
echo "[5] Validate required ppl_match_group_id"
INVALID_PAYLOAD=$(jq -n --arg cam "$CAMERA_ID" '{
  name:"invalid-no-group",
  trigger_mode:"ppl_match",
  demographic_conditions:[],
  time_span:"any",
  camera_device_id:$cam,
  camera_name:$cam,
  tracking_duration:"10 minutes",
  cooldown_seconds:30,
  is_active:true,
  ppl_match_similarity_threshold:0.75,
  ppl_match_top_k:1
}')
INVALID_JSON="$ARTIFACT_DIR/invalid_create.json"
INVALID_STATUS=$(curl -sS -o "$INVALID_JSON" -w '%{http_code}' -X POST "$MEDIA_URL/api/v1/triggers" \
  -H 'Content-Type: application/json' -d "$INVALID_PAYLOAD")
if [[ "$INVALID_STATUS" == "422" ]]; then
  pass "Invalid create rejected with 422"
else
  fail "Invalid create returned HTTP $INVALID_STATUS (expected 422)"
fi

echo
echo "[6] Update trigger ppl_match fields"
UPDATE_JSON="$ARTIFACT_DIR/update_trigger.json"
curl -sS -X PUT "$MEDIA_URL/api/v1/triggers/$TRIGGER_UUID" \
  -H 'Content-Type: application/json' \
  -d '{"ppl_match_similarity_threshold":0.80,"ppl_match_top_k":2}' > "$UPDATE_JSON"
THRESHOLD=$(jq -r '.ppl_match_similarity_threshold // empty' "$UPDATE_JSON")
TOPK=$(jq -r '.ppl_match_top_k // empty' "$UPDATE_JSON")
if [[ "$THRESHOLD" == "0.8" && "$TOPK" == "2" ]]; then
  pass "Update persisted threshold/top_k"
else
  fail "Update did not persist expected fields"
fi

echo
echo "[7] Evaluate missing source MVR UUIDs (expect non-fire)"
EVAL1_JSON="$ARTIFACT_DIR/eval_missing_source.json"
EVAL1_PAYLOAD=$(jq -n --arg cam "$CAMERA_ID" --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" '{
  camera_id:$cam,
  timestamp:$ts,
  people_count:1,
  demographics:{percent_male:50,percent_female:50},
  metadata:{}
}')
curl -sS -X POST "$MEDIA_URL/api/v1/triggers/instant-detection" \
  -H 'Content-Type: application/json' \
  -d "$EVAL1_PAYLOAD" > "$EVAL1_JSON"
EVAL1_REASON=$(jq -r --arg t "$TRIGGER_UUID" '.results[]?|select(.trigger_uuid==$t)|.reason // empty' "$EVAL1_JSON")
if [[ "$EVAL1_REASON" == *"No source MVR UUIDs"* ]]; then
  pass "Missing-source path returns expected reason"
else
  fail "Missing-source reason unexpected: ${EVAL1_REASON:-<empty>}"
fi

echo
echo "[8] Evaluate with source MVR UUID"
if [[ -z "$CANDIDATE_UUID" ]]; then
  MEMBERS_JSON="$ARTIFACT_DIR/group_members.json"
  curl -sS "$VMETA_URL/api/v1/individual-groups/$GROUP_ID/members?skip=0&limit=1" \
    -H "Authorization: Bearer $TOKEN" > "$MEMBERS_JSON"
  CANDIDATE_UUID=$(jq -r '.members[0].id // empty' "$MEMBERS_JSON")
fi

if [[ -z "$CANDIDATE_UUID" ]]; then
  skip "No candidate UUID available for source evaluation"
else
  EVAL2_JSON="$ARTIFACT_DIR/eval_with_source_1.json"
  EVAL2_PAYLOAD=$(jq -n --arg cam "$CAMERA_ID" --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" --arg cand "$CANDIDATE_UUID" '{
    camera_id:$cam,
    timestamp:$ts,
    people_count:1,
    demographics:{percent_male:50,percent_female:50},
    metadata:{source_mvr_uuids:[$cand]}
  }')
  curl -sS -X POST "$MEDIA_URL/api/v1/triggers/instant-detection" \
    -H 'Content-Type: application/json' \
    -d "$EVAL2_PAYLOAD" > "$EVAL2_JSON"

  EVAL2_PASSED=$(jq -r --arg t "$TRIGGER_UUID" '.results[]?|select(.trigger_uuid==$t)|.passed // false' "$EVAL2_JSON")
  EVAL2_REASON=$(jq -r --arg t "$TRIGGER_UUID" '.results[]?|select(.trigger_uuid==$t)|.reason // empty' "$EVAL2_JSON")

  if [[ "$EVAL2_PASSED" == "true" ]]; then
    pass "Source evaluation fired trigger"

    EVAL3_JSON="$ARTIFACT_DIR/eval_with_source_2.json"
    curl -sS -X POST "$MEDIA_URL/api/v1/triggers/instant-detection" \
      -H 'Content-Type: application/json' \
      -d "$EVAL2_PAYLOAD" > "$EVAL3_JSON"
    EVAL3_REASON=$(jq -r --arg t "$TRIGGER_UUID" '.results[]?|select(.trigger_uuid==$t)|.reason // empty' "$EVAL3_JSON")
    if [[ "$EVAL3_REASON" == *"Cooldown active"* ]]; then
      pass "Cooldown suppresses immediate re-fire"
    else
      fail "Cooldown check failed or unexpected reason: ${EVAL3_REASON:-<empty>}"
    fi
  else
    if [[ "$EVAL2_REASON" == *"No group matches above threshold"* ]]; then
      pass "Source evaluation non-fire reason is valid (no match)"
      skip "Cooldown test not run because trigger did not fire"
    else
      fail "Source evaluation returned unexpected reason: ${EVAL2_REASON:-<empty>}"
    fi
  fi
fi

echo
echo "[9] Fetch trigger state"
GET_JSON="$ARTIFACT_DIR/get_trigger.json"
curl -sS "$MEDIA_URL/api/v1/triggers/$TRIGGER_UUID" > "$GET_JSON"
MODE=$(jq -r '.trigger_mode // empty' "$GET_JSON")
GROUP=$(jq -r '.ppl_match_group_id // empty' "$GET_JSON")
if [[ "$MODE" == "ppl_match" && "$GROUP" == "$GROUP_ID" ]]; then
  pass "Trigger state reflects ppl_match config"
else
  fail "Trigger state mismatch"
fi

echo
echo "[10] Cleanup"
DELETE_STATUS=$(curl -sS -o "$ARTIFACT_DIR/delete_trigger.json" -w '%{http_code}' -X DELETE "$MEDIA_URL/api/v1/triggers/$TRIGGER_UUID")
TRIGGER_UUID=""
if [[ "$DELETE_STATUS" == "204" ]]; then
  pass "Cleanup delete succeeded"
else
  fail "Cleanup delete returned HTTP $DELETE_STATUS"
fi

echo
echo "================ Acceptance Summary ================"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Skipped: $SKIP_COUNT"
echo "Artifacts: $ARTIFACT_DIR"
echo "===================================================="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi
