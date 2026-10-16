"""
Decoder-safe video variants for signage players.

Signage tablets such as the Lenovo TB330FU (Helio G88) reject files whose
frame size or H.264 level exceeds the hardware decoder, with
``format_supported=NO_EXCEEDS_CAPABILITIES``. This module serves those files
as H.264 Baseline, 8-bit 4:2:0, inside a 1920x1080 box at 30 fps.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SIGNAGE_MAX_WIDTH = 1920
SIGNAGE_MAX_HEIGHT = 1080
SIGNAGE_MAX_FPS = 30.5
SIGNAGE_MAX_H264_LEVEL = 40  # level 4.0, the 1080p30 limit
_SAFE_PROFILES = frozenset({"baseline", "constrained baseline", "main", "high"})
_CACHE_DIR = Path("/tmp/ppl-meta-media-android-compat")
_locks_guard = threading.Lock()
_media_locks: dict[str, threading.Lock] = {}


def _parse_frame_rate(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text or text == "0/0":
        return 0.0
    if "/" in text:
        num, den = text.split("/", 1)
        try:
            den_f = float(den)
            if den_f == 0:
                return 0.0
            return float(num) / den_f
        except ValueError:
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def signage_stream_needs_transcode(stream: Optional[dict]) -> bool:
    """Return True when a probed video stream is outside signage decoder limits.

    ``None`` means probing failed. Callers keep the original file in that case
    rather than guessing.
    """
    if not stream:
        return False

    codec = str(stream.get("codec_name") or "").lower()
    if codec != "h264":
        return True

    profile = str(stream.get("profile") or "").lower()
    if profile not in _SAFE_PROFILES:
        return True

    if str(stream.get("pix_fmt") or "").lower() != "yuv420p":
        return True

    try:
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
    except (TypeError, ValueError):
        return True
    if width <= 0 or height <= 0 or width > SIGNAGE_MAX_WIDTH or height > SIGNAGE_MAX_HEIGHT:
        return True

    try:
        level = int(stream.get("level") or 0)
    except (TypeError, ValueError):
        level = 0
    if level > SIGNAGE_MAX_H264_LEVEL:
        return True

    fps = _parse_frame_rate(stream.get("avg_frame_rate"))
    if fps > SIGNAGE_MAX_FPS:
        return True

    return False


def _resolve_binary(name: str) -> Optional[str]:
    for candidate in (
        shutil.which(name),
        f"/usr/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/opt/homebrew/bin/{name}",
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _probe_primary_video_stream(path: Path) -> Optional[dict]:
    ffprobe = _resolve_binary("ffprobe")
    if not ffprobe:
        logger.warning("ffprobe not found; serving original signage file %s", path)
        return None

    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,profile,width,height,pix_fmt,level,avg_frame_rate",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffprobe failed for %s: %s", path, exc)
        return None

    if result.returncode != 0:
        logger.warning("ffprobe rejected %s: %s", path, (result.stderr or "").strip()[-400:])
        return None

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        logger.warning("ffprobe returned non-JSON for %s", path)
        return None

    streams = payload.get("streams") or []
    if not streams:
        return None
    return streams[0]


def _lock_for(media_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _media_locks.get(media_id)
        if lock is None:
            lock = threading.Lock()
            _media_locks[media_id] = lock
        return lock


def _transcode(original_path: Path, media_id: str) -> Path:
    ffmpeg = _resolve_binary("ffmpeg")
    if not ffmpeg:
        logger.error("ffmpeg not found; serving original signage file for %s", media_id)
        return original_path

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _CACHE_DIR / f"{media_id}_signage_1080_v1.mp4"
    if output_path.exists() and output_path.stat().st_mtime >= original_path.stat().st_mtime:
        logger.info("Using cached signage variant %s", output_path)
        return output_path

    # Fit inside 1920x1080 without upscaling. Even dimensions are required for yuv420p.
    scale = (
        "scale="
        "'min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,"
        "fps=30"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(original_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-profile:v",
        "baseline",
        "-level",
        "4.0",
        "-pix_fmt",
        "yuv420p",
        "-x264-params",
        "cabac=0:ref=1:bframes=0:weightp=0",
        "-vf",
        scale,
        "-b:v",
        "2500k",
        "-maxrate",
        "3000k",
        "-bufsize",
        "6000k",
        "-g",
        "60",
        "-c:a",
        "aac",
        "-ac",
        "2",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    logger.info("Transcoding %s to a signage-safe 1080p variant", media_id)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Signage transcode failed for %s: %s", media_id, exc)
        return original_path

    if result.returncode != 0 or not output_path.exists():
        logger.error(
            "Signage transcode failed for %s (code %s): %s",
            media_id,
            result.returncode,
            (result.stderr or "")[-800:],
        )
        return original_path

    logger.info(
        "Signage variant ready for %s at %s (%s bytes)",
        media_id,
        output_path,
        output_path.stat().st_size,
    )
    return output_path


def get_signage_playable_file(original_path: Path, media_id: str) -> Path:
    """Return ``original_path`` or a cached decoder-safe MP4 for signage playback."""
    with _lock_for(str(media_id)):
        stream = _probe_primary_video_stream(original_path)
        if not signage_stream_needs_transcode(stream):
            return original_path
        logger.info(
            "Signage source %s exceeds decoder limits (codec=%s %sx%s profile=%s level=%s); transcoding",
            media_id,
            stream.get("codec_name") if stream else None,
            stream.get("width") if stream else None,
            stream.get("height") if stream else None,
            stream.get("profile") if stream else None,
            stream.get("level") if stream else None,
        )
        return _transcode(original_path, str(media_id))
