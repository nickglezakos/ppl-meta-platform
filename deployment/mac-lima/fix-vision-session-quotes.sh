#!/usr/bin/env bash
set -euo pipefail
cd "${HOME}/eyenet-platform"
VIS_CID="$(docker compose -f docker-compose.yml -p pplmeta ps -aq ppl-meta-vision)"
TMP="$(mktemp)"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

docker cp "$VIS_CID":/app/src/session_manager.py "$TMP"
python3 - "$TMP" <<'PY'
from pathlib import Path
import ast
import sys

p = Path(sys.argv[1])
text = p.read_text()
fixed = text.replace(r'\"ended_at\"', '"ended_at"')
print("changed", fixed != text)
for i, line in enumerate(fixed.splitlines(), 1):
    if "_ensure_aware" in line and "ended_at" in line:
        print(i, repr(line))
p.write_text(fixed)
ast.parse(fixed)
print("syntax_ok")
PY

docker stop "$VIS_CID"
docker cp "$TMP" "$VIS_CID":/app/src/session_manager.py
docker start "$VIS_CID"

for i in $(seq 1 25); do
  st="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$VIS_CID")"
  echo "  $i $st"
  [[ "$st" == "healthy" ]] && break
  sleep 2
done

docker compose -f docker-compose.yml -p pplmeta exec -T ppl-meta-vision \
  python -c 'import ast; ast.parse(open("/app/src/session_manager.py").read()); print("syntax_ok")'
docker compose -f docker-compose.yml -p pplmeta exec -T ppl-meta-vision sed -n '315,322p' /app/src/session_manager.py
echo DONE
