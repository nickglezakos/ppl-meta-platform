#!/usr/bin/env python3
"""Validate software_ref frontmatter on EyeNet wiki markdown pages."""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_TOP_KEYS = {"platform_version", "policy_revision", "channels_documented", "install_path"}
REQUIRED_CHANNELS = {"sandbox", "pilot", "stable"}


def extract_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter starting with ---")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("missing closing --- for YAML frontmatter")
    block = text[4:end]
    data: dict[str, object] = {}
    current_list_key: str | None = None
    software_ref: dict[str, object] | None = None
    in_software_ref = False

    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("software_ref:"):
            software_ref = {}
            data["software_ref"] = software_ref
            in_software_ref = True
            current_list_key = None
            continue
        if in_software_ref and line.startswith("  ") and not line.startswith("    "):
            # nested under software_ref
            assert software_ref is not None
            stripped = line.strip()
            if stripped.startswith("- "):
                if current_list_key is None:
                    raise ValueError(f"list item without key: {line}")
                values = software_ref.setdefault(current_list_key, [])
                if not isinstance(values, list):
                    raise ValueError(f"{current_list_key} is not a list")
                values.append(stripped[2:].strip().strip('"').strip("'"))
                continue
            if ":" not in stripped:
                raise ValueError(f"invalid software_ref line: {line}")
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                current_list_key = key
                software_ref[key] = []
            else:
                current_list_key = None
                software_ref[key] = value.strip('"').strip("'")
            continue
        if in_software_ref and line.startswith("    "):
            assert software_ref is not None
            stripped = line.strip()
            if stripped.startswith("- "):
                if current_list_key is None:
                    raise ValueError(f"list item without key: {line}")
                values = software_ref.setdefault(current_list_key, [])
                if not isinstance(values, list):
                    raise ValueError(f"{current_list_key} is not a list")
                values.append(stripped[2:].strip().strip('"').strip("'"))
                continue
        # top-level keys after software_ref or before
        if ":" in line and not line.startswith(" "):
            in_software_ref = False
            current_list_key = None
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")

    if "software_ref" not in data or not isinstance(data["software_ref"], dict):
        raise ValueError("software_ref mapping is required")
    return data


def validate_page(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    data = extract_frontmatter(text)
    ref = data["software_ref"]
    assert isinstance(ref, dict)
    missing = REQUIRED_TOP_KEYS - set(ref)
    if missing:
        raise ValueError(f"software_ref missing keys: {sorted(missing)}")
    channels = ref.get("channels_documented")
    if not isinstance(channels, list) or not channels:
        raise ValueError("channels_documented must be a non-empty list")
    missing_channels = REQUIRED_CHANNELS - set(channels)
    if missing_channels:
        raise ValueError(f"channels_documented missing: {sorted(missing_channels)}")
    if not str(ref.get("platform_version", "")).strip():
        raise ValueError("platform_version must be non-empty")
    if not str(ref.get("policy_revision", "")).strip():
        raise ValueError("policy_revision must be non-empty")
    if str(ref.get("install_path")) != "windows-docker-desktop-ghcr":
        raise ValueError("install_path must be windows-docker-desktop-ghcr for this revamp")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <wiki-site-directory>", file=sys.stderr)
        return 2
    root = Path(argv[1])
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2
    pages = sorted(root.rglob("*.md"))
    if not pages:
        print(f"No markdown pages under {root}", file=sys.stderr)
        return 1
    failures = 0
    for page in pages:
        try:
            validate_page(page)
            print(f"OK  {page}")
        except Exception as exc:  # noqa: BLE001 - report all page errors
            failures += 1
            print(f"FAIL {page}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
