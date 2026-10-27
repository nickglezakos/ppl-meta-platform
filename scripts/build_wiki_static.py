#!/usr/bin/env python3
"""Build static HTML for EyeNet online wiki from docs/wiki markdown."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import markdown as md_lib
except ImportError:  # pragma: no cover - CI installs markdown
    md_lib = None

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIKI_ROOT = REPO_ROOT / "docs" / "documentation" / "wiki"
DEFAULT_CSS = REPO_ROOT / "autonomous" / "ppl-meta-wiki" / "static" / "site.css"
DEFAULT_JS = REPO_ROOT / "autonomous" / "ppl-meta-wiki" / "static" / "wiki.js"
DEFAULT_LOGO = REPO_ROOT / "autonomous" / "ppl-meta-wiki" / "static" / "eyenet-dark.svg"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "wiki-site"

SITES = (
    ("what-is-eyenet", "What is EyeNet"),
    ("owners-admins", "User guide"),
    ("distributors", "Distributors guide"),
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass
class PageInfo:
    audience: str
    section_label: str
    rel_html: str
    url: str
    title: str
    text: str
    platform_version: str
    nav_order: int = 100


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    platform_version = ""
    in_software_ref = False
    for raw in match.group(1).splitlines():
        line = raw.rstrip()
        if line.startswith("software_ref:"):
            in_software_ref = True
            continue
        if in_software_ref and line.startswith("  platform_version:"):
            platform_version = line.split(":", 1)[1].strip().strip('"').strip("'")
            continue
        if in_software_ref and line and not line.startswith(" "):
            in_software_ref = False
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    if platform_version:
        meta["platform_version"] = platform_version
    body = text[match.end() :]
    return meta, body


def nav_order_from_meta(meta: dict[str, str], rel_html: str) -> int:
    raw = meta.get("nav_order", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    # Default: index first, then alphabetical-ish high numbers
    return 0 if rel_html == "index.html" else 100


def rewrite_md_links(body: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        if target.endswith(".md"):
            target = target[:-3] + ".html"
        elif "/index.md" in target:
            target = target.replace("/index.md", "/index.html")
        return f"[{label}]({target})"

    return MD_LINK_RE.sub(repl, body)


def render_markdown(body: str) -> str:
    if md_lib is None:
        raise SystemExit(
            "Python package 'markdown' is required. Install with: pip install markdown"
        )
    return md_lib.markdown(
        body,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "md_in_html"],
        output_format="html5",
    )


def plain_text(md_body: str) -> str:
    text = TAG_RE.sub(" ", md_body)
    text = re.sub(r"[#*_`>\-|]", " ", text)
    return WS_RE.sub(" ", text).strip()


def asset_href(rel_posix: str, asset: str, version: str = "") -> str:
    depth = rel_posix.count("/")
    href = "../" * depth + f"assets/{asset}"
    if version:
        href = f"{href}?v={version}"
    return href


def file_version(path: Path) -> str:
    digest = __import__("hashlib").sha1(path.read_bytes()).hexdigest()
    return digest[:10]


def sidebar_pages_html(pages: list[PageInfo], current_url: str) -> str:
    items: list[str] = []
    # Explicit nav_order (from frontmatter), then title
    ordered = sorted(
        pages,
        key=lambda p: (p.nav_order, p.title.lower()),
    )
    for page in ordered:
        current = ' aria-current="page"' if page.url == current_url else ""
        items.append(
            f'<a href="{html.escape(page.url)}" data-title="{html.escape(page.title)}"{current}>'
            f"{html.escape(page.title)}</a>"
        )
    return "\n".join(items)


def page_shell(
    *,
    title: str,
    audience: str | None,
    body_html: str,
    platform_version: str,
    css_href: str,
    js_href: str,
    search_index_href: str,
    logo_href: str,
    sidebar_html: str,
    sidebar_heading: str,
) -> str:
    nav_bits = [
        '<a href="/"'
        + (' aria-current="section"' if audience is None else "")
        + ">Home</a>",
        '<a href="/what-is-eyenet/"'
        + (' aria-current="section"' if audience == "what-is-eyenet" else "")
        + ">What is EyeNet</a>",
        '<a href="/owners-admins/"'
        + (' aria-current="section"' if audience == "owners-admins" else "")
        + ">User guide</a>",
        '<a href="/distributors/"'
        + (' aria-current="section"' if audience == "distributors" else "")
        + ">Distributors guide</a>",
    ]
    version_line = (
        f"Platform ref: <code>{html.escape(platform_version)}</code>"
        if platform_version
        else "EyeNet online wiki"
    )
    audience_attr = html.escape(audience or "home")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="icon" href="{html.escape(logo_href)}" type="image/svg+xml">
  <link rel="stylesheet" href="{html.escape(css_href)}">
</head>
<body data-audience="{audience_attr}" data-search-index="{html.escape(search_index_href)}">
  <header class="site-header">
    <div class="site-header-inner">
      <div class="header-nav">
        <button type="button" class="sidebar-toggle" id="sidebarToggle" aria-expanded="false" aria-controls="wikiSidebar">Menu</button>
        <a class="brand" href="/" aria-label="EyeNet Wiki home">
          <img class="brand-logo" src="{html.escape(logo_href)}" alt="EyeNet">
        </a>
      </div>
      <nav class="header-nav" aria-label="Site sections">{"".join(nav_bits)}</nav>
    </div>
  </header>
  <div class="sidebar-backdrop" id="sidebarBackdrop"></div>
  <div class="layout">
    <aside class="sidebar" id="wikiSidebar" aria-label="Wiki pages">
      <div class="search-wrap">
        <label class="visually-hidden" for="wikiSearch" style="position:absolute;left:-9999px">Search wiki</label>
        <input id="wikiSearch" type="search" placeholder="Search wiki…" autocomplete="off" spellcheck="false">
      </div>
      <div class="sidebar-label">{html.escape(sidebar_heading)}</div>
      <nav class="sidebar-nav" id="sidebarNav">
{sidebar_html}
      </nav>
      <div class="search-empty" id="searchEmpty">No matching pages</div>
      <div class="search-hits" id="searchHits"></div>
    </aside>
    <div class="content-wrap">
      <main class="page">
{body_html}
      </main>
      <footer class="site-footer">
        <div class="site-footer-inner">{version_line}</div>
      </footer>
    </div>
  </div>
  <script src="{html.escape(js_href)}" defer></script>
</body>
</html>
"""


