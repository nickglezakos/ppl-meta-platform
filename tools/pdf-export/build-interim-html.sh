#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_HTML="${1:-$ROOT_DIR/product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan.html}"
OUT_HTML="${2:-$ROOT_DIR/product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/BusinessPlan-interim-print.html}"

node "$ROOT_DIR/tools/pdf-export/build_static_chart_print_html.mjs" "$SRC_HTML" "$OUT_HTML"
echo "Interim HTML generated: $OUT_HTML"
