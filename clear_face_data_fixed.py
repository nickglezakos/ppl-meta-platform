#!/usr/bin/env python3
"""
Clear face detection data and re-scan video metadata for PostgreSQL databases.
This script will:
1. Clear all face detection records from vision service PostgreSQL database
2. Reset media face counts to 0 in media service PostgreSQL database
3. Set has_stored_faces to false for specific media
4. Update target media with fresh processing status
5. Re-scan video metadata (fps, frame_count) using VideoMetadataExtractor after face data clearing
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import asyncpg
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configurations
DATABASES = {
    "ppl_meta_platform": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_meta_platform",
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
    "ppl_media_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_media_db",
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
    "ppl_vision_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_vision_db",
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
}

# Target media ID
TARGET_MEDIA_ID = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"


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

    async def extract_video_metadata_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive video metadata from video file path.

        Args:
            file_path: Path to video file

        Returns:
            Dictionary containing video metadata including exact frame count
        """
        try:
            metadata = {}

            # Method 1: Use ffprobe (most accurate and comprehensive)
            if self.ffprobe_available:
                ffprobe_metadata = await self._extract_with_ffprobe(file_path)
                metadata.update(ffprobe_metadata)
            else:
                ffprobe_metadata = {}

            # Method 2: Use OpenCV as fallback/validation
            opencv_metadata = await self._extract_with_opencv(file_path)
            metadata.update(opencv_metadata)

            # Method 3: Cross-validation and fallback logic
            final_metadata = self._consolidate_metadata(
                ffprobe_metadata, opencv_metadata
            )

            return final_metadata

        except Exception as e:
            logger.error(f"Error extracting video metadata: {e}")
            return {}

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

            metadata = {
                "extraction_method": "ffprobe",
                "total_frames": frame_count,
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "duration_seconds": float(video_stream.get("duration", 0)),
                "fps": fps,
                "codec": video_stream.get("codec_name"),
            }

            return metadata

        except subprocess.CalledProcessError as e:
            return {"ffprobe_error": f"ffprobe failed: {e}"}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return {"ffprobe_error": f"ffprobe extraction error: {e}"}

    async def _get_exact_frame_count_ffprobe(self, video_path: str) -> Optional[int]:
        """Get exact frame count using ffprobe frame counting."""
        try:
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

            return None

        except subprocess.CalledProcessError:
            return None

    async def _extract_with_opencv(self, video_path: str) -> Dict[str, Any]:
        """Extract metadata using OpenCV (fallback method)."""
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                return {"opencv_error": "Failed to open video with OpenCV"}

            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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

        except (cv2.error, ValueError, OSError) as e:
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
        metadata_keys = ["width", "height", "duration_seconds", "fps", "codec"]

        for key in metadata_keys:
            if key in ffprobe and ffprobe[key] is not None:
                final_metadata[key] = ffprobe[key]
            elif f"{key}_opencv" in opencv and opencv[f"{key}_opencv"] is not None:
                final_metadata[key] = opencv[f"{key}_opencv"]

        return final_metadata


async def clear_face_data():
    """Clear all face detection data from PostgreSQL databases."""

    print("🧹 PPL Meta Platform - PostgreSQL Face Data Cleanup Script")
    print("=" * 60)

    for db_name, config in DATABASES.items():
        print(f"\n🔌 Connecting to PostgreSQL database: {db_name}...")

        try:
            conn = await asyncpg.connect(**config)

            # List all tables to see what exists
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            )

            table_names = [t["table_name"] for t in tables]
            print(f"📊 Tables in {db_name}: {table_names}")

            if db_name == "ppl_media_db":
                # Clear face-related data from media service
                await clear_media_face_data(conn)
            elif db_name == "ppl_vision_db":
                # Clear vision service face detection data
                await clear_vision_face_data(conn)
            else:
                # Check for any face/vision tables in other databases
                face_tables = [t for t in table_names if "face" in t.lower()]
                if face_tables:
                    print(f"🔍 Found face tables: {face_tables}")
                    for table in face_tables:
                        count_q = f"SELECT COUNT(*) FROM {table}"
                        count = await conn.fetchval(count_q)
                        if count > 0:
                            await conn.execute(f"DELETE FROM {table}")
                            print(f"✅ Cleared {count} records from {table}")
                        else:
                            print(f"ℹ️  Table {table} is already empty")

            await conn.close()
            print(f"✅ Completed cleanup for {db_name}")

        except asyncpg.exceptions.InvalidCatalogNameError:
            print(f"⚠️  Database {db_name} does not exist - skipping")
        except asyncpg.PostgresConnectionError as e:
            print(f"❌ Connection failed for {db_name}: {e}")
        except asyncpg.PostgresError as e:
            print(f"❌ PostgreSQL error with {db_name}: {e}")
        except Exception as e:
            print(f"❌ Unexpected error with {db_name}: {e}")
            continue


