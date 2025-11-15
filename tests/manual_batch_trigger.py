#!/usr/bin/env python3
"""
Manual Batch Trigger Script
Manually creates a batch and triggers cross-video tracking for videos with cached faces
"""

import requests
import json
from datetime import datetime

# Configuration
VMETA_URL = "http://localhost:8008"
NODE_URL = "http://localhost:8001"
ORCHESTRATOR_URL = "http://localhost:8002"
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"

# Video UUIDs from 07:00 recording (4 minutes, 8 videos)
VIDEO_UUIDS = [
    "8b1faa6b-331d-4165-83cf-7a1d24ae2725",
    "75f6fbc6-f31a-4ecf-8619-35a5cd3d6c8d",
    "35a0b026-dce5-4c7d-9757-a7f4abf98d72",
    "5c45edcd-5de5-41cc-bf5a-97b373020b39",
    "308864fa-4618-4bf3-afd7-05e60dc80081",
    "b65df69e-8790-4ff5-b4a1-a64a1f6e3503",
    "2b04e8e1-ecf7-440f-983e-f2b9cba8a758",
    "2383c138-adf8-433b-93f5-59480c694daa",
]

COLLECTION_ID = "usb_camera_0"

def get_auth_token():
    """Get authentication token"""
    print("🔐 Authenticating...")
    response = requests.post(
        f"{NODE_URL}/api/v1/users/login",
        data={
            "username": USERNAME,
            "password": PASSWORD
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    print(f"✅ Got token: {token[:50]}...")
    return token

def create_tracking_session(token):
    """Create cross-video tracking session for the 8 videos"""
    print(f"\n📊 Creating tracking session for {len(VIDEO_UUIDS)} videos...")
    
    # Need to get video timestamps
    print("📹 Fetching video metadata...")
    headers = {"Authorization": f"Bearer {token}"}
    videos_response = requests.get(
        f"http://localhost:8000/api/v1/media/search?limit=10&order_by=created_at&order=desc",
        headers=headers
    )
    videos_response.raise_for_status()
    all_videos = videos_response.json()
    
    # Filter to our target videos
    target_videos = [v for v in all_videos if v['uuid'] in VIDEO_UUIDS]
    
    if not target_videos:
        print("❌ No videos found!")
        return None
    
    # Get time range
    start_time = min(v['created_at'] for v in target_videos)
    end_time = max(v['created_at'] for v in target_videos)
    
    print(f"   Start: {start_time}")
    print(f"   End: {end_time}")
    print(f"   Videos: {len(target_videos)}")
    
    # Create tracking session
    session_data = {
        "collections": [f"{COLLECTION_ID} Collection"],
        "start_time": start_time.replace("+02:00", "Z"),
        "end_time": end_time.replace("+02:00", "Z"),
        "background_processing": False
    }
    
    print(f"\n🚀 Creating tracking session...")
    response = requests.post(
        f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions",
        json=session_data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    
    print(f"📋 Response status: {response.status_code}")
    
    if response.status_code == 200 or response.status_code == 201:
        result = response.json()
        print(f"✅ Tracking session created!")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"❌ Failed: {response.text}")
        return None

def main():
    print("=" * 70)
    print("Manual Batch Processing Trigger")
    print("=" * 70)
    print(f"\nTarget: {len(VIDEO_UUIDS)} videos from {COLLECTION_ID}")
    print("")
    
    try:
        # Get auth token
        token = get_auth_token()
        
        # Create tracking session (this will process all 8 videos)
        result = create_tracking_session(token)
        
        if result:
            print("\n" + "=" * 70)
            print("✅ Success!")
            print("=" * 70)
            print(f"\nSession UUID: {result.get('session_uuid', 'N/A')}")
            print(f"Status: {result.get('status', 'N/A')}")
            print(f"Individuals: {result.get('individuals_found', 0)}")
            print(f"MVR People: {result.get('mvr_people_created', result.get('unique_mvr_people_count', 0))}")
            print("\nRun smoke test to verify: bash tests/smoke_test_pipeline.sh")
        else:
            print("\n❌ Failed to create tracking session")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
