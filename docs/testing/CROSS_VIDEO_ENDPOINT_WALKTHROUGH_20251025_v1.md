# Endpoint-only cross-video tracking walkthrough (usb_camera_0)

Date: 2025-10-25
Version: v1.0

This document is a step-by-step, copy-pasteable terminal checklist for running the "endpoint-only" cross-video tracking test for the two target videos in collection `usb_camera_0`. Run each command interactively from your shell (zsh). If a step fails, copy the output here and I'll debug the failing step.

Prerequisites
- Repo root: `/Users/nickgklezakos/Documents/ppl-meta-code`
- Services running locally (best started via workspace tasks): Node (8001), Media (8000), Gateway (8080), vmeta (8008), etc.
- Canonical credentials (use exactly this login command every time):
  - username: `fresh.user@example.com`
  - password: `NewPassword234!`

Important local paths used by these scripts
- vmeta uvicorn logs: `/tmp/vmeta_uvicorn.log`
- test run log (when captured): `/tmp/comprehensive_test_run.log`
- gateway manual responses: `/tmp/gateway_naive.json` and `/tmp/gateway_z.json`

---

## 1) Obtain an access token (canonical)

Why: Authenticate and get a JWT for subsequent calls.

Commands:

```bash
curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))"

# Extract token into shell variable
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

echo "TOKEN_LEN=${#TOKEN}"
```

Expected: JSON response containing `access_token` and `token_type: bearer`. `TOKEN_LEN` should be > 0.

---

## 2) Confirm Gateway authenticated search returns the two target videos

Why: Verify the Gateway returns the expected media items with the token the same way vmeta should.

Parameters (the timeframe vmeta will use):
- collection: `usb_camera_0`
- start_time: `2025-10-19T13:08:00Z`
- end_time: `2025-10-19T13:11:00Z`

Commands:

```bash
# naive (no explicit Z)
curl -s -H "Authorization: Bearer $TOKEN" \
 "http://localhost:8080/api/v1/media/search?collection=usb_camera_0&start_time=2025-10-19T13:08:00&end_time=2025-10-19T13:11:00" \
 | python3 -m json.tool > /tmp/gateway_naive.json

# Z-suffixed (explicit UTC)
curl -s -H "Authorization: Bearer $TOKEN" \
 "http://localhost:8080/api/v1/media/search?collection=usb_camera_0&start_time=2025-10-19T13:08:00Z&end_time=2025-10-19T13:11:00Z" \
 | python3 -m json.tool > /tmp/gateway_z.json

# Quick counts
python3 - <<'PY'
import json
for p,label in [('/tmp/gateway_naive.json','naive'),('/tmp/gateway_z.json','z')]:
    try:
        d=json.load(open(p))
    except Exception as e:
        print(label, 'failed to parse:', e)
        continue
    items = d.get('items') or d.get('media') or (d if isinstance(d,list) else [])
    print(label, 'count=', len(items))
    print(label, 'sample ids=', [ (i.get('uuid') or i.get('id')) for i in items[:5] ])
PY
```

Expected: Both queries return items and include these target UUIDs:
- `7b462847-cd1f-441a-8bd9-aaed6643b7cb`
- `38f80c41-e0af-41fc-882d-f7ff79abd43d`

---

## 3) Create a cross-video tracking session via vmeta API (endpoint-only)

Why: Triggers vmeta background processing.

Prepare request:

```bash
cat > /tmp/create_session.json <<'JSON'
{
  "collections":["usb_camera_0"],
  "start_time":"2025-10-19T13:08:00Z",
  "end_time":"2025-10-19T13:11:00Z",
  "algorithm_config": {
    "max_gap_seconds": 10,
    "iou_threshold": 0.3,
    "min_overlap_confidence": 0.5
  },
  "background_processing": true
}
JSON

curl -s -X POST 'http://localhost:8008/individuals/tracking/sessions' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d @/tmp/create_session.json \
  | python3 -m json.tool
```

Expected: Response with `session_uuid` and status `initialized`. Save the `session_uuid` for polling.

---

## 4) Poll session status until completed (endpoint-only)

Why: Verify background processing result.

Replace `<SESSION_UUID>` with the `session_uuid` from the previous step.

```bash
SESSION_UUID=<paste_session_uuid_here>
for i in {1..12}; do
  echo "poll $i"
  curl -s "http://localhost:8008/individuals/tracking/sessions/$SESSION_UUID" | python3 -m json.tool
  sleep 1
done
```

Expected successful run: status transitions initialized -> running -> completed and final values show
- `total_videos` >= 2 (ideally 2)
- `processed_videos` > 0
- `individuals_found` >= 1

If `total_videos == 0`, continue with Step 5.

---

## 5) Inspect DB debug buffer when discovery found 0 videos

Why: We append short debug strings to `tracking_sessions.failed_videos` to record what discovery observed.

