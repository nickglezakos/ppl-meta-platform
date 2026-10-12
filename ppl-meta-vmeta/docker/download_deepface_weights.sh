#!/usr/bin/env bash
# Download DeepFace model weights into $DEEPFACE_HOME/weights (default: /root/.deepface).
# Used at image build time so labs/installs do not hit GitHub on first face.
set -euo pipefail

DEEPFACE_HOME="${DEEPFACE_HOME:-/root/.deepface}"
WEIGHTS_DIR="${DEEPFACE_HOME}/weights"
BASE_URL="${DEEPFACE_WEIGHTS_BASE_URL:-https://github.com/serengil/deepface_models/releases/download/v1.0}"
RETRIES="${DEEPFACE_WEIGHTS_RETRIES:-5}"

mkdir -p "${WEIGHTS_DIR}"

# name:min_bytes — facenet512 ~90.5 MiB; age/gender ~513–539 MiB. Reject truncations.
download_one() {
  local name="$1"
  local min_bytes="$2"
  local dest="${WEIGHTS_DIR}/${name}"
  local url="${BASE_URL}/${name}"
  local attempt=1

  if [[ -f "${dest}" ]]; then
    local size
    size="$(wc -c < "${dest}" | tr -d ' ')"
    if [[ "${size}" -ge "${min_bytes}" ]]; then
      echo "OK already present: ${name} (${size} bytes)"
      return 0
    fi
    echo "WARN trunc/incomplete ${name} (${size} < ${min_bytes}); re-downloading"
    rm -f "${dest}"
  fi

  while [[ "${attempt}" -le "${RETRIES}" ]]; do
    echo "Downloading ${name} (attempt ${attempt}/${RETRIES})..."
    if curl -fL --retry 3 --retry-delay 2 --connect-timeout 30 \
      --output "${dest}.partial" "${url}"; then
      local size
      size="$(wc -c < "${dest}.partial" | tr -d ' ')"
      if [[ "${size}" -ge "${min_bytes}" ]]; then
        mv "${dest}.partial" "${dest}"
        echo "OK ${name} (${size} bytes)"
        return 0
      fi
      echo "WARN ${name} too small (${size} < ${min_bytes})"
      rm -f "${dest}.partial"
    else
      echo "WARN curl failed for ${name}"
      rm -f "${dest}.partial"
    fi
    attempt=$((attempt + 1))
    sleep $((attempt * 2))
  done

  echo "ERROR failed to download ${name} after ${RETRIES} attempts" >&2
  return 1
}

download_one "facenet512_weights.h5" 90000000
download_one "age_model_weights.h5" 500000000
download_one "gender_model_weights.h5" 500000000

echo "DeepFace weights ready in ${WEIGHTS_DIR}:"
ls -lh "${WEIGHTS_DIR}"
