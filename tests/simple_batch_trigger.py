#!/usr/bin/env python3
"""
Simple Batch Trigger - Bypasses session management
Checks for videos with cached face data and directly triggers batch processing
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
VMETA_URL = "http://localhost:8008"
VISION_URL = "http://localhost:8003"
MEDIA_URL = "http://localhost:8000"
NODE_URL = "http://localhost:8001"
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"
COLLECTION_ID = "usb_camera_0"

def get_auth_token():
    """Get authentication token"""
    print("🔐 Authenticating...")
    response = requests.post(
        f"{NODE_URL}/api/v1/users/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    print(f"✅ Got token: {token[:50]}...")
    return token


def get_recent_videos(token, hours=24, limit=20):
    """Get recent videos from Media service"""
    print(f"\n📹 Fetching recent videos (last {hours} hours)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{MEDIA_URL}/api/v1/media/search?limit={limit}&order_by=created_at&order=desc",
        headers=headers
    )
    response.raise_for_status()
    
    videos = response.json()
    # Filter to target collection and recent videos
    cutoff = datetime.now() - timedelta(hours=hours)
    
    recent = []
    for v in videos:
        created = v.get('created_at', '')
        if COLLECTION_ID.lower() in str(v).lower():
            recent.append(v)
    
    print(f"   Found {len(recent)} videos from {COLLECTION_ID}")
    return recent[:limit]


def check_video_has_faces(token, video_uuid):
    """Check if video has cached face data"""
    try:
        response = requests.post(
            f"{VISION_URL}/faces/media/{video_uuid}/bulk-process",
            json={},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            face_count = data.get('total_faces', 0)
            return face_count > 0, face_count
        return False, 0
    except Exception as e:
        print(f"      Error checking faces: {e}")
        return False, 0


def trigger_batch_for_videos(token, videos):
    """Trigger cross-video tracking (batch processing) for videos"""
    if not videos:
        print("\n⚠️  No videos to process")
        return None
    
    print(f"\n🚀 Triggering batch processing for {len(videos)} videos...")
    
    # Get time range
    start_time = min(v['created_at'] for v in videos)
    end_time = max(v['created_at'] for v in videos)
    
    print(f"   Time range: {start_time} to {end_time}")
    
    # Create tracking session (this IS batch processing)
    session_data = {
        "collections": [f"{COLLECTION_ID} Collection"],
        "start_time": start_time.replace("+02:00", "Z").replace("+00:00", "Z"),
        "end_time": end_time.replace("+02:00", "Z").replace("+00:00", "Z"),
        "background_processing": False
    }
    
    response = requests.post(
        f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions",
        json=session_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Batch processing triggered!")
        return result
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def main():
    print("=" * 70)
    print("Simple Batch Trigger - Check Videos with Faces")
    print("=" * 70)
    print("")
    
    try:
        # Authenticate
        token = get_auth_token()
        
        # Get recent videos
        videos = get_recent_videos(token, hours=2, limit=20)
        
        if not videos:
            print("\n❌ No videos found")
            return
        
        # Check which videos have faces
        print(f"\n🔍 Checking which videos have face data...")
        videos_with_faces = []
        
        for i, video in enumerate(videos, 1):
            uuid = video['uuid']
            created = video.get('created_at', 'N/A')
            
            has_faces, count = check_video_has_faces(token, uuid)
            
            if has_faces:
                print(f"   ✅ {i}. {uuid[:8]}... - {count} faces - {created}")
                videos_with_faces.append(video)
            else:
                print(f"   ⚠️  {i}. {uuid[:8]}... - no faces - {created}")
        
        print(f"\n📊 Summary: {len(videos_with_faces)}/{len(videos)} videos have face data")
        
        if len(videos_with_faces) >= 2:
            # Trigger batch processing
            result = trigger_batch_for_videos(token, videos_with_faces)
            
            if result:
                print("\n" + "=" * 70)
                print("✅ Success!")
                print("=" * 70)
                session_uuid = result.get('session_uuid', 'N/A')
                print(f"\nSession UUID: {session_uuid}")
                print(f"Status: {result.get('status', 'N/A')}")
                print(f"\n⏳ Processing... Check status with:")
                print(f"   curl -H 'Authorization: Bearer <token>' \\")
                print(f"     {VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}")
                print(f"\nOr run smoke test after a few seconds:")
                print(f"   bash tests/smoke_test_pipeline.sh")
        else:
            print(f"\n⚠️  Need at least 2 videos with faces (found {len(videos_with_faces)})")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
