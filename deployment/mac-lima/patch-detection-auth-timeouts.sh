#!/usr/bin/env bash
# Hot-patch running eyenet Lima stack: VMeta age/gender timeouts + enhanced-v2
# internal-token auth + Vision SessionStatusResponse / JWT sub fallback.
set -euo pipefail

REPO="${REPO:-$HOME/Documents/ppl-meta-code}"
CAM=pplmeta-ppl-meta-cameras-1
VIS=pplmeta-ppl-meta-vision-1

limactl copy "$REPO/ppl-meta-cameras/src/services/instant_detection.py" eyenet:/tmp/instant_detection.py
limactl copy "$REPO/ppl-meta-cameras/src/services/camera_detection.py" eyenet:/tmp/camera_detection.py
limactl copy "$REPO/ppl-meta-cameras/src/services/camera_worker.py" eyenet:/tmp/camera_worker.py
limactl copy "$REPO/ppl-meta-vision/src/main.py" eyenet:/tmp/vision_main.py
limactl copy "$REPO/ppl-meta-vision/src/session_manager.py" eyenet:/tmp/vision_session_manager.py

limactl shell eyenet -- bash -lc "
set -e
CAM='$CAM'
VIS='$VIS'
sudo docker cp /tmp/instant_detection.py \"\$CAM:/app/src/services/instant_detection.py\"
sudo docker cp /tmp/camera_detection.py \"\$CAM:/app/src/services/camera_detection.py\"
sudo docker cp /tmp/camera_worker.py \"\$CAM:/app/src/services/camera_worker.py\"
sudo docker cp /tmp/vision_main.py \"\$VIS:/app/src/main.py\"
sudo docker cp /tmp/vision_session_manager.py \"\$VIS:/app/src/session_manager.py\"

# Ensure cameras has aligned INTERNAL_SERVICE_TOKEN + longer VMeta timeouts
cd /home/nickgklezakos.guest/eyenet-platform
python3 - <<'PY'
from pathlib import Path
p = Path('docker-compose.override.yml')
text = p.read_text() if p.exists() else 'services: {}\n'
needle = 'VMETA_AGE_GENDER_TIMEOUT'
if needle not in text:
    # append under cameras environment if present
    block = '''  ppl-meta-cameras:
    environment:
      INTERNAL_SERVICE_TOKEN: ppl-meta-internal-service-secret-key-change-in-production
      VMETA_AGE_GENDER_TIMEOUT: \"20\"
      VMETA_IDENTITY_TIMEOUT: \"20\"
'''
    if 'ppl-meta-cameras:' in text:
        # inject env keys into existing cameras block via rewrite of known override
        text = text.replace(
            'INTERNAL_SERVICE_TOKEN: ppl-meta-internal-service-secret-key-change-in-production',
            'INTERNAL_SERVICE_TOKEN: ppl-meta-internal-service-secret-key-change-in-production\n      VMETA_AGE_GENDER_TIMEOUT: \"20\"\n      VMETA_IDENTITY_TIMEOUT: \"20\"',
            1,
        )
        # cameras block may already have token; ensure VMETA keys once more for cameras section only
        if 'VMETA_AGE_GENDER_TIMEOUT' not in text:
            text = text.rstrip() + '\n' + block
    else:
        text = text.rstrip() + '\n' + block
    p.write_text(text)
    print('override updated with VMeta timeouts')
else:
    print('override already has VMeta timeouts')
PY

# Inject env into running cameras without full recreate when possible
sudo docker exec \"\$CAM\" sh -c 'printenv INTERNAL_SERVICE_TOKEN | wc -c'
sudo docker restart \"\$CAM\" \"\$VIS\"
# Also restart celery worker if cameras uses separate celery container (same image often)
CEL=\$(sudo docker ps --format '{{.Names}}' | grep -E 'celery|cameras-worker' | head -3 || true)
if [ -n \"\$CEL\" ]; then
  echo \"restarting celery: \$CEL\"
  sudo docker restart \$CEL || true
fi
sleep 8
echo ===verify patches===
sudo docker exec \"\$CAM\" grep -n 'VMETA_AGE_GENDER_TIMEOUT\\|internal service token' /app/src/services/instant_detection.py /app/src/services/camera_detection.py | head -20
sudo docker exec \"\$VIS\" grep -n 'success=True\\|return str(sub)' /app/src/session_manager.py /app/src/main.py | head -20
sudo docker ps --filter name=pplmeta --format '{{.Names}} {{.Status}}' | head -20
"
