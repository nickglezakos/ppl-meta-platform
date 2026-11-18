#!/usr/bin/env bash
set -euo pipefail
cd /home/eyenet/ppl-meta-platform
export PATH=/opt/flutter/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export RELEASE_TAG=2.25.107
echo "START=$(date -u -Iseconds)"
# frontend already published from earlier attempt; rebuild remaining Mode D services here
./scripts/stage2_one.sh vmeta gateway vision orchestrator cameras
echo "REBUILD_DONE=$(date -u -Iseconds)"
FROM_TAG=2.25.106 TO_TAG=2.25.107 EXCLUDE="frontend vmeta gateway vision orchestrator cameras" ./scripts/stage2_retag_forward.sh
echo "RETAG_DONE=$(date -u -Iseconds)"
./scripts/stage2_finalize_manifest.sh
echo "FINALIZE_DONE=$(date -u -Iseconds)"
