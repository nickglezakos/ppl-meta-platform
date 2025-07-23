#!/usr/bin/env python3
"""
Test script to debug video metadata endpoint issue
"""
import os
import sys

sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src")

from models.media import Media, MediaType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://postgres:devpassword@localhost:5433/ppl_meta_media"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_video_metadata():
    """Test video metadata retrieval"""
    media_id = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
    user_guid = "4cf362b1-3e05-4e85-81c7-c08a98c7e41b"

    db = SessionLocal()
    try:
        print(f"Testing media ID: {media_id}")
        print(f"User GUID: {user_guid}")
        print("-" * 50)

        # Test without user filter
        print("1. Query without user filter:")
        query = db.query(Media).filter(Media.uuid == media_id)
        media = query.first()

        if media:
            print(f"   ✅ Media found!")
            print(f"   Media type: {media.media_type}")
            print(f"   Uploaded by: {media.uploaded_by}")
            print(f"   Has technical_metadata: {media.technical_metadata is not None}")

            if media.technical_metadata:
                print(f"   Metadata keys: {list(media.technical_metadata.keys())}")
                print(
                    f"   Has video_properties: {'video_properties' in media.technical_metadata}"
                )

                if "video_properties" in media.technical_metadata:
                    video_props = media.technical_metadata["video_properties"]
                    print(f"   Video properties: {video_props}")
            else:
                print("   ❌ No technical_metadata")
        else:
            print("   ❌ No media found")

        print()

        # Test with user filter
        print("2. Query with user filter:")
        query_with_user = db.query(Media).filter(
            Media.uuid == media_id, Media.uploaded_by == user_guid
        )
        media_with_user = query_with_user.first()

        if media_with_user:
            print("   ✅ Media found with user filter!")
        else:
            print("   ❌ No media found with user filter")
            if media:
                print(f"   Expected user: {user_guid}")
                print(f"   Actual user: {media.uploaded_by}")
                print(f"   Match: {str(media.uploaded_by) == user_guid}")

    finally:
        db.close()


if __name__ == "__main__":
    test_video_metadata()
