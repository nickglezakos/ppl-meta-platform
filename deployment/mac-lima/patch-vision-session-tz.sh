#!/usr/bin/env bash
# Restore image-compatible session_manager.py and surgically add _ensure_aware.
set -euo pipefail
cd "${HOME}/eyenet-platform"
VIS_CID="$(docker compose -f docker-compose.yml -p pplmeta ps -aq ppl-meta-vision)"
IMG="$(docker inspect -f '{{.Image}}' "$VIS_CID")"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

docker create --name vis-extract "$IMG" >/dev/null
docker cp vis-extract:/app/src/session_manager.py "$TMP/session_manager.py"
docker rm vis-extract >/dev/null

python3 - "$TMP/session_manager.py" <<'PY'
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
text = p.read_text()

if "from datetime import datetime, timezone" not in text:
    text = text.replace("from datetime import datetime\n", "from datetime import datetime, timezone\n", 1)

if "_ensure_aware" not in text:
    candidates = [
        "    def _get_current_timestamp(self) -> datetime:\n        \"\"\"Get current timestamp in UTC.\"\"\"\n        return datetime.now(timezone.utc)\n",
        "    def _get_current_timestamp(self) -> datetime:\n        \"\"\"Get current timestamp in UTC.\"\"\"\n        return datetime.utcnow()\n",
    ]
    needle = next((c for c in candidates if c in text), None)
    if not needle:
        raise SystemExit("timestamp helper not found")
    helper = """
    @staticmethod
    def _ensure_aware(dt):
        \"\"\"Normalize DB/naive timestamps so duration math never mixes tz awareness.\"\"\"
        if dt is None:
            return None
        if getattr(dt, "tzinfo", None) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
"""
    text = text.replace(needle, needle + helper, 1)
    print("inserted _ensure_aware")
else:
    print("already has ensure_aware")

text, n1 = re.subn(
    r"session_duration\s*=\s*\(\s*current_time\s*-\s*current_session\.started_at\s*\)\.total_seconds\(\)",
    "session_duration = (current_time - (self._ensure_aware(current_session.started_at) or current_time)).total_seconds()",
    text,
)
text, n2 = re.subn(
    r"-\s*session_data\[\"started_at\"\]",
    '- self._ensure_aware(session_data["started_at"])',
    text,
)
text, n3 = re.subn(
    r'session_data\.get\("ended_at"\)\s*\n(\s*)or self\._get_current_timestamp\(\)',
    r'self._ensure_aware(session_data.get("ended_at"))\n\1or self._get_current_timestamp()',
    text,
)
print(f"fixes n1={n1} n2={n2} n3={n3}")
p.write_text(text)
PY

docker stop "$VIS_CID"
docker cp "$TMP/session_manager.py" "$VIS_CID":/app/src/session_manager.py
docker start "$VIS_CID"

for i in $(seq 1 25); do
  st="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$VIS_CID")"
  echo "  $i $st"
  [[ "$st" == "healthy" ]] && break
  sleep 2
done

docker compose -f docker-compose.yml -p pplmeta exec -T ppl-meta-vision \
  grep -n "_ensure_aware" /app/src/session_manager.py | head -5

bash /Users/nickgklezakos/Documents/ppl-meta-code/deployment/mac-lima/reregister-discovery-services.sh
echo DONE
