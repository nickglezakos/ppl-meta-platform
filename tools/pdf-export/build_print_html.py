#!/usr/bin/env python3
"""Build a simplified, print-friendly HTML from the current business plan."""

from __future__ import annotations

import argparse
from pathlib import Path
from bs4 import BeautifulSoup


DEFAULT_INPUT = Path(
  (
    "product/BP and Funding/Business Plan/documents/"
    "eyenetBusinessPLan/index.html"
  )
)
DEFAULT_OUTPUT = Path(
  "tools/pdf-export/output/business-plan-print-friendly.html"
)


def clean_section(
  section_wrapper: BeautifulSoup,
  soup_factory: BeautifulSoup,
) -> BeautifulSoup:
    """Remove interactive-only pieces that are noisy for print."""
    # Drop script/style fragments if any made it into copied section content.
    for node in section_wrapper.find_all(["script", "style"]):
        node.decompose()

    # Remove canvas-heavy chart blocks and replace with compact placeholders.
    for canvas in section_wrapper.find_all("canvas"):
        placeholder = soup_factory.new_tag("div")
        placeholder["class"] = ["chart-placeholder"]
        title = "Chart"

        # Try to pick nearby heading text.
        heading = None
        parent = canvas.parent
        if parent:
            heading = parent.find(["h2", "h3", "h4"])
        if heading and heading.get_text(strip=True):
            title = heading.get_text(" ", strip=True)

        placeholder.string = (
          f"{title} (interactive chart omitted in print-friendly export)"
        )

        # Replace the closest chart card if it mostly contains this one canvas.
        card = canvas.parent
        if (
          card
          and len(card.find_all("canvas")) == 1
          and len(card.find_all(recursive=False)) <= 3
        ):
            card.replace_with(placeholder)
        else:
            canvas.replace_with(placeholder)

    return section_wrapper


def build_document(input_path: Path, output_path: Path) -> Path:
    html = input_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    main_el = soup.find("main")
    if not main_el:
        raise RuntimeError("Could not find <main> in source HTML")

    pages = main_el.find_all("div", class_="page", recursive=False)
    if not pages:
        raise RuntimeError("Could not find page sections in source HTML")

    sections = []
    for page in pages:
        section_id = page.get("id", "section")
        wrapper = page.find("div", class_="content-wrapper")
        if not wrapper:
            continue

        section_title_tag = wrapper.find("h1")
        if section_title_tag:
            section_title = section_title_tag.get_text(" ", strip=True)
        else:
            section_title = section_id.title()

        cleaned = BeautifulSoup(str(wrapper), "lxml")
        body = cleaned.find("div", class_="content-wrapper")
        body = clean_section(body if body else cleaned, cleaned)

        sections.append(
            {
                "id": section_id,
                "title": section_title,
                "content": str(body),
            }
        )

    toc_items = "\n".join(
        f'<li><a href="#{s["id"]}">{s["title"]}</a></li>' for s in sections
    )
    section_blocks = "\n".join(
        (
          f"<section id=\"{s['id']}\" class=\"print-section\">\n"
          f"{s['content']}\n"
          "</section>"
        )
        for s in sections
    )

    output_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>EyeNet Vision - Print Friendly Business Plan</title>
  <style>
    @page {{
      size: A4;
      margin: 14mm;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: #1a1a1a;
      background: #ffffff;
      line-height: 1.45;
    }}

    .doc {{
      max-width: 900px;
      margin: 0 auto;
      padding: 0;
    }}

    .toc {{
      border: 1px solid #d7d7d7;
      padding: 16px 20px;
      margin-bottom: 22px;
      page-break-after: always;
    }}

    .toc h1 {{
      margin: 0 0 8px 0;
      font-size: 28px;
      border-bottom: 2px solid #333;
      padding-bottom: 6px;
    }}

    .toc p {{
      margin: 0 0 10px 0;
      color: #444;
    }}

    .toc ol {{
      margin: 0;
      padding-left: 20px;
    }}

    .toc li {{
      margin: 4px 0;
    }}

    .toc a {{
      color: #111;
      text-decoration: none;
    }}

    .print-section {{
      page-break-before: always;
      break-before: page;
    }}

    .print-section:first-of-type {{
      page-break-before: auto;
      break-before: auto;
    }}

    .content-wrapper {{
      border: 1px solid #d7d7d7;
      border-radius: 0;
      box-shadow: none;
      padding: 16px 18px;
      background: #fff;
    }}

    h1, h2, h3, h4 {{
      break-after: avoid-page;
      page-break-after: avoid;
      margin-top: 14px;
      margin-bottom: 7px;
      color: #111;
    }}

    h1 {{
      font-size: 24px;
      border-bottom: 2px solid #333;
      padding-bottom: 6px;
      margin-top: 0;
    }}

    h2 {{
      font-size: 20px;
      border-bottom: 1px solid #999;
      padding-bottom: 4px;
    }}

    h3 {{ font-size: 16px; }}
    h4 {{ font-size: 14px; }}

    p, li, td, th {{
      font-size: 11.5px;
      color: #222;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0;
      page-break-inside: auto;
    }}

    thead {{
      display: table-header-group;
    }}

    tr {{
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    th, td {{
      border: 1px solid #cfcfcf;
      padding: 6px;
      vertical-align: top;
    }}

    th {{
      background: #efefef;
      color: #111;
    }}

    .chart-placeholder {{
      border: 1px dashed #b8b8b8;
      background: #fafafa;
      padding: 8px 10px;
      margin: 8px 0 12px 0;
      font-size: 10.5px;
      color: #555;
      font-style: italic;
    }}

    .badge, .badge-nav, .badge-nav-container, nav, footer, #backToTop {{
      display: none !important;
    }}
  </style>
</head>
<body>
  <div class="doc">
    <section class="toc" aria-label="Table of Contents">
      <h1>Table of Contents</h1>
      <p>EyeNet Vision Business Plan 2026</p>
      <ol>
{toc_items}
      </ol>
    </section>
{section_blocks}
  </div>
</body>
</html>
'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_html, encoding="utf-8")
    return output_path


def cli_main() -> None:
    parser = argparse.ArgumentParser(
        description="Build print-friendly business plan HTML"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = build_document(args.input, args.output)
    print(f"Generated print-friendly HTML: {output}")


if __name__ == "__main__":
    cli_main()
