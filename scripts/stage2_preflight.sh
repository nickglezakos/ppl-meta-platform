#!/usr/bin/env bash
# Stage 2 preflight: refuse builds that are not backed by pushed GitHub source.
#
# Sourced by stage2_one.sh (and usable standalone).
# Escape hatch for emergencies only:
#   STAGE2_ALLOW_DIRTY=1 RELEASE_TAG=… ./scripts/stage2_one.sh cameras
#
# Why: lab docker cp / local image rebuilds that never hit origin/main produced
# GHCR tags that did not match the "working" lab — Stage 3 then looked "wrong".

stage2_service_paths() {
  local key="$1"
  case "$key" in
    node) echo "ppl-meta-node" ;;
    media) echo "ppl-meta-media" ;;
    gateway) echo "ppl-meta-gateway" ;;
    orchestrator) echo "ppl-meta-orchestrator" ;;
    discovery) echo "ppl-meta-discovery" ;;
    communications) echo "ppl-meta-communications" ;;
    frontend) echo "ppl-meta-frontend" ;;
    vision) echo "ppl-meta-vision" ;;
    vmeta) echo "ppl-meta-vmeta" ;;
    cameras) echo "ppl-meta-cameras" ;;
    presence) echo "ppl-meta-presence" ;;
    models) echo "ppl-meta-models" ;;
    *)
      echo "Unknown Stage 2 service: $key" >&2
      return 2
      ;;
  esac
}

stage2_preflight() {
  local root="${1:-.}"
  shift || true
  local services=("$@")
  local git_bin
  git_bin="$(command -v git || true)"
  if [[ -z "$git_bin" ]]; then
    echo "FATAL: git not found on PATH (required for Stage 2 source gate)" >&2
    return 1
  fi

  if [[ "${STAGE2_ALLOW_DIRTY:-0}" == "1" ]]; then
    echo "WARN: STAGE2_ALLOW_DIRTY=1 — skipping Stage 2 source gate (not a release path)"
    return 0
  fi

  if ! "$git_bin" -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "FATAL: Stage 2 must run inside the git monorepo (got root=$root)" >&2
    return 1
  fi

  echo "==> Stage 2 preflight: sync check against origin/main"
  if ! "$git_bin" -C "$root" fetch origin main >/dev/null 2>&1; then
    echo "WARN: git fetch origin main failed — continuing with existing refs"
  fi

  if ! "$git_bin" -C "$root" rev-parse --verify origin/main >/dev/null 2>&1; then
    echo "FATAL: origin/main missing. Fetch remote before Stage 2." >&2
    return 1
  fi

  local head remote
  head="$("$git_bin" -C "$root" rev-parse HEAD)"
  remote="$("$git_bin" -C "$root" rev-parse origin/main)"
  if [[ "$head" != "$remote" ]]; then
    echo "FATAL: HEAD ($head) != origin/main ($remote)." >&2
    echo "       Stage 1 must land on GitHub, then: git checkout main && git pull --ff-only" >&2
    echo "       Emergency only: STAGE2_ALLOW_DIRTY=1" >&2
    return 1
  fi

  local svc path porcelain
  for svc in "${services[@]}"; do
    path="$(stage2_service_paths "$svc")" || return 2
    if [[ ! -d "$root/$path" ]]; then
      echo "FATAL: missing service tree $path (Stage 1 incomplete?)" >&2
      return 1
    fi
    porcelain="$("$git_bin" -C "$root" status --porcelain -- "$path" || true)"
    if [[ -n "$porcelain" ]]; then
      echo "FATAL: uncommitted changes under $path — Stage 1 first:" >&2
      echo "$porcelain" >&2
      return 1
    fi
    if ! "$git_bin" -C "$root" diff --quiet "origin/main" -- "$path"; then
      echo "FATAL: $path differs from origin/main — push Stage 1 before Stage 2" >&2
      "$git_bin" -C "$root" diff --stat "origin/main" -- "$path" >&2 || true
      return 1
    fi
    echo "OK source gate service=$svc path=$path @ $("$git_bin" -C "$root" rev-parse --short HEAD)"
  done
  return 0
}

# Allow: bash scripts/stage2_preflight.sh frontend cameras
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <service> [service…]" >&2
    exit 2
  fi
  stage2_preflight "$ROOT" "$@"
fi
