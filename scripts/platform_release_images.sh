#!/usr/bin/env bash
# Shared Stage 2 / release-manifest image identity.
# Source from other scripts:  source "$(dirname "$0")/platform_release_images.sh"
#
# Service keys (stage2_one / retag): node media gateway … models
# GHCR image names:               ppl-meta-node … ppl-meta-vision-protected …

# shellcheck disable=SC2034
PLATFORM_REGISTRY_DEFAULT="ghcr.io/nickglezakos/ppl-meta-platform"

# Ordered service keys (build / Stage 2 args)
PLATFORM_SERVICE_KEYS=(
  node
  media
  gateway
  orchestrator
  discovery
  communications
  frontend
  vision
  vmeta
  cameras
  presence
  models
)

# Ordered GHCR image names (manifest / verify)
PLATFORM_IMAGE_NAMES=(
  ppl-meta-node
  ppl-meta-media
  ppl-meta-gateway
  ppl-meta-orchestrator
  ppl-meta-discovery
  ppl-meta-communications
  ppl-meta-frontend
  ppl-meta-vision-protected
  ppl-meta-vmeta-protected
  ppl-meta-cameras
  ppl-meta-presence
  ppl-meta-models
)

platform_image_name_for_key() {
  local key="$1"
  case "$key" in
    vision) echo "ppl-meta-vision-protected" ;;
    vmeta) echo "ppl-meta-vmeta-protected" ;;
    node|media|gateway|orchestrator|discovery|communications|frontend|cameras|presence|models)
      echo "ppl-meta-${key}"
      ;;
    *)
      echo "Unknown service key: $key" >&2
      return 1
      ;;
  esac
}

platform_key_for_image_name() {
  local name="$1"
  case "$name" in
    ppl-meta-vision-protected) echo "vision" ;;
    ppl-meta-vmeta-protected) echo "vmeta" ;;
    ppl-meta-*) echo "${name#ppl-meta-}" ;;
    *)
      echo "Unknown image name: $name" >&2
      return 1
      ;;
  esac
}

platform_image_ref() {
  local registry="$1"
  local image_name="$2"
  local tag="$3"
  echo "${registry}/${image_name}:${tag}"
}

# Resolve the registry digest for a tagged ref (sha256:…).
# Prefers buildx imagetools; falls back to parsing inspect text.
platform_resolve_digest() {
  local ref="$1"
  local digest=""

  if command -v docker >/dev/null 2>&1; then
    digest="$(docker buildx imagetools inspect "$ref" --format '{{.Digest}}' 2>/dev/null || true)"
    if [[ -z "$digest" || "$digest" == "<no value>" || "$digest" == "<nil>" ]]; then
      digest="$(
        docker buildx imagetools inspect "$ref" 2>/dev/null \
          | sed -n 's/^Digest:[[:space:]]*//p' \
          | head -1 \
          || true
      )"
    fi
  fi

  if [[ -z "$digest" || "$digest" != sha256:* ]]; then
    return 1
  fi
  echo "$digest"
}
