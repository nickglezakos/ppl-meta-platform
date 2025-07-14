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


class ThumbnailService:
    """Service for generating thumbnails for media files."""

    # Standard thumbnail sizes
    THUMBNAIL_SIZES = {
        "small": (150, 150),
        "medium": (300, 300),
        "large": (600, 600),
    }

    def __init__(self, storage_root: str):
        """Initialize thumbnail service with storage root path."""
        self.storage_root = Path(storage_root)
        self.thumbnail_cache_dir = self.storage_root / "thumbnails"
        self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_thumbnail(
        self, file_path: str, size: str = "medium", force_regenerate: bool = False
    ) -> Optional[bytes]:
        """
        Generate thumbnail for media file.

        Args:
            file_path: Path to the original media file
            size: Thumbnail size (small, medium, large)
            force_regenerate: Force regeneration even if cached exists

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

        # Generate cache filename
        cache_filename = f"{file_path_obj.stem}_{size}.jpg"
        cache_path = self.thumbnail_cache_dir / cache_filename

        # Return cached thumbnail if exists and not forcing regeneration
        if cache_path.exists() and not force_regenerate:
            try:
                with open(cache_path, "rb") as f:
                    return f.read()
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
                file_path_obj, thumbnail_size
            )

        # Cache the generated thumbnail
        if thumbnail_bytes:
            try:
                with open(cache_path, "wb") as f:
                    f.write(thumbnail_bytes)
            except (OSError, IOError):
                pass  # Continue even if caching fails

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
        self, file_path: Path, size: Tuple[int, int]
    ) -> Optional[bytes]:
        """Generate thumbnail for video files using ffmpeg."""
        try:
            # Create temporary output file
            temp_output = self.thumbnail_cache_dir / (f"temp_{file_path.stem}.jpg")

            # Use ffmpeg to extract first frame
            scale_filter = (
                f"scale={size[0]}:{size[1]}:" "force_original_aspect_ratio=decrease"
            )
            cmd = [
                "ffmpeg",
                "-i",
                str(file_path),
                "-ss",
                "00:00:01",  # Seek to 1 second
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
