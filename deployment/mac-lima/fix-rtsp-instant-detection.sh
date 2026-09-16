#!/usr/bin/env bash
# Enable instant face/body detection for RTSP cameras and hot-patch Lima
# cameras + vmeta so Celery actually runs the face path.
set -euo pipefail

REPO="${REPO:-/Users/nickgklezakos/Documents/ppl-meta-code}"
DEVICE_ID="${1:-bec5f94f-02ce-4620-9dc7-ed50d564c182}"

limactl copy "$REPO/ppl-meta-cameras/src/services/instant_detection.py" eyenet:/tmp/instant_detection.py
limactl copy "$REPO/ppl-meta-cameras/src/api/v1/endpoints/cameras.py" eyenet:/tmp/cameras_ep.py
limactl copy "$REPO/ppl-meta-vmeta/src/api/v1/instant_detection_storage.py" eyenet:/tmp/instant_detection_storage.py
limactl copy "$REPO/deployment/mac-lima/enable_rtsp_instant_flags.py" eyenet:/tmp/enable_rtsp_instant_flags.py

limactl shell eyenet -- bash -lc "
set -e
CAM=\$(sudo docker ps -qf name=ppl-meta-cameras | head -1)
VMETA=\$(sudo docker ps -qf name=ppl-meta-vmeta | head -1)
test -n \"\$CAM\" && test -n \"\$VMETA\"
sudo docker cp /tmp/instant_detection.py \"\$CAM\":/app/src/services/instant_detection.py
sudo docker cp /tmp/cameras_ep.py \"\$CAM\":/app/src/api/v1/endpoints/cameras.py
sudo docker cp /tmp/enable_rtsp_instant_flags.py \"\$CAM\":/tmp/enable_rtsp_instant_flags.py
sudo docker cp /tmp/instant_detection_storage.py \"\$VMETA\":/app/src/api/v1/instant_detection_storage.py
sudo docker exec -w /app -e DEVICE_ID=$DEVICE_ID \"\$CAM\" python3 /tmp/enable_rtsp_instant_flags.py
sudo docker restart \"\$CAM\" \"\$VMETA\"
echo waiting...
for i in \$(seq 1 40); do
  cs=\$(sudo docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \"\$CAM\")
  vs=\$(sudo docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \"\$VMETA\")
  echo \"  \$i cameras=\$cs vmeta=\$vs\"
  [[ \"\$cs\" == healthy && \"\$vs\" == healthy ]] && break
  sleep 2
done
sudo docker exec \"\$CAM\" grep -n '_camera_instant_face_enabled\|auto_face or instant' /app/src/services/instant_detection.py | head -8
sudo docker exec \"\$VMETA\" grep -n 'complete-session\|get_current_user_or_internal' /app/src/api/v1/instant_detection_storage.py | head -10
echo DONE
"
