#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IN_HTML="${1:-$ROOT_DIR/product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan-interim-print.html}"
OUT_PDF="${2:-$ROOT_DIR/product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan-interim-print.pdf}"

node "$ROOT_DIR/tools/export-business-plan-pdf.mjs" "$IN_HTML" "$OUT_PDF"
echo "Interim PDF generated: $OUT_PDF"
