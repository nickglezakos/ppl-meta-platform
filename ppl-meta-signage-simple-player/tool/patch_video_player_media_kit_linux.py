#!/usr/bin/env python3
"""Patch video_player_media_kit for Raspberry Pi / Linux Docker.

Default media_kit VideoController.create() sets hwdec=auto, which on RPi
tries VDPAU (libvdpau_nvidia) and never produces video-out-params. The
Flutter texture then stays at the intentional 1x1 placeholder forever.

Also: full-res 4K portrait S/W textures (2160x4096) cause lag, window
overflow painting, and segfaults on dispose/create. Force:
  - hwdec=no + enableHardwareAcceleration=false + vo=libmpv
  - mpv vf scale down into a 1280x1280 box (keep aspect)
  - VideoController output size capped at 720x1280 (portrait-friendly)

Flutter BoxFit.cover then fills the window from a small, stable texture.
"""
from __future__ import annotations

import pathlib
import sys

OLD = """    final player = Player();
    final completer = Completer();
    final videoController = VideoController(player);"""

NEW = """    final player = Player();
    final completer = Completer();
    // RPi / Linux Docker: software decode + downscaled texture.
    // VideoController.create() defaults hwdec to 'auto' (VDPAU on Linux).
    // Cap decode/output ~720p-class so 4K portrait does not OOM/segfault.
    try {
      await (player.platform as dynamic).setProperty(
        'vf',
        'lavfi=[scale=w=1280:h=1280:force_original_aspect_ratio=decrease]',
      );
    } catch (_) {}
    final videoController = VideoController(
      player,
      configuration: const VideoControllerConfiguration(
        vo: 'libmpv',
        hwdec: 'no',
        enableHardwareAcceleration: false,
        width: 720,
        height: 1280,
      ),
    );"""

# Prior "strong" patch without downscale / with or without pinned 1080p.
OLD_STRONG_NO_SIZE = """    final player = Player();
    final completer = Completer();
    // RPi / Linux Docker: CPU textures + software decode.
    // VideoController.create() defaults hwdec to 'auto' (VDPAU on Linux),
    // which overwrites any earlier setProperty('hwdec','no').
    // Do not pin width/height — portrait assets must keep their aspect.
    final videoController = VideoController(
      player,
      configuration: const VideoControllerConfiguration(
        vo: 'libmpv',
        hwdec: 'no',
        enableHardwareAcceleration: false,
      ),
    );"""

OLD_PINNED_1080 = """    final player = Player();
    final completer = Completer();
    // RPi / Linux Docker: CPU textures + software decode.
    // VideoController.create() defaults hwdec to 'auto' (VDPAU on Linux),
    // which overwrites any earlier setProperty('hwdec','no').
    final videoController = VideoController(
      player,
      configuration: const VideoControllerConfiguration(
        vo: 'libmpv',
        hwdec: 'no',
        enableHardwareAcceleration: false,
        width: 1920,
        height: 1080,
      ),
    );"""

OLD_PARTIAL = """    final player = Player();
    final completer = Completer();
    // RPi / Linux Docker: CPU textures (GPU path yields 1x1 black frames).
    // Also force software decode via native setProperty when available.
    try {
      await (player.platform as dynamic).setProperty('hwdec', 'no');
    } catch (_) {}
    final videoController = VideoController(
      player,
      configuration: const VideoControllerConfiguration(
        enableHardwareAcceleration: false,
      ),
    );"""


def main() -> int:
    pub = pathlib.Path("/root/.pub-cache/hosted/pub.dev")
    if not pub.exists():
        home = pathlib.Path.home() / ".pub-cache/hosted/pub.dev"
        pub = home
    matches = sorted(pub.glob("video_player_media_kit-*/lib/src/media_kit_video_player.dart"))
    if not matches:
        print("ERROR: video_player_media_kit source not found under", pub, file=sys.stderr)
        return 1
    path = matches[-1]
    text = path.read_text()
    if "scale=w=1280:h=1280" in text and "width: 720" in text and "height: 1280" in text:
        print("already patched (downscale 720x1280):", path)
        return 0
    for label, old in (
        ("strong-no-size", OLD_STRONG_NO_SIZE),
        ("pinned-1080", OLD_PINNED_1080),
        ("partial", OLD_PARTIAL),
        ("stock", OLD),
    ):
        if old in text:
            path.write_text(text.replace(old, NEW, 1))
            print(f"patched ({label}):", path)
            return 0
    print("ERROR: expected Player()/VideoController block not found in", path, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
