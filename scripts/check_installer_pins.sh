#!/usr/bin/env bash
# Fail if installer RELEASE_TAG / VERSION pins drift from root VERSION.
# One product on GHCR; both installers must pin the same tag.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
fail=0

check() {
  local file="$1"
  local pattern="$2"
  if [[ ! -f "$file" ]]; then
    echo "MISSING $file"
    fail=$((fail + 1))
    return
  fi
  if grep -E "$pattern" "$file" >/dev/null; then
    echo "OK      $file"
  else
    echo "DRIFT   $file (expected pin $VERSION)"
    fail=$((fail + 1))
  fi
}

echo "Checking installer pins against VERSION=$VERSION"
echo

check "$ROOT/deployment/windows-installer/.env.windows.template" \
  "^RELEASE_TAG=${VERSION}$"
check "$ROOT/deployment/windows-installer/install-platform.bat" \
  "^set \"VERSION=${VERSION}\"\$"
check "$ROOT/deployment/windows-installer/install-platform.ps1" \
  "\\\$script:ReleaseTag = \"${VERSION}\""
check "$ROOT/deployment/ubuntu/install-eyenet-ubuntu.sh" \
  "^RELEASE_TAG=\"\\\$\{RELEASE_TAG:-${VERSION}\}\"\$"

echo
if (( fail > 0 )); then
  echo "FAILED: ${fail} pin check(s) failed"
  exit 1
fi
echo "PASSED: both installers pin VERSION=${VERSION}"
