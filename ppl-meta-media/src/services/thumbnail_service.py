"""
Thumbnail generation service for PPL Meta Platform Media Service.
"""

import subprocess
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps

try:
    import magic
except ImportError:
    magic = None

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False


class ThumbnailService:
    """Service for generating thumbnails for media files."""

    # Standard thumbnail sizes
    THUMBNAIL_SIZES = {
        "small": (150, 150),
        "medium": (300, 300),
        "large": (600, 600),
    }

    def __init__(self, storage_root: str, redis_url: Optional[str] = None):
        """Initialize thumbnail service with storage root path and Redis."""
        self.storage_root = Path(storage_root)
        self.thumbnail_cache_dir = self.storage_root / "thumbnails"
        self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Redis cache if available and URL provided
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)  # type: ignore
                # Test connection
                self.redis_client.ping()
            except Exception:
                self.redis_client = None

    def generate_thumbnail(
        self,
        file_path: str,
        size: str = "medium",
        force_regenerate: bool = False,
        video_timestamp: Optional[str] = None,
        video_position: str = "start",
    ) -> Optional[bytes]:
        """
        Generate thumbnail for media file.

        Args:
            file_path: Path to the original media file
            size: Thumbnail size (small, medium, large)
            force_regenerate: Force regeneration even if cached exists
            video_timestamp: Custom timestamp for video thumbnails (e.g., "00:02:30")
            video_position: Video position for thumbnail ("start", "middle", "end")

        Returns:
            Thumbnail image bytes or None if generation failed
        """
        if size not in self.THUMBNAIL_SIZES:
            size = "medium"

        thumbnail_size = self.THUMBNAIL_SIZES[size]
        file_path_obj = Path(file_path)

        # Check if file exists
        if not file_path_obj.exists():
            return None

        # Generate cache filename with position/timestamp info for videos
        cache_suffix = ""
        if video_timestamp:
            cache_suffix = f"_{video_timestamp.replace(':', '')}"
        elif video_position != "start":
            cache_suffix = f"_{video_position}"

        cache_filename = f"{file_path_obj.stem}_{size}{cache_suffix}.jpg"
        cache_path = self.thumbnail_cache_dir / cache_filename

        # Check Redis cache first if available
        redis_key = None
        if self.redis_client:
            redis_key = f"thumbnail:{file_path}:{size}:{video_position}:{video_timestamp or 'none'}"
            if not force_regenerate:
                try:
                    cached_data = self.redis_client.get(redis_key)
                    if cached_data:
                        return cached_data
                except Exception:
                    pass  # Continue with file generation if Redis fails

        # Return cached thumbnail if exists and not forcing regeneration
        if cache_path.exists() and not force_regenerate:
            try:
                with open(cache_path, "rb") as f:
                    thumbnail_data = f.read()
                    # Also cache in Redis if available
                    if self.redis_client and redis_key:
                        try:
                            # Cache for 24 hours
                            self.redis_client.setex(redis_key, 86400, thumbnail_data)
                        except Exception:
                            pass
                    return thumbnail_data
            except Exception:
                pass  # Continue to regenerate

        # Detect file type
        try:
            if magic:
                mime_type = magic.from_file(str(file_path_obj), mime=True)
            else:
                mime_type = self._get_mime_type_from_extension(file_path_obj.suffix)
        except (OSError, IOError):
            # Fallback to extension-based detection
            mime_type = self._get_mime_type_from_extension(file_path_obj.suffix)

        thumbnail_bytes = None

        if mime_type.startswith("image/"):
            thumbnail_bytes = self._generate_image_thumbnail(
                file_path_obj, thumbnail_size
            )
        elif mime_type.startswith("video/"):
            thumbnail_bytes = self._generate_video_thumbnail(
                file_path_obj, thumbnail_size, video_timestamp, video_position
            )

        # Cache the generated thumbnail (both file and Redis)
        if thumbnail_bytes:
            try:
                # File-based caching
                with open(cache_path, "wb") as f:
                    f.write(thumbnail_bytes)

                # Redis caching if available
                if self.redis_client and redis_key:
                    try:
                        # Cache for 24 hours
                        self.redis_client.setex(redis_key, 86400, thumbnail_bytes)
                    except Exception:
                        pass  # Continue even if Redis caching fails

            except (OSError, IOError):
                pass  # Continue even if file caching fails

        return thumbnail_bytes

    def _generate_image_thumbnail(
        self, file_path: Path, size: Tuple[int, int]
    ) -> Optional[bytes]:
        """Generate thumbnail for image files using Pillow."""
        try:
            with Image.open(file_path) as img:
                # Fix image orientation if needed
                img = ImageOps.exif_transpose(img)

                # Convert to RGB if necessary (for PNG with transparency, etc.)
                if img.mode in ("RGBA", "LA", "P"):
                    # Create white background
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1]
                    )  # Use alpha channel as mask
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Create thumbnail maintaining aspect ratio
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save to bytes
                thumbnail_io = BytesIO()
                img.save(thumbnail_io, format="JPEG", quality=85, optimize=True)
                return thumbnail_io.getvalue()

        except (OSError, IOError, Image.UnidentifiedImageError) as e:
            print(f"Error generating image thumbnail for {file_path}: {e}")
            return None

    def _generate_video_thumbnail(
        self,
        file_path: Path,
        size: Tuple[int, int],
        video_timestamp: Optional[str] = None,
        video_position: str = "start",
    ) -> Optional[bytes]:
        """Generate thumbnail for video files using ffmpeg."""
        try:
            # Create temporary output file
            temp_output = self.thumbnail_cache_dir / (f"temp_{file_path.stem}.jpg")

            # Determine timestamp for thumbnail extraction
            seek_time = "00:00:01"  # Default: 1 second from start

            if video_timestamp:
                # Use custom timestamp if provided
                seek_time = video_timestamp
            elif video_position == "middle":
                # For middle position, we need to get video duration first
                duration_cmd = [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "csv=p=0",
                    str(file_path),
                ]
                try:
                    duration_result = subprocess.run(
                        duration_cmd, capture_output=True, text=True, timeout=10
                    )
                    if duration_result.returncode == 0:
                        duration = float(duration_result.stdout.strip())
                        middle_seconds = duration / 2
                        hours = int(middle_seconds // 3600)
                        minutes = int((middle_seconds % 3600) // 60)
                        seconds = int(middle_seconds % 60)
                        seek_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except (subprocess.TimeoutExpired, ValueError):
                    # Fall back to default if duration detection fails
                    seek_time = "00:00:05"
            elif video_position == "end":
                # For end position, seek to 10 seconds before end (or 30 seconds)
                seek_time = "00:00:30"

            # Use ffmpeg to extract frame at specified time
            scale_filter = (
                f"scale={size[0]}:{size[1]}:" "force_original_aspect_ratio=decrease"
            )
            cmd = [
                "ffmpeg",
                "-i",
                str(file_path),
                "-ss",
                seek_time,
                "-vframes",
                "1",  # Extract 1 frame
                "-vf",
                scale_filter,
                "-y",  # Overwrite output file
                str(temp_output),
            ]

            # Run ffmpeg command
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )

            if result.returncode == 0 and temp_output.exists():
                # Read the generated thumbnail
                with open(temp_output, "rb") as f:
                    thumbnail_bytes = f.read()

                # Clean up temporary file
                temp_output.unlink()

                return thumbnail_bytes
            else:
                print(f"ffmpeg error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"ffmpeg timeout for {file_path}")
            return None
        except (OSError, IOError) as e:
            print(f"Error generating video thumbnail for {file_path}: {e}")
            return None

    def _get_mime_type_from_extension(self, extension: str) -> str:
        """Get MIME type from file extension as fallback."""
        extension = extension.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".wmv": "video/x-ms-wmv",
            ".flv": "video/x-flv",
            ".webm": "video/webm",
            ".mkv": "video/x-matroska",
        }
        return mime_types.get(extension, "application/octet-stream")

    def clear_cache(self) -> int:
        """
        Clear all cached thumbnails.

        Returns:
            Number of files deleted
        """
        deleted_count = 0
        try:
            for thumbnail_file in self.thumbnail_cache_dir.glob("*.jpg"):
                thumbnail_file.unlink()
                deleted_count += 1
        except Exception as e:
            print(f"Error clearing thumbnail cache: {e}")

        return deleted_count

    def get_cache_size(self) -> int:
        """
        Get total size of thumbnail cache in bytes.

        Returns:
            Cache size in bytes
        """
        total_size = 0
        try:
            for thumbnail_file in self.thumbnail_cache_dir.glob("*.jpg"):
                total_size += thumbnail_file.stat().st_size
        except Exception:
            pass

        return total_size

    def generate_thumbnails_on_upload(self, file_path: str) -> dict:
        """
        Generate all thumbnail sizes automatically on file upload.

        Args:
            file_path: Path to the uploaded media file

        Returns:
            Dictionary with generation results for each size
        """
        results = {}

        for size_name in self.THUMBNAIL_SIZES.keys():
            try:
                thumbnail_bytes = self.generate_thumbnail(file_path, size=size_name)
                results[size_name] = {
                    "success": thumbnail_bytes is not None,
                    "size_bytes": len(thumbnail_bytes) if thumbnail_bytes else 0,
                }
            except Exception as e:
                results[size_name] = {"success": False, "error": str(e)}

        return results

    def clear_cache_for_file(self, file_path: str) -> int:
        """
        Clear all cached thumbnails for a specific file.

        Args:
            file_path: Path to the media file

        Returns:
            Number of cache entries cleared
        """
        cleared_count = 0
        file_stem = Path(file_path).stem

        # Clear file-based cache
        try:
            for thumbnail_file in self.thumbnail_cache_dir.glob(f"{file_stem}_*.jpg"):
                thumbnail_file.unlink()
                cleared_count += 1
        except Exception:
            pass

        # Clear Redis cache if available
        if self.redis_client:
            try:
                # Get all keys for this file
                pattern = f"thumbnail:{file_path}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    cleared_count += len(keys)
            except Exception:
                pass

        return cleared_count

    def get_default_video_thumbnail(self, size: str = "medium") -> Optional[bytes]:
        """
        Generate a default video thumbnail for when thumbnail generation fails.

        Args:
            size: Thumbnail size (small, medium, large)

        Returns:
            Default thumbnail as bytes, or None if unable to create
        """
        try:
            # Define size dimensions
            size_map = {"small": (160, 120), "medium": (320, 240), "large": (640, 480)}

            width, height = size_map.get(size, size_map["medium"])

            # Create a simple dark gray image with a play icon
            try:
                from PIL import ImageDraw
            except ImportError:
                # PIL not available, return None
                return None

            # Create base image with dark gray background
            img = Image.new("RGB", (width, height), color="#2d2d2d")
            draw = ImageDraw.Draw(img)

            # Draw a simple play button in the center
            center_x, center_y = width // 2, height // 2
            play_size = min(width, height) // 6

            # Calculate triangle points for play button
            triangle = [
                (center_x - play_size // 2, center_y - play_size // 2),
                (center_x + play_size // 2, center_y),
                (center_x - play_size // 2, center_y + play_size // 2),
            ]

            # Draw play button
            draw.polygon(triangle, fill="#ffffff", outline="#cccccc")

            # Add text indicating it's a video thumbnail
            try:
                # Try to add small text
                text = "Video"
                text_bbox = draw.textbbox((0, 0), text)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (width - text_width) // 2
                text_y = center_y + play_size

                if text_y + text_height < height - 10:
                    draw.text((text_x, text_y), text, fill="#cccccc")
            except Exception:  # pylint: disable=broad-except
                # Font handling might fail, continue without text
                pass

            # Convert to JPEG bytes
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return buffer.getvalue()

        except Exception as e:  # pylint: disable=broad-except
            print(f"Error creating default video thumbnail: {e}")
            return None
