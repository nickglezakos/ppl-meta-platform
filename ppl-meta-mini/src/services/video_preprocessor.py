"""
Video preprocessing service for Mini service.
Lightweight video processing to improve face detection accuracy.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VideoPreprocessor:
    """Lightweight video preprocessing to improve face detection."""

    def __init__(self):
        """Initialize video preprocessor."""
        temp_base = Path(tempfile.gettempdir())
        self.temp_dir = temp_base / "ppl_mini_video_processing"
        self.temp_dir.mkdir(exist_ok=True)

    def preprocess_video_for_detection(self, video_path: str) -> Optional[str]:
        """
        Preprocess video to improve face detection accuracy.

        This applies minimal processing that can improve face detection:
        - Ensures proper encoding
        - Optimizes for frame extraction
        - Maintains original quality

        Args:
            video_path: Path to the original video file

        Returns:
            Path to preprocessed video or None if preprocessing failed
        """
        try:
            input_path = Path(video_path)
            if not input_path.exists():
                logger.error(f"Input video not found: {video_path}")
                return None

            # Create temporary output file
            output_path = self.temp_dir / f"preprocessed_{input_path.stem}.mp4"

            # AGGRESSIVE ffmpeg optimization to match Media service compression
            # Based on analysis: 33MB → 8.6MB compression improves face detection
            cmd = [
                "ffmpeg",
                "-i",
                str(input_path),
                "-c:v",
                "libx264",  # Use H.264 codec
                "-preset",
                "medium",  # Better compression than "fast"
                "-crf",
                "28",  # More aggressive compression (was 23)
                "-maxrate",
                "2M",  # Limit bitrate for better compression
                "-bufsize",
                "4M",  # Buffer size for rate control
                "-vf",
                "scale=-2:min(1080\\,ih)",  # Scale down if > 1080p
                "-c:a",
                "aac",  # Audio codec
                "-b:a",
                "128k",  # Lower audio bitrate
                "-movflags",
                "+faststart",  # Optimize for streaming
                "-y",  # Overwrite output
                str(output_path),
            ]

            logger.info(f"Preprocessing video: {input_path.name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False,
            )

            if result.returncode == 0 and output_path.exists():
                file_size_original = input_path.stat().st_size
                file_size_processed = output_path.stat().st_size

                logger.info(
                    f"Video preprocessing successful: "
                    f"{input_path.name} ({file_size_original:,} bytes) -> "
                    f"{output_path.name} ({file_size_processed:,} bytes)"
                )
                return str(output_path)
            else:
                logger.error(f"ffmpeg failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Video preprocessing timeout: {video_path}")
            return None
        except Exception as e:
            logger.error(f"Video preprocessing error: {e}")
            return None

    def get_video_info(self, video_path: str) -> Optional[dict]:
        """
        Get basic video information using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video information or None if failed
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=True
            )

            import json

            return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None

    def cleanup_processed_files(self):
        """Clean up temporary processed files."""
        try:
            for file_path in self.temp_dir.glob("preprocessed_*"):
                file_path.unlink()
                logger.debug(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def should_preprocess(self, video_path: str) -> bool:
        """
        Determine if video should be preprocessed based on characteristics.

        UPDATED: Now more aggressive to match Media service optimization.
        We force preprocessing for better face detection results.

        Args:
            video_path: Path to video file

        Returns:
            True if preprocessing is recommended
        """
        try:
            video_info = self.get_video_info(video_path)
            if not video_info:
                return True  # If we can't get info, try preprocessing

            # Check video streams
            video_streams = [
                stream
                for stream in video_info.get("streams", [])
                if stream.get("codec_type") == "video"
            ]

            if not video_streams:
                return False

            video_stream = video_streams[0]
            codec_name = video_stream.get("codec_name", "").lower()
            file_size = video_info.get("format", {}).get("size", "0")

            # Get file size in MB
            file_size_mb = int(file_size) / (1024 * 1024) if file_size.isdigit() else 0

            # AGGRESSIVE PREPROCESSING STRATEGY:
            # Based on Media service analysis, preprocessing improves face detection
            # Force preprocessing if:
            # 1. File is larger than 5MB (more aggressive threshold)
            # 2. Any resolution above 480p (lower threshold)
            # 3. Not using optimal encoding settings
            # 4. File seems unoptimized for face detection

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            needs_preprocessing = (
                file_size_mb > 5  # Much lower threshold: 5MB
                or width > 640  # Lower resolution threshold
                or height > 480  # Even 480p+ gets preprocessing
                or codec_name not in ["h264", "avc"]  # Ensure H.264
                or file_size_mb > 15  # Definitely preprocess large files
            )

            logger.info(
                f"Video analysis: codec={codec_name}, "
                f"resolution={video_stream.get('width')}x"
                f"{video_stream.get('height')}, "
                f"file_size={file_size_mb:.1f}MB, "
                f"needs_preprocessing={needs_preprocessing}"
            )

            return needs_preprocessing

        except Exception as e:
            logger.error(f"Error checking if preprocessing needed: {e}")
            return True  # Default to preprocessing if uncertain