def _is_archived_wiki_path(rel: Path) -> bool:
    """Skip _archive trees and pages marked archived in front matter."""
    return any(part in {"_archive", "archive"} for part in rel.parts)


def collect_site_pages(src: Path, audience: str, section_label: str) -> list[PageInfo]:
    pages: list[PageInfo] = []
    for md_path in sorted(src.rglob("*.md")):
        rel = md_path.relative_to(src)
        if _is_archived_wiki_path(rel):
            continue
        rel_html = rel.with_suffix(".html").as_posix()
        text = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if meta.get("archived") in (True, "true", "yes", 1):
            continue
        title = meta.get("title") or md_path.stem.replace("-", " ").title()
        url = f"/{audience}/" if rel_html == "index.html" else f"/{audience}/{rel_html}"
        pages.append(
            PageInfo(
                audience=audience,
                section_label=section_label,
                rel_html=rel_html,
                url=url,
                title=title,
                text=plain_text(body),
                platform_version=meta.get("platform_version", ""),
                nav_order=nav_order_from_meta(meta, rel_html),
            )
        )
    return pages


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
DOWNLOAD_SUFFIXES = {".zip", ".apk", ".sha256", ".txt"}


def copy_site_images(src: Path, dest: Path) -> int:
    """Copy illustration files that sit beside wiki markdown."""
    copied = 0
    for path in src.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        rel = path.relative_to(src)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        copied += 1
    return copied