async def clear_vision_face_data(conn):
    """Clear face detection data from vision service PostgreSQL database."""

    print("🎯 Clearing vision service face detection data...")

    # Clear face detections table
    face_count = await conn.fetchval("SELECT COUNT(*) FROM face_detections")
    if face_count > 0:
        await conn.execute("DELETE FROM face_detections")
        print(f"✅ Cleared {face_count} face detection records")
    else:
        print("ℹ️  No face detection records to clear")

    # Clear media records table
    media_count = await conn.fetchval("SELECT COUNT(*) FROM media_records")
    if media_count > 0:
        await conn.execute("DELETE FROM media_records")
        print(f"✅ Cleared {media_count} media records")
    else:
        print("ℹ️  No media records to clear")

    # Reset sequences if they exist
    try:
        await conn.execute("SELECT setval('face_detections_id_seq', 1, false)")
        await conn.execute("SELECT setval('media_records_id_seq', 1, false)")
        print("✅ Reset PostgreSQL sequences")
    except asyncpg.UndefinedTableError:
        print("ℹ️  No sequences to reset (using TEXT IDs)")

    print("🎯 Vision service cleanup completed")


async def clear_media_face_data(conn):
    """Clear face detection data from media service PostgreSQL database."""

    print("🎯 Clearing media service face-related data...")

    # Check if media table exists and has face-related columns
    tables = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
    )
    table_names = [t["table_name"] for t in tables]
    print(f"📊 Available tables: {table_names}")

    # Try both possible table names
    media_table = None
    if "media" in table_names:
        media_table = "media"
    elif "media_items" in table_names:
        media_table = "media_items"
    else:
        print("⚠️  No media table found - skipping media cleanup")
        return

    print(f"📋 Using media table: {media_table}")

    columns = await conn.fetch(
        f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{media_table}' AND table_schema = 'public'
        ORDER BY column_name
        """
    )

    column_names = [c["column_name"] for c in columns]
    print(f"📋 {media_table} table columns: {column_names}")

    # Look for face-related columns
    face_columns = [col for col in column_names if "face" in col.lower()]

    if face_columns:
        print(f"🎯 Found face-related columns: {face_columns}")

        # Reset face data for target media specifically
        if "total_faces" in face_columns:
            result = await conn.execute(
                f"""
                UPDATE {media_table}
                SET total_faces = 0
                WHERE uuid = $1
                """,
                TARGET_MEDIA_ID,
            )
            print(f"✅ Reset total_faces for {TARGET_MEDIA_ID}: {result}")

        if "has_stored_faces" in face_columns:
            result = await conn.execute(
                f"""
                UPDATE {media_table}
                SET has_stored_faces = false
                WHERE uuid = $1
                """,
                TARGET_MEDIA_ID,
            )
            print(f"✅ Reset has_stored_faces for {TARGET_MEDIA_ID}: {result}")

        # Update processing status to allow re-processing
        if "processing_status" in column_names:
            result = await conn.execute(
                f"""
                UPDATE {media_table}
                SET processing_status = 'pending'
                WHERE uuid = $1
                """,
                TARGET_MEDIA_ID,
            )
            print(f"✅ Reset processing_status for {TARGET_MEDIA_ID}: {result}")
    else:
        print("ℹ️  No face-related columns found in media table")

    # Re-scan video metadata for the target video after clearing face data
    await rescan_video_metadata(conn, media_table, TARGET_MEDIA_ID)

    print("🎯 Media service cleanup completed")


async def rescan_video_metadata(conn, media_table: str, target_media_id: str):
    """
    Re-scan video metadata for the target video using VideoMetadataExtractor.
    """
    print("🎬 Re-scanning video metadata after face data cleanup...")

    # Get video file path for target media
    video_query = f"""
        SELECT file_path, original_filename, mime_type
        FROM {media_table}
        WHERE uuid = $1 AND mime_type LIKE 'video/%'
    """

    video_record = await conn.fetchrow(video_query, target_media_id)

    if not video_record:
        print(f"⚠️  No video file found for media {target_media_id}")
        return

    # Determine the full video file path
    video_file_path = None
    storage_base = "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media"

    if video_record["file_path"]:
        # Try file_path
        if os.path.exists(video_record["file_path"]):
            video_file_path = video_record["file_path"]
        else:
            # Try relative to storage base
            potential_path = os.path.join(storage_base, video_record["file_path"])
            if os.path.exists(potential_path):
                video_file_path = potential_path
            else:
                # Try with storage/ prefix
                storage_path = os.path.join(
                    storage_base, "storage", video_record["file_path"]
                )
                if os.path.exists(storage_path):
                    video_file_path = storage_path

    if not video_file_path:
        print(f"❌ Video file not found for {target_media_id}")
        print(f"   Tried: {video_record['file_path']}")
        return

    print(f"📁 Found video file: {video_file_path}")

    # Extract video metadata using VideoMetadataExtractor
    extractor = VideoMetadataExtractor()
    video_metadata = await extractor.extract_video_metadata_from_file(video_file_path)

    if not video_metadata or "total_frames" not in video_metadata:
        print("❌ Failed to extract video metadata")
        return

    print(f"📊 Extracted metadata:")
    print(f"   Total frames: {video_metadata.get('total_frames')}")
    print(f"   FPS: {video_metadata.get('fps')}")
    print(f"   Duration: {video_metadata.get('duration_seconds')} seconds")
    print(
        f"   Resolution: {video_metadata.get('width')}x{video_metadata.get('height')}"
    )
    print(f"   Source: {video_metadata.get('frame_count_source')}")
    print(f"   Confidence: {video_metadata.get('frame_count_confidence')}")

    # Get current technical_metadata
    current_metadata = await conn.fetchval(
        f"SELECT technical_metadata FROM {media_table} WHERE uuid = $1",
        target_media_id,
    )

    if current_metadata is None:
        current_metadata = {}
    elif isinstance(current_metadata, str):
        # Parse JSON string to dict
        import json

        current_metadata = json.loads(current_metadata)
    elif not isinstance(current_metadata, dict):
        current_metadata = {}

    # Add video_properties to technical_metadata
    current_metadata["video_properties"] = video_metadata

    # Update the database
    result = await conn.execute(
        f"""
        UPDATE {media_table}
        SET technical_metadata = $1
        WHERE uuid = $2
        """,
        json.dumps(current_metadata),  # Convert back to JSON string
        target_media_id,
    )

    print(f"✅ Updated video metadata in database: {result}")
    print("🎬 Video metadata re-scan completed successfully")


async def rescan_all_videos_metadata(conn, media_table: str):
    """
    Re-scan video metadata for ALL video files in the database.
    """
    print("🎬 Re-scanning video metadata for ALL videos...")

    # Get all video records
    videos_query = f"""
        SELECT uuid, file_path, original_filename, mime_type
        FROM {media_table}
        WHERE mime_type LIKE 'video/%'
        ORDER BY created_at DESC
        LIMIT 10
    """

    video_records = await conn.fetch(videos_query)

    if not video_records:
        print("ℹ️  No video files found in database")
        return

    print(f"📊 Found {len(video_records)} video files to process")

    storage_base = "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media"
    extractor = VideoMetadataExtractor()
    updated_count = 0

    for record in video_records:
        media_id = record["uuid"]
        print(f"\n🎯 Processing video: {media_id}")

        # Determine the full video file path
        video_file_path = None

        if record["file_path"]:
            if os.path.exists(record["file_path"]):
                video_file_path = record["file_path"]
            else:
                potential_path = os.path.join(storage_base, record["file_path"])
                if os.path.exists(potential_path):
                    video_file_path = potential_path

        if not video_file_path:
            print(f"⚠️  Video file not found for {media_id}")
            continue

        # Extract video metadata
        video_metadata = await extractor.extract_video_metadata_from_file(
            video_file_path
        )

        if not video_metadata or "total_frames" not in video_metadata:
            print(f"❌ Failed to extract metadata for {media_id}")
            continue

        # Update database
        current_metadata = await conn.fetchval(
            f"SELECT technical_metadata FROM {media_table} WHERE uuid = $1",
            media_id,
        )

        if current_metadata is None:
            current_metadata = {}
        elif isinstance(current_metadata, str):
            # Parse JSON string to dict
            import json

            current_metadata = json.loads(current_metadata)
        elif not isinstance(current_metadata, dict):
            current_metadata = {}

        current_metadata["video_properties"] = video_metadata

        await conn.execute(
            f"""
            UPDATE {media_table}
            SET technical_metadata = $1
            WHERE uuid = $2
            """,
            json.dumps(current_metadata),  # Convert back to JSON string
            media_id,
        )

        print(f"✅ Updated {media_id}: {video_metadata.get('total_frames')} frames")
        updated_count += 1

    print(f"\n🎉 Successfully updated metadata for {updated_count} videos")


async def main():
    """Main function to clear face detection data from PostgreSQL databases."""
    print("🚀 Starting PostgreSQL Face Data Cleanup...")
    print(f"🎯 Target Media ID: {TARGET_MEDIA_ID}")
    print("")

    await clear_face_data()

    print("\n🎉 PostgreSQL Face data cleanup and video metadata re-scan completed!")
    print("=" * 60)
    print("📝 Summary:")
    print("  • Vision service face detections cleared")
    print("  • Media service face counts reset")
    print("  • Target media processing status reset to 'pending'")
    print("  • All media face flags reset")
    print("  • Video metadata re-scanned using VideoMetadataExtractor")
    print("  • Fresh metadata with exact frame counts available")
    print("")
    print("✅ You can now test:")
    print("  1. Face detection with exact frame counts from fresh metadata")
    print("  2. Progressive pre-loading with backend metadata")
    print("  3. Zero preprocessing delays with stored metadata")
    print("🌐 Frontend available at: http://localhost:3000")
    print("🔍 Vision service health: http://localhost:8003/health")
    print("📊 Media service health: http://localhost:8000/health")


if __name__ == "__main__":
    asyncio.run(main())
