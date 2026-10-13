#!/usr/bin/env bash
# Stage 2 Mode D for 2.25.97: rebuild vision + orchestrator, retag-forward rest, finalize.
# Usage (from Mac):
#   ./artifacts/lab-stage2-2.25.97.sh vision
#   ./artifacts/lab-stage2-2.25.97.sh orchestrator
#   ./artifacts/lab-stage2-2.25.97.sh retag
#   ./artifacts/lab-stage2-2.25.97.sh finalize
set -euo pipefail

LAB="${LAB:-eyenet@192.168.9.13}"
SVC="${1:-}"
RELEASE_TAG=2.25.97
FROM_TAG=2.25.96
EXCLUDE="vision orchestrator"

if [[ -z "$SVC" ]]; then
  echo "Usage: $0 vision|orchestrator|retag|finalize"
  exit 2
fi

ssh_lab() {
  ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120 "$LAB" "$@"
}

case "$SVC" in
  vision|orchestrator)
    ssh_lab bash -s <<EOF
set -euo pipefail
cd ~/ppl-meta-platform
git fetch origin && git checkout main && git reset --hard origin/main
test "\$(tr -d '[:space:]' < VERSION)" = "$RELEASE_TAG"
export RELEASE_TAG=$RELEASE_TAG EXTRA_SHA_TAG=1
for attempt in 1 2 3 4 5; do
  echo "======== $SVC attempt \$attempt ========"
  if EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh $SVC; then
    exit 0
  fi
  echo "failed; sleeping 20s…"
  sleep 20
done
echo "REPORT FAIL service=$SVC"
exit 1
EOF
    ;;
  retag)
    ssh_lab bash -s <<EOF
set -euo pipefail
cd ~/ppl-meta-platform
git fetch origin && git reset --hard origin/main
export FROM_TAG=$FROM_TAG TO_TAG=$RELEASE_TAG EXCLUDE="$EXCLUDE" EXTRA_SHA_TAG=1
./scripts/stage2_retag_forward.sh
EOF
    ;;
  finalize)
    ssh_lab bash -s <<EOF
set -euo pipefail
cd ~/ppl-meta-platform
git fetch origin && git reset --hard origin/main
export RELEASE_TAG=$RELEASE_TAG
./scripts/stage2_finalize_manifest.sh
# Copy manifest back is done via git pull after lab commits? Prefer: scp from lab.
ls -la deployment/windows-installer/release-manifest.yml
head -20 deployment/windows-installer/release-manifest.yml
EOF
    ;;
  *)
    echo "Unknown: $SVC"
    exit 2
    ;;
esac
