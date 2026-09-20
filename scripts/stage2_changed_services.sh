#!/usr/bin/env bash
# Map a git revision range to Stage 2 service build keys (for selective rebuilds).
# Usage:
#   ./scripts/stage2_changed_services.sh                 # HEAD~1..HEAD
#   ./scripts/stage2_changed_services.sh origin/main~5..origin/main
#   ./scripts/stage2_changed_services.sh abc123 def456
#
# Prints one line of space-separated service keys (or ALL / NONE) for:
#   RELEASE_TAG=… ./scripts/stage2_one.sh $(./scripts/stage2_changed_services.sh …)
#
# Works with bash 3.2+ (macOS) and bash 5 (Linux/WSL).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -eq 0 ]]; then
  RANGE="HEAD~1..HEAD"
elif [[ $# -eq 1 ]]; then
  RANGE="$1"
elif [[ $# -eq 2 ]]; then
  RANGE="$1..$2"
else
  echo "Usage: $0 [git-range | from_sha to_sha]" >&2
  exit 2
fi

FILES=()
while IFS= read -r line; do
  [[ -n "$line" ]] && FILES+=("$line")
done < <(git diff --name-only "$RANGE" 2>/dev/null || true)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No file changes in range: $RANGE" >&2
  exit 1
fi

need_list=""
add_need() {
  local s="$1"
  case " $need_list " in
    *" $s "*) ;;
    *) need_list="${need_list:+$need_list }$s" ;;
  esac
}

force_all=0
for f in "${FILES[@]}"; do
  case "$f" in
    ppl-meta-node/*) add_need node ;;
    ppl-meta-media/*) add_need media ;;
    ppl-meta-gateway/*) add_need gateway ;;
    ppl-meta-orchestrator/*) add_need orchestrator ;;
    ppl-meta-discovery/*) add_need discovery ;;
    ppl-meta-communications/*) add_need communications ;;
    ppl-meta-frontend/*) add_need frontend ;;
    ppl-meta-vision/*) add_need vision ;;
    ppl-meta-vmeta/*) add_need vmeta ;;
    ppl-meta-cameras/*) add_need cameras ;;
    ppl-meta-presence/*) add_need presence ;;
    ppl-meta-models/*) add_need models ;;
    shared/*|deployment/windows-installer/schema/*)
      force_all=1
      ;;
  esac
done

if [[ "$force_all" -eq 1 ]]; then
  echo "ALL"
  echo "Reason: shared/ or schema/ changed in $RANGE — full twelve-image Stage 2 recommended." >&2
  exit 0
fi

if [[ -z "$need_list" ]]; then
  echo "NONE"
  echo "No service image paths changed in $RANGE (docs/installer-only Stage 1)." >&2
  exit 0
fi

# Stable order matching build script defaults
ORDER="node media gateway orchestrator discovery communications frontend vision vmeta cameras presence models"
out=""
for s in $ORDER; do
  case " $need_list " in
    *" $s "*) out="${out:+$out }$s" ;;
  esac
done

echo "$out"
echo "Range $RANGE → services: $out" >&2
