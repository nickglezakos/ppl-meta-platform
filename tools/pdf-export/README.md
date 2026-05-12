# Print-Friendly PDF Utility (Isolated)

This utility is isolated under `tools/pdf-export` and does not affect other monorepo apps.

## Isolation

- Virtual environment: `tools/pdf-export/venv` created with Python 3.11
- Python dependencies: local to that virtual environment only
- Output folder: `tools/pdf-export/output`

## Build simplified print HTML

```bash
source tools/pdf-export/venv/bin/activate
python tools/pdf-export/build_print_html.py
```

Default output:

- `tools/pdf-export/output/business-plan-print-friendly.html`

## Build PDF from the simplified HTML

Use the existing Playwright exporter already in the repo:

```bash
node tools/export-business-plan-pdf.mjs \
  "tools/pdf-export/output/business-plan-print-friendly.html" \
  "tools/pdf-export/output/business-plan-print-friendly.pdf"
```

## Build print HTML with static chart images (recommended)

This captures the existing Chart.js canvases as PNG images and replaces interactive canvases with static images for more stable PDFs.

```bash
node tools/pdf-export/build_static_chart_print_html.mjs \\
  "product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/index.html" \\
  "tools/pdf-export/output/business-plan-static-charts.html"
```

Then generate PDF from that static-chart HTML:

```bash
node tools/export-business-plan-pdf.mjs \\
  "tools/pdf-export/output/business-plan-static-charts.html" \\
  "tools/pdf-export/output/business-plan-static-charts.pdf"
```

## Optional custom paths

```bash
python tools/pdf-export/build_print_html.py \
  --input "product/BP and Funding/Business Plan/documents/eyenetBusinessPLan/index.html" \
  --output "tools/pdf-export/output/custom-print.html"
```
