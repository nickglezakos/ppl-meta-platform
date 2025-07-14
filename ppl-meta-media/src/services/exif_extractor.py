"""
EXIF metadata extraction service for PPL Meta Platform Media Service.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

logger = logging.getLogger(__name__)


class ExifExtractor:
    """
    Service for extracting and processing EXIF metadata from images.

    Provides comprehensive EXIF data extraction including:
    - Camera settings (ISO, aperture, shutter speed, focal length)
    - GPS coordinates with conversion to decimal degrees
    - Device information (camera make/model)
    - Timestamp extraction from image metadata
    - Privacy controls for sensitive data removal
    """

    def __init__(self, privacy_mode: bool = False):
        """
        Initialize EXIF extractor.

        Args:
            privacy_mode: If True, strips GPS and other sensitive metadata
        """
        self.privacy_mode = privacy_mode
        self.sensitive_tags = {
            "GPS",
            "GPSInfo",
            "GPSLatitude",
            "GPSLongitude",
            "GPSAltitude",
            "GPSTimeStamp",
            "GPSDateStamp",
            "UserComment",
            "ImageDescription",
            "XPComment",
            "XPAuthor",
            "XPKeywords",
            "XPSubject",
            "Copyright",
        }

    def extract_exif_data(self, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive EXIF metadata from an image file.

        Args:
            file_path: Path to the image file

        Returns:
            Dictionary containing structured EXIF metadata
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.warning(f"File not found: {file_path}")
                return {}

            # Check if file is an image
            if not self._is_image_file(file_path_obj):
                logger.debug(f"File is not an image: {file_path}")
                return {}

            with Image.open(file_path) as img:
                exif_data = img._getexif()

                if not exif_data:
                    logger.debug(f"No EXIF data found in: {file_path}")
                    return {}

                # Extract and structure EXIF data
                structured_exif = self._structure_exif_data(exif_data)

                # Apply privacy filters if enabled
                if self.privacy_mode:
                    structured_exif = self._apply_privacy_filter(structured_exif)

                # Add file metadata
                structured_exif["file_info"] = {
                    "file_name": file_path_obj.name,
                    "file_size": file_path_obj.stat().st_size,
                    "file_path": str(file_path_obj),
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                }

                return structured_exif

        except Exception as e:
            logger.error(f"Error extracting EXIF data from {file_path}: {e}")
            return {}

    def _structure_exif_data(self, exif_data: Dict[int, Any]) -> Dict[str, Any]:
        """
        Convert raw EXIF data to structured, human-readable format.

        Args:
            exif_data: Raw EXIF data from PIL

        Returns:
            Structured EXIF metadata dictionary
        """
        structured = {
            "camera_info": {},
            "settings": {},
            "gps_info": {},
            "datetime_info": {},
            "technical_info": {},
            "raw_exif": {},
        }

        for tag_id, value in exif_data.items():
            try:
                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")

                # Store raw data
                structured["raw_exif"][tag_name] = str(value)

                # Categorize and process specific tags
                self._categorize_exif_tag(structured, tag_name, value)

            except Exception as e:
                logger.debug(f"Error processing EXIF tag {tag_id}: {e}")
                continue

        return structured

    def _categorize_exif_tag(
        self, structured: Dict[str, Any], tag_name: str, value: Any
    ) -> None:
        """
        Categorize EXIF tags into logical groups.

        Args:
            structured: The structured EXIF dictionary to populate
            tag_name: Name of the EXIF tag
            value: Value of the EXIF tag
        """
        # Camera information
        if tag_name in ["Make", "Model", "Software", "LensModel", "LensMake"]:
            structured["camera_info"][tag_name] = str(value)

        # Camera settings
        elif tag_name in [
            "ISO",
            "ISOSpeedRatings",
            "FNumber",
            "ExposureTime",
            "FocalLength",
            "Flash",
            "WhiteBalance",
            "ExposureMode",
            "MeteringMode",
            "ExposureProgram",
            "ExposureBiasValue",
        ]:
            structured["settings"][tag_name] = self._process_camera_setting(
                tag_name, value
            )

        # GPS information
        elif tag_name == "GPSInfo":
            structured["gps_info"] = self._process_gps_data(value)

        # DateTime information
        elif tag_name in [
            "DateTime",
            "DateTimeOriginal",
            "DateTimeDigitized",
            "SubSecTime",
            "SubSecTimeOriginal",
            "SubSecTimeDigitized",
        ]:
            structured["datetime_info"][tag_name] = str(value)

        # Technical information
        elif tag_name in [
            "ImageWidth",
            "ImageLength",
            "BitsPerSample",
            "Compression",
            "PhotometricInterpretation",
            "Orientation",
            "SamplesPerPixel",
            "PlanarConfiguration",
            "YCbCrSubSampling",
            "YCbCrPositioning",
            "XResolution",
            "YResolution",
            "ResolutionUnit",
            "ColorSpace",
        ]:
            structured["technical_info"][tag_name] = str(value)

    def _process_camera_setting(self, tag_name: str, value: Any) -> str:
        """
        Process camera setting values to human-readable format.

        Args:
            tag_name: Name of the camera setting tag
            value: Raw value from EXIF

        Returns:
            Processed, human-readable value
        """
        try:
            if tag_name in ["FNumber", "ExposureTime", "FocalLength"]:
                if isinstance(value, tuple) and len(value) == 2:
                    # Handle fractional values
                    numerator, denominator = value
                    if denominator != 0:
                        decimal_value = numerator / denominator
                        if tag_name == "FNumber":
                            return f"f/{decimal_value:.1f}"
                        elif tag_name == "ExposureTime":
                            if decimal_value < 1:
                                return f"1/{int(1/decimal_value)}"
                            else:
                                return f"{decimal_value:.2f}s"
                        elif tag_name == "FocalLength":
                            return f"{decimal_value:.1f}mm"

            return str(value)

        except Exception as e:
            logger.debug(f"Error processing camera setting {tag_name}: {e}")
            return str(value)

    def _process_gps_data(self, gps_data: Dict[int, Any]) -> Dict[str, Any]:
        """
        Process GPS EXIF data and convert to standard format.

        Args:
            gps_data: Raw GPS data from EXIF

        Returns:
            Processed GPS information with decimal coordinates
        """
        gps_info = {}

        try:
            # Convert GPS tag IDs to names
            gps_named = {}
            for gps_tag_id, value in gps_data.items():
                gps_tag_name = GPSTAGS.get(gps_tag_id, f"GPS_{gps_tag_id}")
                gps_named[gps_tag_name] = value
                gps_info[f"raw_{gps_tag_name}"] = str(value)

            # Extract decimal coordinates if available
            coords = self._extract_decimal_coordinates(gps_named)
            if coords:
                gps_info.update(coords)

            # Extract altitude
            altitude = self._extract_altitude(gps_named)
            if altitude is not None:
                gps_info["altitude_meters"] = altitude

            # Extract timestamp
            gps_timestamp = self._extract_gps_timestamp(gps_named)
            if gps_timestamp:
                gps_info["gps_timestamp"] = gps_timestamp

        except Exception as e:
            logger.error(f"Error processing GPS data: {e}")

        return gps_info

    def _extract_decimal_coordinates(
        self, gps_data: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """
        Extract and convert GPS coordinates to decimal degrees.

        Args:
            gps_data: Named GPS data dictionary

        Returns:
            Dictionary with decimal latitude and longitude, or None
        """
        try:
            # Get latitude data
            lat_dms = gps_data.get("GPSLatitude")
            lat_ref = gps_data.get("GPSLatitudeRef")

            # Get longitude data
            lon_dms = gps_data.get("GPSLongitude")
            lon_ref = gps_data.get("GPSLongitudeRef")

            if not all([lat_dms, lat_ref, lon_dms, lon_ref]):
                return None

            # Convert DMS to decimal
            latitude = self._dms_to_decimal(lat_dms, lat_ref)
            longitude = self._dms_to_decimal(lon_dms, lon_ref)

            if latitude is not None and longitude is not None:
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "coordinate_system": "WGS84",
                }

        except Exception as e:
            logger.debug(f"Error extracting decimal coordinates: {e}")

        return None

    def _dms_to_decimal(self, dms_tuple: Tuple, reference: str) -> Optional[float]:
        """
        Convert degrees, minutes, seconds to decimal degrees.

        Args:
            dms_tuple: Tuple of (degrees, minutes, seconds)
            reference: Reference direction (N, S, E, W)

        Returns:
            Decimal degree value or None
        """
        try:
            if not dms_tuple or len(dms_tuple) != 3:
                return None

            degrees, minutes, seconds = dms_tuple

            # Convert fractional values
            if isinstance(degrees, tuple):
                degrees = degrees[0] / degrees[1] if degrees[1] != 0 else 0
            if isinstance(minutes, tuple):
                minutes = minutes[0] / minutes[1] if minutes[1] != 0 else 0
            if isinstance(seconds, tuple):
                seconds = seconds[0] / seconds[1] if seconds[1] != 0 else 0

            decimal = float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0

            # Apply reference direction
            if reference in ["S", "W"]:
                decimal = -decimal

            return decimal

        except Exception as e:
            logger.debug(f"Error converting DMS to decimal: {e}")
            return None

    def _extract_altitude(self, gps_data: Dict[str, Any]) -> Optional[float]:
        """
        Extract altitude from GPS data.

        Args:
            gps_data: Named GPS data dictionary

        Returns:
            Altitude in meters or None
        """
        try:
            altitude_tuple = gps_data.get("GPSAltitude")
            altitude_ref = gps_data.get("GPSAltitudeRef", 0)

            if altitude_tuple and isinstance(altitude_tuple, tuple):
                altitude = (
                    altitude_tuple[0] / altitude_tuple[1]
                    if altitude_tuple[1] != 0
                    else 0
                )

                # Apply reference (0 = above sea level, 1 = below sea level)
                if altitude_ref == 1:
                    altitude = -altitude

                return float(altitude)

        except Exception as e:
            logger.debug(f"Error extracting altitude: {e}")

        return None

    def _extract_gps_timestamp(self, gps_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract GPS timestamp from GPS data.

        Args:
            gps_data: Named GPS data dictionary

        Returns:
            ISO formatted GPS timestamp or None
        """
        try:
            gps_date = gps_data.get("GPSDateStamp")
            gps_time = gps_data.get("GPSTimeStamp")

            if gps_date and gps_time:
                # Parse date (format: "YYYY:MM:DD")
                date_parts = str(gps_date).split(":")
                if len(date_parts) == 3:
                    year, month, day = map(int, date_parts)

                    # Parse time (tuple of hours, minutes, seconds)
                    if isinstance(gps_time, tuple) and len(gps_time) == 3:
                        hour = int(gps_time[0])
                        minute = int(gps_time[1])
                        second = int(gps_time[2])

                        dt = datetime(year, month, day, hour, minute, second)
                        return dt.isoformat() + "Z"  # UTC timestamp

        except Exception as e:
            logger.debug(f"Error extracting GPS timestamp: {e}")

        return None

    def _apply_privacy_filter(self, exif_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive metadata for privacy protection.

        Args:
            exif_data: Structured EXIF data

        Returns:
            Filtered EXIF data with sensitive information removed
        """
        filtered_data = exif_data.copy()

        # Remove GPS information if in privacy mode
        if "gps_info" in filtered_data:
            filtered_data["gps_info"] = {
                "privacy_filtered": True,
                "note": "GPS data removed for privacy protection",
            }

        # Filter raw EXIF data
        if "raw_exif" in filtered_data:
            filtered_raw = {}
            for tag, value in filtered_data["raw_exif"].items():
                if not any(sensitive in tag for sensitive in self.sensitive_tags):
                    filtered_raw[tag] = value
            filtered_data["raw_exif"] = filtered_raw

        return filtered_data

    def _is_image_file(self, file_path: Path) -> bool:
        """
        Check if file is a supported image format.

        Args:
            file_path: Path object for the file

        Returns:
            True if file is a supported image format
        """
        image_extensions = {".jpg", ".jpeg", ".tiff", ".tif"}
        return file_path.suffix.lower() in image_extensions

    def extract_bulk_exif(
        self, media_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract EXIF data from multiple media files.

        Args:
            media_records: List of media records with file paths

        Returns:
            List of media records with EXIF data added
        """
        results = []

        for record in media_records:
            try:
                file_path = record.get("file_path")
                if not file_path:
                    logger.warning("No file_path found in media record")
                    results.append(record)
                    continue

                # Extract EXIF data
                exif_data = self.extract_exif_data(file_path)

                # Add to record
                record_with_exif = record.copy()
                if exif_data:
                    record_with_exif["exif_metadata"] = exif_data
                    logger.info(f"EXIF data extracted for: {file_path}")
                else:
                    record_with_exif["exif_metadata"] = None
                    logger.debug(f"No EXIF data found for: {file_path}")

                results.append(record_with_exif)

            except Exception as e:
                logger.error(f"Error processing media record: {e}")
                results.append(record)

        return results

    def get_summary_stats(self, exif_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics from EXIF data.

        Args:
            exif_data: Structured EXIF data

        Returns:
            Summary statistics dictionary
        """
        stats = {
            "has_camera_info": bool(exif_data.get("camera_info")),
            "has_gps_data": bool(exif_data.get("gps_info", {}).get("latitude")),
            "has_datetime": bool(exif_data.get("datetime_info")),
            "camera_make": exif_data.get("camera_info", {}).get("Make"),
            "camera_model": exif_data.get("camera_info", {}).get("Model"),
            "focal_length": exif_data.get("settings", {}).get("FocalLength"),
            "iso": exif_data.get("settings", {}).get("ISO"),
            "aperture": exif_data.get("settings", {}).get("FNumber"),
            "exposure_time": exif_data.get("settings", {}).get("ExposureTime"),
            "total_tags": len(exif_data.get("raw_exif", {})),
        }

        return stats