def copy_site_downloads(src: Path, dest: Path) -> int:
    """Copy downloadable packages (APK zips, checksums) under downloads/."""
    downloads = src / "downloads"
    if not downloads.is_dir():
        return 0
    copied = 0
    out_root = dest / "downloads"
    out_root.mkdir(parents=True, exist_ok=True)
    for path in downloads.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in DOWNLOAD_SUFFIXES:
            continue
        rel = path.relative_to(downloads)
        out = out_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        copied += 1
    return copied


def build_site_tree(
    src: Path,
    dest: Path,
    audience: str,
    section_label: str,
    pages: list[PageInfo],
    asset_version: str,
) -> str:
    dest.mkdir(parents=True, exist_ok=True)
    found_version = ""
    by_rel = {p.rel_html: p for p in pages}

    for md_path in sorted(src.rglob("*.md")):
        rel = md_path.relative_to(src)
        if _is_archived_wiki_path(rel):
            continue
        rel_html = rel.with_suffix(".html").as_posix()
        if rel_html not in by_rel:
            continue
        out_path = dest / rel.with_suffix(".html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        text = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        body = rewrite_md_links(body)
        body_html = render_markdown(body)
        page = by_rel[rel_html]
        version = page.platform_version or found_version
        if page.platform_version and not found_version:
            found_version = page.platform_version
        asset_rel = f"{audience}/{rel_html}"
        out_path.write_text(
            page_shell(
                title=f"{page.title} · EyeNet Wiki",
                audience=audience,
                body_html=body_html,
                platform_version=version or found_version,
                css_href=asset_href(asset_rel, "site.css", asset_version),
                js_href=asset_href(asset_rel, "wiki.js", asset_version),
                search_index_href=asset_href(asset_rel, "search-index.json", asset_version),
                logo_href=asset_href(asset_rel, "eyenet-dark.svg", asset_version),
                sidebar_html=sidebar_pages_html(pages, page.url),
                sidebar_heading=section_label,
            ),
            encoding="utf-8",
        )
    return found_version


def landing_sidebar_html(all_pages: list[PageInfo]) -> str:
    """Home sidebar: top-level section drawers with indented child pages."""
    by_audience: dict[str, list[PageInfo]] = {}
    for page in all_pages:
        by_audience.setdefault(page.audience, []).append(page)

    parts = [
        '<a href="/" data-title="Home" aria-current="page">Home</a>',
    ]
    for slug, label in SITES:
        pages = sorted(
            by_audience.get(slug, []),
            key=lambda p: (p.nav_order, p.title.lower()),
        )
        children = [p for p in pages if p.rel_html != "index.html"]
        group_id = f"nav-group-{slug}"
        parts.append(f'<div class="nav-group is-open" data-nav-group="{html.escape(slug)}">')
        parts.append('<div class="nav-group-head">')
        parts.append(
            f'<a class="nav-group-link" href="/{html.escape(slug)}/" '
            f'data-title="{html.escape(label)}">{html.escape(label)}</a>'
        )
        if children:
            parts.append(
                f'<button type="button" class="nav-group-toggle" aria-expanded="true" '
                f'aria-controls="{html.escape(group_id)}" '
                f'aria-label="Toggle {html.escape(label)} pages">▾</button>'
            )
        parts.append("</div>")
        if children:
            parts.append(
                f'<div class="nav-group-body" id="{html.escape(group_id)}">'
            )
            for page in children:
                parts.append(
                    f'<a class="nav-child" href="{html.escape(page.url)}" '
                    f'data-title="{html.escape(page.title)}">'
                    f"{html.escape(page.title)}</a>"
                )
            parts.append("</div>")
        parts.append("</div>")
    return "\n".join(parts)


def write_landing(
    out: Path,
    all_pages: list[PageInfo],
    version: str,
    asset_version: str,
) -> None:
    body = """
<h1>EyeNet Wiki</h1>
<p>Product overview plus separate how-to guides for install owners and channel operators.</p>
<div class="landing-cards">
  <a class="landing-card" href="/what-is-eyenet/">
    <strong>What is EyeNet</strong>
    <span>Six applications on one on-premises platform — Presence, Signage, Vradar, Gate, Sentinel, Matrix.</span>
  </a>
  <a class="landing-card" href="/owners-admins/">
    <strong>User guide</strong>
    <span>Install, bootstrap, cameras, Presence, Signage, Automation, analytics, and remote access.</span>
  </a>
  <a class="landing-card" href="/distributors/">
    <strong>Distributors guide</strong>
    <span>Authority admin, invites, and installation licences.</span>
  </a>
</div>
"""
    (out / "index.html").write_text(
        page_shell(
            title="EyeNet Wiki",
            audience=None,
            body_html=body,
            platform_version=version,
            css_href=f"assets/site.css?v={asset_version}",
            js_href=f"assets/wiki.js?v={asset_version}",
            search_index_href=f"assets/search-index.json?v={asset_version}",
            logo_href=f"assets/eyenet-dark.svg?v={asset_version}",
            sidebar_html=landing_sidebar_html(all_pages),
            sidebar_heading="Browse",
        ),
        encoding="utf-8",
    )


def write_search_index(out: Path, pages: list[PageInfo]) -> None:
    payload = [
        {
            "title": page.title,
            "url": page.url,
            "section": page.section_label,
            "sectionSlug": page.audience,
            "text": page.text[:4000],
        }
        for page in pages
    ]
    payload.insert(
        0,
        {
            "title": "EyeNet Wiki home",
            "url": "/",
            "section": "Home",
            "sectionSlug": "home",
            "text": "EyeNet wiki home what is eyenet features user guide distributors guide owners platform admins installation authority licences",
        },
    )
    (out / "assets" / "search-index.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT)
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS)
    parser.add_argument("--js", type=Path, default=DEFAULT_JS)
    parser.add_argument("--logo", type=Path, default=DEFAULT_LOGO)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv[1:])

    wiki_root: Path = args.wiki_root
    out: Path = args.out
    css: Path = args.css
    js: Path = args.js
    logo: Path = args.logo

    if not wiki_root.is_dir():
        print(f"Wiki root not found: {wiki_root}", file=sys.stderr)
        return 1
    if not css.is_file():
        print(f"CSS not found: {css}", file=sys.stderr)
        return 1
    if not js.is_file():
        print(f"JS not found: {js}", file=sys.stderr)
        return 1
    if not logo.is_file():
        print(f"Logo not found: {logo}", file=sys.stderr)
        return 1

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    assets = out / "assets"
    assets.mkdir()
    shutil.copy2(css, assets / "site.css")
    shutil.copy2(js, assets / "wiki.js")
    shutil.copy2(logo, assets / "eyenet-dark.svg")
    asset_version = file_version(css) + file_version(js)[:4] + file_version(logo)[:4]

    all_pages: list[PageInfo] = []
    versions: dict[str, str] = {}
    for slug, label in SITES:
        src = wiki_root / slug
        if not src.is_dir():
            print(f"Missing site tree: {src}", file=sys.stderr)
            return 1
        pages = collect_site_pages(src, slug, label)
        all_pages.extend(pages)
        versions[slug] = build_site_tree(
            src, out / slug, slug, label, pages, asset_version
        )
        images = copy_site_images(src, out / slug)
        downloads = copy_site_downloads(src, out / slug)
        print(
            f"Built {slug} → {out / slug} "
            f"({len(pages)} pages, {images} images, {downloads} downloads)"
        )

    write_search_index(out, all_pages)
    write_landing(
        out,
        all_pages,
        next((v for v in versions.values() if v), ""),
        asset_version,
    )
    print(f"Landing → {out / 'index.html'}")
    print(f"Search index → {out / 'assets' / 'search-index.json'}")
    print(f"Asset version → {asset_version}")
    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
