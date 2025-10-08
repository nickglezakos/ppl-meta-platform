#!/usr/bin/env python3
"""
Fix cached video metadata for existing media entries.

This script re-processes video metadata for media that has "video_error": "Video file not found"
in their technical_metadata, now that we've fixed the storage path configuration.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the media service to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ppl-meta-media", "src"))

from database import get_db
from models.media import Media, MediaType
from services.media_service import MediaService


async def fix_video_metadata():
    """Fix video metadata for all media with video_error."""

    print("🔧 Starting video metadata fix...")

    # Get database session
    db = next(get_db())
    media_service = MediaService(db)

    try:
        # Find all video media with video_error in technical_metadata
        # Only process completed videos to avoid interfering with active uploads
        from models.media import ProcessingStatus

        videos_with_errors = []
        all_media = (
            db.query(Media)
            .filter(
                Media.media_type == MediaType.VIDEO,
                Media.processing_status == ProcessingStatus.COMPLETED,
            )
            .all()
        )

        for media in all_media:
            if (
                media.technical_metadata
                and isinstance(media.technical_metadata, dict)
                and media.technical_metadata.get("video_error")
            ):
                videos_with_errors.append(media)

        print(f"📊 Found {len(videos_with_errors)} videos with video_error")

        if not videos_with_errors:
            print("✅ No videos need metadata refresh")
            return

        # Re-process each video
        for i, media in enumerate(videos_with_errors, 1):
            print(
                f"\n🎬 Processing {i}/{len(videos_with_errors)}: {media.original_filename}"
            )
            print(f"   UUID: {media.uuid}")
            print(f"   Current error: {media.technical_metadata.get('video_error')}")

            try:
                # Clear the error from technical_metadata
                if "video_error" in media.technical_metadata:
                    del media.technical_metadata["video_error"]

                # Re-extract video metadata with corrected storage path
                await media_service._extract_video_metadata(media)

                # Commit the changes
                db.commit()

                # Check if error was resolved
                if media.technical_metadata.get("video_error"):
                    print(
                        f"   ❌ Still has error: {media.technical_metadata.get('video_error')}"
                    )
                else:
                    video_data = media.technical_metadata.get("video", {})
                    total_frames = video_data.get("total_frames")
                    print(f"   ✅ Fixed! Total frames: {total_frames}")

            except Exception as e:
                print(f"   ❌ Failed to process: {e}")
                # Rollback this media's changes
                db.rollback()

            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)

        print(f"\n🎉 Video metadata fix complete!")

    except Exception as e:
        print(f"❌ Error during metadata fix: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(fix_video_metadata())
