#!/usr/bin/env bash
# Verify deployment/windows-installer/release-manifest.yml against GHCR.
#
# Checks:
#   1. platform_version matches root VERSION (unless --skip-version-check)
#   2. every expected image has a digest
#   3. each digest still matches GHCR for that tag
#
# Usage:
#   ./scripts/verify_release_manifest.sh
#   ./scripts/verify_release_manifest.sh /path/to/release-manifest.yml
#   ./scripts/verify_release_manifest.sh --skip-version-check
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=platform_release_images.sh
source "$ROOT/scripts/platform_release_images.sh"

SKIP_VERSION=0
MANIFEST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-version-check) SKIP_VERSION=1; shift ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      if [[ -z "$MANIFEST" ]]; then
        MANIFEST="$1"
        shift
      else
        echo "Unknown arg: $1" >&2
        exit 2
      fi
      ;;
  esac
done

MANIFEST="${MANIFEST:-$ROOT/deployment/windows-installer/release-manifest.yml}"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"

if [[ ! -f "$MANIFEST" ]]; then
  echo "MISSING manifest: $MANIFEST" >&2
  echo "Run ./scripts/write_release_manifest.sh after Stage 2." >&2
  exit 1
fi

export VERIFY_MANIFEST="$MANIFEST"
export VERIFY_VERSION="$VERSION"
export VERIFY_SKIP_VERSION="$SKIP_VERSION"
export VERIFY_REGISTRY_DEFAULT="$PLATFORM_REGISTRY_DEFAULT"
# Pass expected image names as newline list
printf '%s\n' "${PLATFORM_IMAGE_NAMES[@]}" >"${TMPDIR:-/tmp}/eyenet-manifest-expected.$$"
export VERIFY_EXPECTED_FILE="${TMPDIR:-/tmp}/eyenet-manifest-expected.$$"
# shellcheck disable=SC2064
trap 'rm -f "$VERIFY_EXPECTED_FILE"' EXIT

# Resolve digests via the shared bash helper (docker buildx).
export VERIFY_HELPER="$ROOT/scripts/platform_release_images.sh"

python3 - <<'PY'
import os
import subprocess
import sys
from pathlib import Path

manifest_path = Path(os.environ["VERIFY_MANIFEST"])
version = os.environ["VERIFY_VERSION"]
skip_version = os.environ.get("VERIFY_SKIP_VERSION") == "1"
registry_default = os.environ["VERIFY_REGISTRY_DEFAULT"]
expected = [
    line.strip()
    for line in Path(os.environ["VERIFY_EXPECTED_FILE"]).read_text().splitlines()
    if line.strip()
]
helper = os.environ["VERIFY_HELPER"]

text = manifest_path.read_text()
platform_version = None
registry = None
schema_version = None
images = {}
current = None

for raw in text.splitlines():
    line = raw.rstrip()
    if not line or line.lstrip().startswith("#"):
        continue
    if line.startswith("schema_version:"):
        schema_version = line.split(":", 1)[1].strip().strip('"')
    elif line.startswith("platform_version:"):
        platform_version = line.split(":", 1)[1].strip().strip('"')
    elif line.startswith("registry:"):
        registry = line.split(":", 1)[1].strip().strip('"')
    elif line.startswith("images:"):
        continue
    elif (
        line.startswith("  ")
        and line.strip().endswith(":")
        and not line.strip().startswith(("tag:", "digest:"))
    ):
        current = line.strip().rstrip(":")
        images[current] = {"tag": "", "digest": ""}
    elif current and "tag:" in line:
        images[current]["tag"] = line.split(":", 1)[1].strip().strip('"')
    elif current and "digest:" in line:
        val = line.split(":", 1)[1].strip()
        if "#" in val:
            val = val.split("#", 1)[0].strip()
        val = val.strip('"')
        if val in ("null", "~", ""):
            val = ""
        images[current]["digest"] = val

registry = registry or registry_default

print(f"Verifying release manifest: {manifest_path}")
print(
    f"  schema_version={schema_version or '?'} "
    f"platform_version={platform_version or '?'} registry={registry}"
)
print()

fail = 0
if not skip_version:
    if platform_version != version:
        print(f"DRIFT   platform_version={platform_version} != root VERSION={version}")
        fail += 1
    else:
        print(f"OK      platform_version matches VERSION ({version})")


def resolve_digest(ref: str) -> str:
    script = f'''
set -euo pipefail
source "{helper}"
platform_resolve_digest "{ref}"
'''
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    out = (proc.stdout or "").strip()
    return out if out.startswith("sha256:") else ""


for image in expected:
    if image not in images:
        print(f"MISSING {image} (not in manifest)")
        fail += 1
        continue
    tag = images[image]["tag"]
    digest = images[image]["digest"]
    if not digest.startswith("sha256:"):
        print(f"BAD     {image}: missing or invalid digest")
        fail += 1
        continue
    ref = f"{registry}/{image}:{tag}"
    live = resolve_digest(ref)
    if not live:
        print(f"MISSING {ref} (cannot resolve on GHCR)")
        fail += 1
    elif live == digest:
        print(f"OK      {image}  {digest}")
    else:
        print(f"DRIFT   {image}: manifest={digest}  ghcr={live}")
        fail += 1

for name in images:
    if name not in expected:
        print(f"WARN    unexpected manifest key: {name}")

print()
if fail:
    print(f"FAILED: {fail} check(s) failed")
    sys.exit(1)
print(f"PASSED: release manifest matches GHCR for {platform_version}")
PY
