#!/usr/bin/env python3
"""Cap media_kit Linux SW texture size for RPi stability.

Default clamp is 1920x1080 (landscape-only). Raising to 4096x4096 allowed
correct portrait aspect but made 4K S/W textures that lag and segfault.

Use 1280x1280: enough for downscaled portrait (~720x1280) and landscape
(~1280x720) after the vf=scale patch, without 4K framebuffers.
"""
from __future__ import annotations

import pathlib
import sys

TARGETS = (
    """#define SW_RENDERING_MAX_WIDTH 1920
#define SW_RENDERING_MAX_HEIGHT 1080""",
    """#define SW_RENDERING_MAX_WIDTH 4096
#define SW_RENDERING_MAX_HEIGHT 4096""",
)

NEW = """#define SW_RENDERING_MAX_WIDTH 1280
#define SW_RENDERING_MAX_HEIGHT 1280"""


def main() -> int:
    pub = pathlib.Path("/root/.pub-cache/hosted/pub.dev")
    if not pub.exists():
        pub = pathlib.Path.home() / ".pub-cache/hosted/pub.dev"
    matches = sorted(pub.glob("media_kit_video-*/linux/include/media_kit_video/texture_sw.h"))
    if not matches:
        print("ERROR: texture_sw.h not found under", pub, file=sys.stderr)
        return 1
    path = matches[-1]
    text = path.read_text()
    if "SW_RENDERING_MAX_WIDTH 1280" in text and "SW_RENDERING_MAX_HEIGHT 1280" in text:
        print("already patched (1280x1280):", path)
        return 0
    for old in TARGETS:
        if old in text:
            path.write_text(text.replace(old, NEW, 1))
            print("patched SW limits -> 1280x1280:", path)
            return 0
    print("ERROR: expected SW_RENDERING_MAX defines not found in", path, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
