#!/usr/bin/env bash
# Hot-patch Lima: instant Celery timeouts, VMeta URL for MVR, mobile letterbox.
set -euo pipefail
REPO="${REPO:-$HOME/Documents/ppl-meta-code}"

limactl copy "$REPO/ppl-meta-cameras/src/services/instant_detection.py" eyenet:/tmp/instant_detection.py
limactl copy "$REPO/ppl-meta-cameras/src/tasks/instant_detection_tasks.py" eyenet:/tmp/instant_detection_tasks.py
limactl copy "$REPO/ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py" eyenet:/tmp/instant_detection_ep.py
limactl copy "$REPO/ppl-meta-cameras/src/services/camera_detection.py" eyenet:/tmp/camera_detection.py
limactl copy "$REPO/ppl-meta-orchestrator/src/face_detection_endpoints.py" eyenet:/tmp/face_detection_endpoints.py

limactl shell eyenet -- bash -lc '
set -e
CAM=pplmeta-ppl-meta-cameras-1
ORCH=pplmeta-ppl-meta-orchestrator-1
sudo docker cp /tmp/instant_detection.py "$CAM:/app/src/services/instant_detection.py"
sudo docker cp /tmp/instant_detection_tasks.py "$CAM:/app/src/tasks/instant_detection_tasks.py"
sudo docker cp /tmp/instant_detection_ep.py "$CAM:/app/src/api/v1/endpoints/instant_detection.py"
sudo docker cp /tmp/camera_detection.py "$CAM:/app/src/services/camera_detection.py"
sudo docker cp /tmp/face_detection_endpoints.py "$ORCH:/app/face_detection_endpoints.py"
sudo docker restart "$CAM" "$ORCH"
sleep 10
echo ===verify===
sudo docker exec "$ORCH" grep -n "ppl-meta-vmeta:8008\|serving_pipeline=" /app/face_detection_endpoints.py | head -15
sudo docker exec "$CAM" grep -n "soft_time_limit=75\|_letterbox_resize\|VMETA_AGE_GENDER_TIMEOUT\", \"4\"" \
  /app/src/tasks/instant_detection_tasks.py \
  /app/src/services/camera_detection.py \
  /app/src/services/instant_detection.py | head -20
sudo docker ps --filter name=pplmeta --format "{{.Names}} {{.Status}}" | grep -E "cameras|orchestrator"
'
