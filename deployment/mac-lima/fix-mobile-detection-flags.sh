#!/usr/bin/env bash
# Apply mobile detection follow-up fixes on the running Lima stack:
# 1) Enable auto_face_detection for MOBILE cameras in DB
# 2) Patch cameras register defaults into the cameras container
# 3) Patch vision session_manager datetime awareness into the vision container
set -euo pipefail

cd "${HOME}/eyenet-platform"
REPO="/Users/nickgklezakos/Documents/ppl-meta-code"

CAM_CID="$(docker compose -f docker-compose.yml -p pplmeta ps -aq ppl-meta-cameras)"
VIS_CID="$(docker compose -f docker-compose.yml -p pplmeta ps -aq ppl-meta-vision)"

echo "=== DB: enable face detection for MOBILE + RTSP cameras ==="
docker compose -f docker-compose.yml -p pplmeta exec -T postgres psql -U pplmeta -d ppl_db -v ON_ERROR_STOP=1 <<'SQL'
UPDATE cameras
SET auto_face_detection = TRUE,
    instant_detection_enabled = TRUE,
    processing_options = CASE
      WHEN processing_options IS NULL OR processing_options::text IN ('null', '{}', '')
        THEN '{"auto_body_detection": true}'::json
      ELSE (
        SELECT json_object_agg(key, value)
        FROM (
          SELECT * FROM json_each(COALESCE(processing_options, '{}'::json))
          UNION ALL
          SELECT * FROM json_each('{"auto_body_detection": true}'::json)
        ) merged
      )
    END,
    updated_at = NOW()
WHERE upper(camera_type::text) LIKE '%MOBILE%'
   OR upper(camera_type::text) LIKE '%RTSP%';

SELECT device_id, name, camera_type, auto_face_detection, instant_detection_enabled, processing_options
FROM cameras
WHERE upper(camera_type::text) LIKE '%MOBILE%'
   OR upper(camera_type::text) LIKE '%RTSP%'
ORDER BY id DESC;
SQL

echo "=== Patch cameras register defaults ==="
docker cp "$REPO/ppl-meta-cameras/src/api/v1/endpoints/cameras.py" \
  "$CAM_CID":/app/src/api/v1/endpoints/cameras.py

echo "=== Patch vision session_manager (_ensure_aware) ==="
docker cp "$REPO/ppl-meta-vision/src/session_manager.py" \
  "$VIS_CID":/app/src/session_manager.py

echo "=== Restart vision (pick up session_manager) ==="
docker restart "$VIS_CID"
# cameras endpoint is imported at startup — restart to load register defaults
docker restart "$CAM_CID"

echo "waiting for healthy..."
for i in $(seq 1 40); do
  cs="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CAM_CID")"
  vs="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$VIS_CID")"
  echo "  $i cameras=$cs vision=$vs"
  [[ "$cs" == "healthy" && "$vs" == "healthy" ]] && break
  sleep 2
done

docker compose -f docker-compose.yml -p pplmeta exec -T ppl-meta-vision \
  grep -n "_ensure_aware" /app/src/session_manager.py | head -5

echo "=== re-register discovery (cameras/vision may have dropped) ==="
bash "$REPO/deployment/mac-lima/reregister-discovery-services.sh"

echo "DONE"