```bash
export PGPASSWORD=ppl_password
psql -h localhost -U ppl_user -d ppl_meta -c "SELECT session_uuid, failed_videos FROM tracking_sessions WHERE session_uuid = '$SESSION_UUID';"
```

What to look for in `failed_videos` (array of short markers):
- `create_auth_preview: present=...` — whether API received Authorization header at session creation
- `discover_start: auth_present=..., start=..., end=..., collections=...` — exactly what vmeta used for discovery
- `gateway_debug: status=..., items=..., auth_present=..., sample=[...]` — gateway call outcome (if written)
- `discovery_debug: found=<n>, sample=[...]` — final discovery summary we always write

Interpretation examples:
- If `create_auth_preview` is `present=True` and `discover_start` shows `auth_present=True`, the API forwarded auth into the background task.
- If `gateway_debug` is missing or shows `items=0`, the vmeta->gateway call either returned zero or failed; check vmeta and gateway logs.

---

## 6) Inspect vmeta logs (if DB entries are insufficient)

Why: See runtime logs from the discovery path and any error traces.

```bash
# Show last 400 lines
tail -n 400 /tmp/vmeta_uvicorn.log

# Follow live while you re-run the session creation
tail -F /tmp/vmeta_uvicorn.log
```

Look for lines containing:
- `Querying Gateway media search`
- `Gateway search -> status=`
- `Gateway returned` or `gateway_debug` ORM write traces
- Any `ERROR`/tracebacks that mention discovery or session UUID

Notes: If `uvicorn` was run with `--reload`, the reloader spawns child processes — prefer starting vmeta without `--reload` when capturing logs for debugging.

---

## 7) Inspect Gateway logs (if vmeta appears to call gateway)

Why: Confirm whether Gateway received the request and its response code.

If nginx is used locally, check:

```bash
sudo tail -n 200 /var/log/nginx/access.log
sudo tail -n 200 /var/log/nginx/error.log
```

Or check the Gateway uvicorn log capture (if you run it to file). Look for GET requests to `/api/v1/media/search` around the session time.

---

## 8) Manually reproduce the exact discovery call vmeta attempted

Why: If `discover_start` shows the start/end strings vmeta used, re-run that exact call from your shell using the same Authorization header to confirm parity.

Example (replace with strings from `discover_start` if different):

```bash
curl -v -H "Authorization: Bearer $TOKEN" \
 "http://localhost:8080/api/v1/media/search?collection=usb_camera_0&start_time=2025-10-19T13:08:00Z&end_time=2025-10-19T13:11:00Z" \
 -o /tmp/manual_discovery.json

python3 - <<'PY'
import json
try:
    d=json.load(open('/tmp/manual_discovery.json'))
    items=d.get('items') or d.get('media') or (d if isinstance(d,list) else [])
    print('count', len(items))
    print('sample', [ (i.get('uuid') or i.get('id')) for i in items[:10]])
except Exception as e:
    print('parse failure', e)
PY
```

If this returns items locally but `vmeta` recorded `found=0`, compare carefully:
- the exact query string (start/end formatting)
- headers (ensure `Authorization: Bearer $TOKEN` used by vmeta)
- percent-encoding or accidental quotes

---

## 9) Check `individuals` and `individual_video_appearances` tables

```bash
export PGPASSWORD=ppl_password
psql -h localhost -U ppl_user -d ppl_meta -c "SELECT COUNT(*) FROM individuals;"
psql -h localhost -U ppl_user -d ppl_meta -c "SELECT * FROM individual_video_appearances WHERE individual_uuid IS NOT NULL LIMIT 10;"
```

Expected: If cross-video tracking succeeded you should see at least 1 `individuals` row and 2 appearances.

---

## 10) Quick debugging checklist (summary)

- Not authenticated: ensure you used the canonical login to create `TOKEN` and that you pass the header exactly as `Authorization: Bearer $TOKEN` when creating the session.
- `create_auth_preview` present=False: ensure the create session request included the Authorization header.
- `discover_start` shows `auth_present=False` while `create_auth_preview` is True: indicates the background task was scheduled without receiving the header; check that `create_tracking_session` forwards the header into `background_tasks.add_task(process_tracking_session, session_uuid, auth_header)`.
- `gateway_debug` shows non-200 status: check gateway logs for why (auth rejection, missing param, other error).
- Manual query works but vmeta found none: compare start/end strings exactly and run the manual query using the exact strings logged in `discover_start`.

---

## 11) Safe restart commands (preferred: use workspace tasks)

- Stop all local Python services:
  - Use the workspace task: `🛑 Stop All Local Python Services`
- Start all local Python services:
  - Use the workspace task: `🚀 Start All Local Python Services`

---

## 12) If you want this file in the repo (already saved)
Path: `docs/testing/CROSS_VIDEO_ENDPOINT_WALKTHROUGH_20251025_v1.md`

---

If you'd like, I can now:
- Run through these commands step-by-step and capture logs for you, or
- Wait while you execute them and paste back the first failing command output so I can debug that specific step.

Which do you prefer?