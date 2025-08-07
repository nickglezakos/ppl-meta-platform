#!/usr/bin/env python3
"""
Test script to update existing video with extracted metadata.
This simulates what should happen during upload.
"""

import sys
import os
import asyncio
import json
import psycopg2


# Test updating the technical_metadata for the existing video
async def update_video_metadata():
    """Update the existing video with extracted metadata."""

    # The metadata we just extracted
    metadata = {
        "video_properties": {
            "extraction_timestamp": "2025-07-23T00:00:00Z",
            "extraction_methods_used": ["ffprobe"],
            "total_frames": 381,
            "frame_count_source": "ffprobe_exact",
            "frame_count_confidence": "high",
            "width": 1080,
            "height": 1920,
            "duration_seconds": 12.833333,
            "fps": 30.0,
            "codec": "h264",
            "pixel_format": "yuvj420p",
            "bit_rate": 5220844,
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        }
    }

    # Database connection parameters
    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_meta_platform",
        "user": "postgres",
        "password": "postgres",
    }

    video_uuid = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"

    try:
        # Connect to database
        print("🔗 Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Get current technical_metadata
        cursor.execute(
            "SELECT technical_metadata FROM media_items WHERE uuid = %s", (video_uuid,)
        )
        result = cursor.fetchone()

        if not result:
            print(f"❌ Video {video_uuid} not found in database")
            return

        current_metadata = result[0] or {}
        print(f"📋 Current metadata keys: {list(current_metadata.keys())}")

        # Merge with new video properties
        updated_metadata = {**current_metadata, **metadata}

        # Update database
        cursor.execute(
            "UPDATE media_items SET technical_metadata = %s WHERE uuid = %s",
            (json.dumps(updated_metadata), video_uuid),
        )

        conn.commit()
        print(f"✅ Updated video {video_uuid} with video properties")
        print(f"📊 New metadata includes: {list(updated_metadata.keys())}")

        cursor.close()
        conn.close()

        print("\n🧪 Now test the API endpoint...")

    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(update_video_metadata())
