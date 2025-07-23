"""
Video Metadata Extractor for PPL Meta Platform Media Service.

Extracts comprehensive video metadata including exact frame count using
ffprobe.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import cv2


class VideoMetadataExtractor:
    """Extract comprehensive video metadata using ffprobe and OpenCV."""

    def __init__(self):
        """Initialize the video metadata extractor."""
        self.ffprobe_available = self._check_ffprobe_availability()

    def _check_ffprobe_availability(self) -> bool:
        """Check if ffprobe is available on the system."""
        try:
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    async def extract_video_metadata(
        self, video_content: bytes, filename: str
    ) -> Dict[str, Any]:
        """
        Extract comprehensive video metadata from video content.

        Args:
            video_content: Raw video file bytes
            filename: Original filename for context

        Returns:
            Dictionary containing video metadata including exact frame count
        """

        # Create temporary file for processing
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(video_content)
            temp_path = temp_file.name

        try:
            metadata = {}

            # Method 1: Use ffprobe (most accurate and comprehensive)
            if self.ffprobe_available:
                ffprobe_metadata = await self._extract_with_ffprobe(temp_path)
                metadata.update(ffprobe_metadata)
            else:
                ffprobe_metadata = {}

            # Method 2: Use OpenCV as fallback/validation
            opencv_metadata = await self._extract_with_opencv(temp_path)
            metadata.update(opencv_metadata)

            # Method 3: Cross-validation and fallback logic
            final_metadata = self._consolidate_metadata(
                ffprobe_metadata, opencv_metadata
            )

            return final_metadata

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def _extract_with_ffprobe(self, video_path: str) -> Dict[str, Any]:
        """Extract metadata using ffprobe (most accurate method)."""
        try:
            # Get general video information
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            ffprobe_data = json.loads(result.stdout)

            # Find video stream
            video_stream = None
            for stream in ffprobe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break

            if not video_stream:
                return {"ffprobe_error": "No video stream found"}

            # Extract exact frame count using ffprobe frame counting
            frame_count = await self._get_exact_frame_count_ffprobe(video_path)

            # Parse frame rate safely
            fps = 0.0
            r_frame_rate = video_stream.get("r_frame_rate", "0/1")
            if "/" in r_frame_rate:
                num, denom = r_frame_rate.split("/")
                if denom != "0":
                    fps = float(num) / float(denom)

            # Parse average frame rate safely
            avg_fps = 0.0
            avg_frame_rate = video_stream.get("avg_frame_rate", "0/1")
            if "/" in avg_frame_rate:
                num, denom = avg_frame_rate.split("/")
                if denom != "0":
                    avg_fps = float(num) / float(denom)

            metadata = {
                "extraction_method": "ffprobe",
                "total_frames": frame_count,
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "duration_seconds": float(video_stream.get("duration", 0)),
                "fps": fps,
                "avg_fps": avg_fps,
                "codec": video_stream.get("codec_name"),
                "pixel_format": video_stream.get("pix_fmt"),
                "bit_rate": (
                    int(video_stream.get("bit_rate", 0))
                    if video_stream.get("bit_rate")
                    else None
                ),
                "format_name": ffprobe_data.get("format", {}).get("format_name"),
                "file_size": int(ffprobe_data.get("format", {}).get("size", 0)),
                "ffprobe_raw": ffprobe_data,  # Store full ffprobe output
            }

            return metadata

        except subprocess.CalledProcessError as e:
            return {"ffprobe_error": f"ffprobe failed: {e}"}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return {"ffprobe_error": f"ffprobe extraction error: {e}"}

    async def _get_exact_frame_count_ffprobe(self, video_path: str) -> Optional[int]:
        """Get exact frame count using ffprobe frame counting."""
        try:
            # Method 1: Try to get nb_frames from stream info (fastest)
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count_frames",
                "-show_entries",
                "stream=nb_frames",
                "-of",
                "csv=p=0",
                video_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            frame_count_str = result.stdout.strip()

            if frame_count_str and frame_count_str.isdigit():
                return int(frame_count_str)

            # Method 2: Fallback - count packets (slower but accurate)
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count_packets",
                "-show_entries",
                "stream=nb_read_packets",
                "-of",
                "csv=p=0",
                video_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            packet_count_str = result.stdout.strip()

            if packet_count_str and packet_count_str.isdigit():
                return int(packet_count_str)

            return None

        except subprocess.CalledProcessError:
            return None

    async def _extract_with_opencv(self, video_path: str) -> Dict[str, Any]:
        """Extract metadata using OpenCV (fallback method)."""
        try:
            cap = cv2.VideoCapture(video_path)  # type: ignore

            if not cap.isOpened():
                return {"opencv_error": "Failed to open video with OpenCV"}

            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # type: ignore
            fps = cap.get(cv2.CAP_PROP_FPS)  # type: ignore
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # type: ignore
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # type: ignore

            # Calculate duration
            duration_seconds = total_frames / fps if fps > 0 else 0

            cap.release()

            metadata = {
                "extraction_method_fallback": "opencv",
                "total_frames_opencv": total_frames,
                "width_opencv": width,
                "height_opencv": height,
                "fps_opencv": fps,
                "duration_seconds_opencv": duration_seconds,
            }

            return metadata

        except (cv2.error, ValueError, OSError) as e:  # type: ignore
            return {"opencv_error": f"OpenCV extraction error: {e}"}

    def _consolidate_metadata(self, ffprobe: Dict, opencv: Dict) -> Dict[str, Any]:
        """
        Consolidate metadata from multiple sources with fallback logic.

        Priority: ffprobe > opencv > time-based calculation
        """

        final_metadata = {
            "extraction_timestamp": "2025-07-23T00:00:00Z",
            "extraction_methods_used": [],
        }

        # Determine most reliable frame count
        total_frames = None
        frame_count_source = "none"

        # Priority 1: ffprobe exact count
        if (
            "total_frames" in ffprobe
            and ffprobe["total_frames"]
            and ffprobe["total_frames"] > 0
        ):
            total_frames = ffprobe["total_frames"]
            frame_count_source = "ffprobe_exact"
            final_metadata["extraction_methods_used"].append("ffprobe")

        # Priority 2: OpenCV frame count
        elif "total_frames_opencv" in opencv and opencv["total_frames_opencv"] > 0:
            total_frames = opencv["total_frames_opencv"]
            frame_count_source = "opencv"
            final_metadata["extraction_methods_used"].append("opencv")

        # Priority 3: Calculate from duration and fps (fallback)
        elif "duration_seconds" in ffprobe and "fps" in ffprobe and ffprobe["fps"] > 0:
            total_frames = int(ffprobe["duration_seconds"] * ffprobe["fps"])
            frame_count_source = "calculated_ffprobe"
            final_metadata["extraction_methods_used"].append("calculated")

        elif (
            "duration_seconds_opencv" in opencv
            and "fps_opencv" in opencv
            and opencv["fps_opencv"] > 0
        ):
            calculated_frames = int(
                opencv["duration_seconds_opencv"] * opencv["fps_opencv"]
            )
            total_frames = calculated_frames
            frame_count_source = "calculated_opencv"
            final_metadata["extraction_methods_used"].append("calculated_opencv")

        # Store final frame count
        final_metadata["total_frames"] = total_frames
        final_metadata["frame_count_source"] = frame_count_source

        confidence = (
            "high"
            if frame_count_source.startswith("ffprobe")
            else ("medium" if frame_count_source == "opencv" else "low")
        )
        final_metadata["frame_count_confidence"] = confidence

        # Consolidate other metadata (prefer ffprobe values)
        metadata_keys = [
            "width",
            "height",
            "duration_seconds",
            "fps",
            "codec",
            "pixel_format",
            "bit_rate",
            "format_name",
        ]

        for key in metadata_keys:
            if key in ffprobe and ffprobe[key] is not None:
                final_metadata[key] = ffprobe[key]
            elif f"{key}_opencv" in opencv and opencv[f"{key}_opencv"] is not None:
                final_metadata[key] = opencv[f"{key}_opencv"]

        # Store source metadata for debugging
        final_metadata["ffprobe_metadata"] = ffprobe
        final_metadata["opencv_metadata"] = opencv

        return final_metadata

    async def get_frame_at_position(
        self, video_content: bytes, frame_number: int
    ) -> Optional[bytes]:
        """
        Extract a specific frame from video for validation purposes.

        Args:
            video_content: Raw video file bytes
            frame_number: Frame number to extract (0-based)

        Returns:
            JPEG bytes of the extracted frame, or None if failed
        """

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(video_content)
            temp_path = temp_file.name

        try:
            cap = cv2.VideoCapture(temp_path)  # type: ignore

            if not cap.isOpened():
                return None

            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)  # type: ignore
            ret, frame = cap.read()

            if not ret:
                return None

            # Encode frame as JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]  # type: ignore
            success, encoded = cv2.imencode(".jpg", frame, encode_params)  # type: ignore
            cap.release()

            if success:
                return encoded.tobytes()

            return None

        except (cv2.error, ValueError, OSError):  # type: ignore
            return None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
