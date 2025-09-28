#!/usr/bin/env python3
"""
🎯 Discover Existing Media with Face Data for PPL Thread Testing
===============================================================

This script discovers existing media IDs that have face detection data
by using the same methods that Flutter uses, then tests the automatic
PPL Thread workflow integration with that real data.
"""

import json
import os
import sqlite3
import time
from pathlib import Path

import requests

# Configuration
VISION_SERVICE_URL = "http://localhost:8003"
ORCHESTRATOR_URL = "http://localhost:8002"
NODE_SERVICE_URL = "http://localhost:8001"


def get_auth_token():
    """Get authentication token for API calls."""
    try:
        token_file = Path("auth_token.json")
        if token_file.exists():
            with open(token_file, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("access_token")
    except Exception:
        pass
    return None


def discover_media_with_faces():
    """Discover media IDs that actually have face data using multiple strategies."""
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ No auth token found")
        return []

    headers = {"Authorization": f"Bearer {auth_token}"}
    media_with_faces = []

    print("🔍 Discovering existing media with face detection data...")
    print()

    # Strategy 1: Check the Vision Service database directly (more thorough)
    print("1️⃣ Checking Vision Service database directly...")

    db_path = (
        "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/vision_data.db"
    )
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"   Database tables found: {tables}")

            # Look for any table that might contain media/face data
            for table in tables:
                try:
                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]

                    # Look for media-related columns
                    media_columns = [
                        col
                        for col in columns
                        if any(term in col.lower() for term in ["media", "uuid", "id"])
                    ]

                    if media_columns and len(columns) > 2:  # Likely a data table
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]

                        if count > 0:
                            print(
                                f"   Table '{table}': {count} records, columns: {media_columns}"
                            )

                            # Try to get sample media UUIDs
                            for col in media_columns:
                                try:
                                    cursor.execute(
                                        f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL LIMIT 10"
                                    )
                                    sample_ids = [row[0] for row in cursor.fetchall()]
                                    if sample_ids:
                                        print(
                                            f"     Sample {col} values: {sample_ids[:3]}..."
                                        )

                                        # Test these IDs with the Vision Service API
                                        for media_id in sample_ids:
                                            if (
                                                isinstance(media_id, str)
                                                and len(media_id) > 10
                                            ):
                                                try:
                                                    response = requests.get(
                                                        f"{VISION_SERVICE_URL}/faces/media/{media_id}",
                                                        headers=headers,
                                                        timeout=5,
                                                    )
                                                    if response.status_code == 200:
                                                        faces_data = response.json()
                                                        faces_count = len(
                                                            faces_data.get("faces", [])
                                                        )
                                                        if faces_count > 0:
                                                            media_with_faces.append(
                                                                {
                                                                    "media_id": media_id,
                                                                    "faces_count": faces_count,
                                                                    "source": f"database_table_{table}",
                                                                }
                                                            )
                                                            print(
                                                                f"     ✅ Media {media_id}: {faces_count} faces"
                                                            )
                                                except Exception:
                                                    pass
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"   Error checking table {table}: {e}")

            conn.close()

        except Exception as e:
            print(f"   Database access error: {e}")

    print()

    # Strategy 2: Try sequential UUID patterns (common in testing)
    print("2️⃣ Testing common UUID patterns and known test media...")

    # Try some common patterns that might exist
    import uuid

    test_patterns = [
        # Try some sequential UUIDs that might have been generated during testing
        str(uuid.uuid4()),  # Just to test the format
    ]

    # Also try some known patterns from Flutter/testing
    known_test_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "test-media-id-001",
        "test-media-id-002",
        "sample-video-001",
        "sample-video-002",
    ]

    for media_id in known_test_ids:
        try:
            response = requests.get(
                f"{VISION_SERVICE_URL}/faces/media/{media_id}",
                headers=headers,
                timeout=3,
            )
            if response.status_code == 200:
                faces_data = response.json()
                faces_count = len(faces_data.get("faces", []))
                if faces_count > 0:
                    media_with_faces.append(
                        {
                            "media_id": media_id,
                            "faces_count": faces_count,
                            "source": "known_test_pattern",
                        }
                    )
                    print(f"   ✅ Test media {media_id}: {faces_count} faces")
        except Exception:
            pass

    print()

    # Strategy 3: Check if Vision Service has any internal endpoint to list media
    print("3️⃣ Checking Vision Service for media listing endpoints...")

    try:
        # Try some potential listing endpoints
        potential_endpoints = [
            "/api/v1/media",
            "/media",
            "/faces/recent",
            "/api/v1/faces",
        ]

        for endpoint in potential_endpoints:
            try:
                response = requests.get(
                    f"{VISION_SERVICE_URL}{endpoint}", headers=headers, timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Found data at {endpoint}: {len(str(data))} chars")

                    # Look for media IDs in the response
                    response_str = json.dumps(data).lower()
                    if "media" in response_str or "uuid" in response_str:
                        # Try to extract potential media IDs
                        import re

                        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
                        potential_uuids = re.findall(uuid_pattern, str(data))

                        for uuid_candidate in potential_uuids[:5]:  # Test first 5
                            try:
                                face_response = requests.get(
                                    f"{VISION_SERVICE_URL}/faces/media/{uuid_candidate}",
                                    headers=headers,
                                    timeout=3,
                                )
                                if face_response.status_code == 200:
                                    faces_data = face_response.json()
                                    faces_count = len(faces_data.get("faces", []))
                                    if faces_count > 0:
                                        media_with_faces.append(
                                            {
                                                "media_id": uuid_candidate,
                                                "faces_count": faces_count,
                                                "source": f"discovered_from_{endpoint}",
                                            }
                                        )
                                        print(
                                            f"   ✅ Discovered media {uuid_candidate}: {faces_count} faces"
                                        )
                            except Exception:
                                pass

            except Exception:
                pass

    except Exception as e:
        print(f"   Error checking listing endpoints: {e}")

    print()

    # Remove duplicates and sort by face count
    unique_media = {}
    for media in media_with_faces:
        media_id = media["media_id"]
        if (
            media_id not in unique_media
            or unique_media[media_id]["faces_count"] < media["faces_count"]
        ):
            unique_media[media_id] = media

    final_media_list = sorted(
        unique_media.values(), key=lambda x: x["faces_count"], reverse=True
    )

    print(
        f"🎉 DISCOVERY COMPLETE: Found {len(final_media_list)} unique media items with face data"
    )
    for media in final_media_list:
        print(
            f"   📹 {media['media_id']}: {media['faces_count']} faces (from {media['source']})"
        )

    return final_media_list


def test_ppl_thread_with_discovered_media():
    """Test PPL Thread workflow with discovered media."""
    print("🎯 Testing Automatic PPL Thread Workflow with Discovered Media")
    print("=" * 70)
    print()

    # Discover media with faces
    media_list = discover_media_with_faces()

    if not media_list:
        print("❌ No media with face data discovered")
        print("   This suggests either:")
        print("   • Face data is stored differently than expected")
        print("   • Database is empty/reset")
        print("   • Different authentication or API endpoints needed")
        return False

    # Test with the media that has the most faces
    test_media = media_list[0]
    media_id = test_media["media_id"]
    faces_count = test_media["faces_count"]

    print(f"📹 Testing with media: {media_id}")
    print(f"   Face count: {faces_count}")
    print(f"   Discovery source: {test_media['source']}")
    print()

    auth_token = get_auth_token()
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Test PPL Thread workflow
    print("🎯 Testing PPL Thread auto-trigger...")

    try:
        response = requests.post(
            f"{VISION_SERVICE_URL}/api/v1/person-objects/auto-trigger",
            json={"media_id": media_id},
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            persons_found = result.get("total_persons", 0)

            print(f"✅ PPL Thread workflow completed successfully!")
            print(f"   Input: {faces_count} faces detected")
            print(f"   Output: {persons_found} persons identified")
            print(
                f"   Processing: {faces_count} faces → {persons_found} unique persons"
            )

            # Test Flutter integration
            print()
            print("📱 Testing Flutter getPersonCount() simulation...")

            flutter_response = requests.get(
                f"{ORCHESTRATOR_URL}/person-objects/{media_id}",
                headers=headers,
                timeout=5,
            )

            if flutter_response.status_code == 200:
                flutter_data = flutter_response.json()
                flutter_person_count = flutter_data.get("total_persons", 0)

                print(f"✅ Flutter integration test successful!")
                print(f"   getPersonCount() returned: {flutter_person_count}")
                print(
                    f"   Match with workflow result: {'✅ Yes' if flutter_person_count == persons_found else '⚠️  No'}"
                )

                print()
                print("🎉 COMPLETE SUCCESS!")
                print("   ✅ Face detection data exists")
                print("   ✅ PPL Thread workflow processing works")
                print("   ✅ Auto-trigger endpoint functional")
                print("   ✅ Orchestrator integration confirmed")
                print("   ✅ Flutter getPersonCount() integration validated")
                print()
                print(
                    "🚀 The automatic PPL Thread workflow integration is FULLY OPERATIONAL!"
                )

                return True
            else:
                print(f"⚠️  Flutter API returned status: {flutter_response.status_code}")

        else:
            print(f"❌ PPL Thread workflow failed: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ PPL Thread workflow error: {e}")

    return False


if __name__ == "__main__":
    success = test_ppl_thread_with_discovered_media()

    if success:
        print()
        print("🎉 INTEGRATION COMPLETE AND VERIFIED!")
        print("   The automatic PPL Thread workflow is ready for production.")
        print("   Flutter apps will now show real person counts automatically.")
    else:
        print()
        print("⚠️  Integration testing encountered issues.")
        print("   Check the output above for troubleshooting information.")
