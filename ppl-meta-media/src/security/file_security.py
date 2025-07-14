"""
File Security Service for PPL Meta Media Service.
Provides file type validation, magic number verification, and malware scanning.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Tuple

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


class FileSecurityService:
    """
    Comprehensive file security service for validating and scanning uploads.
    """

    # File signatures (magic numbers) for common file types
    FILE_SIGNATURES = {
        # Images
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a": "image/png",
        b"\x47\x49\x46\x38": "image/gif",
        b"\x00\x00\x01\x00": "image/x-icon",
        b"\x42\x4d": "image/bmp",
        # Videos
        b"\x00\x00\x00\x18\x66\x74\x79\x70": "video/mp4",
        b"\x00\x00\x00\x20\x66\x74\x79\x70": "video/mp4",
        b"\x1a\x45\xdf\xa3": "video/webm",
        b"\x46\x4c\x56": "video/x-flv",
        b"\x00\x00\x01\xba": "video/mpeg",
        b"\x00\x00\x01\xb3": "video/mpeg",
        # Audio
        b"\x49\x44\x33": "audio/mpeg",  # MP3 with ID3
        b"\xff\xfb": "audio/mpeg",  # MP3
        b"\xff\xf3": "audio/mpeg",  # MP3
        b"\xff\xf2": "audio/mpeg",  # MP3
        b"\x4f\x67\x67\x53": "audio/ogg",
        b"\x66\x4c\x61\x43": "audio/flac",
        # Documents
        b"\x25\x50\x44\x46": "application/pdf",
        b"\x50\x4b\x03\x04": "application/zip",  # Also DOCX, XLSX, etc.
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "application/msword",
    }

    # Special RIFF file handling (WebP, WAV share same signature)
    RIFF_SIGNATURE = b"\x52\x49\x46\x46"

    # Allowed MIME types for media files
    ALLOWED_MIME_TYPES = {
        # Images
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/x-icon",
        "image/svg+xml",
        # Videos
        "video/mp4",
        "video/mpeg",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
        "video/x-flv",
        "video/3gpp",
        "video/x-ms-wmv",
        # Audio
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
        "audio/flac",
        "audio/aac",
        "audio/mp4",
        "audio/x-m4a",
        "audio/webm",
        "audio/x-wav",
    }

    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        "image": 50 * 1024 * 1024,  # 50MB for images
        "video": 500 * 1024 * 1024,  # 500MB for videos
        "audio": 100 * 1024 * 1024,  # 100MB for audio
    }

    def __init__(self, enable_malware_scanning: bool = True):
        """
        Initialize the File Security Service.

        Args:
            enable_malware_scanning: Whether to enable malware scanning with ClamAV
        """
        self.enable_malware_scanning = enable_malware_scanning
        self._check_malware_scanner()

    def _check_malware_scanner(self) -> bool:
        """Check if ClamAV is available for malware scanning."""
        if not self.enable_malware_scanning:
            return False

        try:
            result = subprocess.run(
                ["clamdscan", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info("ClamAV malware scanner available")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            result = subprocess.run(
                ["clamscan", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info("ClamAV command-line scanner available")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        logger.warning("ClamAV not available - malware scanning disabled")
        self.enable_malware_scanning = False
        return False

    def validate_file_signature(self, file_content: bytes) -> Tuple[bool, str]:
        """
        Validate file using magic number (file signature).

        Args:
            file_content: First few bytes of the file

        Returns:
            Tuple of (is_valid, detected_mime_type)
        """
        if len(file_content) < 8:
            return False, "File too small to validate"

        # Special handling for RIFF files (WebP, WAV)
        if file_content.startswith(self.RIFF_SIGNATURE):
            if len(file_content) >= 12:
                # Check WebP
                if file_content[8:12] == b"WEBP":
                    return True, "image/webp"
                # Check WAV
                elif file_content[8:12] == b"WAVE":
                    return True, "audio/wav"
            return False, "Unknown RIFF file type"

        # Check each known signature
        for signature, mime_type in self.FILE_SIGNATURES.items():
            if file_content.startswith(signature):
                return True, mime_type

        return False, "Unknown file signature"

    def validate_mime_type(self, mime_type: str) -> bool:
        """
        Validate if MIME type is allowed.

        Args:
            mime_type: MIME type to validate

        Returns:
            True if MIME type is allowed
        """
        return mime_type.lower() in self.ALLOWED_MIME_TYPES

    def validate_file_size(self, file_size: int, file_type: str) -> bool:
        """
        Validate file size against limits.

        Args:
            file_size: Size of file in bytes
            file_type: Type of file (image, video, audio)

        Returns:
            True if file size is within limits
        """
        max_size = self.MAX_FILE_SIZES.get(file_type.lower())
        if max_size is None:
            # Default limit for unknown types
            max_size = 100 * 1024 * 1024  # 100MB

        return file_size <= max_size

    def scan_for_malware(self, file_path: Path) -> Tuple[bool, str]:
        """
        Scan file for malware using ClamAV.

        Args:
            file_path: Path to file to scan

        Returns:
            Tuple of (is_clean, scan_result)
        """
        if not self.enable_malware_scanning:
            return True, "Malware scanning disabled"

        try:
            # Try clamdscan first (daemon mode - faster)
            result = subprocess.run(
                ["clamdscan", "--no-summary", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, "Clean"
            elif result.returncode == 1:
                return False, f"Malware detected: {result.stdout.strip()}"
            else:
                # Fallback to clamscan
                result = subprocess.run(
                    ["clamscan", "--no-summary", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    return True, "Clean"
                elif result.returncode == 1:
                    return False, f"Malware detected: {result.stdout.strip()}"
                else:
                    logger.error(f"ClamAV scan error: {result.stderr}")
                    return True, "Scan failed - allowing file"

        except subprocess.TimeoutExpired:
            logger.error("Malware scan timeout")
            return True, "Scan timeout - allowing file"
        except Exception as e:
            logger.error(f"Malware scan error: {e}")
            return True, "Scan error - allowing file"

    async def validate_upload_file(self, file: UploadFile) -> Dict[str, any]:
        """
        Comprehensive validation of uploaded file.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Dictionary with validation results

        Raises:
            HTTPException: If file fails security validation
        """
        validation_result = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": 0,
            "signature_valid": False,
            "mime_type_valid": False,
            "size_valid": False,
            "malware_scan_clean": False,
            "security_passed": False,
            "errors": [],
        }

        try:
            # Read file content for validation
            content = await file.read()
            validation_result["size"] = len(content)

            # Reset file position
            await file.seek(0)

            # 1. Validate file signature (magic numbers)
            signature_valid, detected_mime = self.validate_file_signature(content[:32])
            validation_result["signature_valid"] = signature_valid
            validation_result["detected_mime_type"] = detected_mime

            if not signature_valid:
                validation_result["errors"].append(
                    f"Invalid file signature: {detected_mime}"
                )

            # 2. Validate MIME type
            declared_mime = file.content_type or ""
            mime_valid = self.validate_mime_type(declared_mime)
            validation_result["mime_type_valid"] = mime_valid

            if not mime_valid:
                validation_result["errors"].append(
                    f"MIME type not allowed: {declared_mime}"
                )

            # 3. Cross-check declared vs detected MIME type
            if signature_valid and mime_valid:
                if not self._mime_types_compatible(declared_mime, detected_mime):
                    validation_result["errors"].append(
                        f"MIME type mismatch: declared {declared_mime}, "
                        f"detected {detected_mime}"
                    )

            # 4. Validate file size
            file_category = self._get_file_category(declared_mime)
            size_valid = self.validate_file_size(
                validation_result["size"], file_category
            )
            validation_result["size_valid"] = size_valid

            if not size_valid:
                max_size = self.MAX_FILE_SIZES.get(file_category, 0)
                validation_result["errors"].append(
                    f"File too large: {validation_result['size']} bytes "
                    f"(max: {max_size} bytes)"
                )

            # 5. Malware scanning (if file passes other checks)
            if signature_valid and mime_valid and size_valid:
                # Save temporary file for scanning
                temp_path = Path(f"/tmp/scan_{file.filename}")
                try:
                    with open(temp_path, "wb") as temp_file:
                        temp_file.write(content)

                    scan_clean, scan_result = self.scan_for_malware(temp_path)
                    validation_result["malware_scan_clean"] = scan_clean
                    validation_result["scan_result"] = scan_result

                    if not scan_clean:
                        validation_result["errors"].append(
                            f"Malware detected: {scan_result}"
                        )
                finally:
                    # Clean up temporary file
                    if temp_path.exists():
                        temp_path.unlink()
            else:
                validation_result["malware_scan_clean"] = False
                validation_result["errors"].append(
                    "Skipped malware scan due to other failures"
                )

            # Overall security check
            validation_result["security_passed"] = (
                signature_valid
                and mime_valid
                and size_valid
                and validation_result["malware_scan_clean"]
            )

            # Reset file position for upload processing
            await file.seek(0)

            # Raise exception if validation failed
            if not validation_result["security_passed"]:
                error_msg = "; ".join(validation_result["errors"])
                raise HTTPException(
                    status_code=400,
                    detail=f"File security validation failed: {error_msg}",
                )

            return validation_result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File validation error: {e}")
            raise HTTPException(
                status_code=500, detail="File validation failed due to internal error"
            )

    def _mime_types_compatible(self, declared: str, detected: str) -> bool:
        """Check if declared and detected MIME types are compatible."""
        # Normalize MIME types
        declared = declared.lower().strip()
        detected = detected.lower().strip()

        # Exact match
        if declared == detected:
            return True

        # Handle common aliases
        aliases = {
            "image/jpg": "image/jpeg",
            "audio/mp3": "audio/mpeg",
            "video/x-msvideo": "video/avi",
        }

        declared = aliases.get(declared, declared)
        detected = aliases.get(detected, detected)

        return declared == detected

    def _get_file_category(self, mime_type: str) -> str:
        """Get file category from MIME type."""
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
        elif mime_type.startswith("audio/"):
            return "audio"
        else:
            return "other"
