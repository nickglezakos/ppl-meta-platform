#!/usr/bin/env python3
"""
Trigger Batch Processing for Jan 9-12 Videos
Process existing videos that have face detections but no MVR linkages
"""

import requests
import json
from datetime import datetime

# Configuration
VMETA_URL = "http://localhost:8008"
NODE_URL = "http://localhost:8001"
ORCH_URL = "http://localhost:8002"
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"
COLLECTION_ID = "usb_camera_0"

def get_auth_token():
    """Get JWT authentication token."""
    print("🔐 Authenticating...")
    response = requests.post(
        f'{NODE_URL}/api/v1/users/login',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=f'username={USERNAME}&password={PASSWORD}'
    )
    
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.text}")
        return None
    
    token = response.json()['access_token']
    print(f"✅ Authenticated\n")
    return token

def get_videos_with_person_objects(token, start_date, end_date):
    """Get videos that have person_objects but might not have MVR linkages."""
    print(f"📹 Fetching videos with person_objects from {start_date} to {end_date}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Query orchestrator for videos with person_objects in date range
    response = requests.get(
        f'{ORCH_URL}/api/v1/person-objects',
        headers=headers,
        params={
            'collection_id': COLLECTION_ID,
            'start_date': f'{start_date}T00:00:00Z',
            'end_date': f'{end_date}T23:59:59Z',
            'limit': 1000
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch person objects: {response.text}")
        return []
    
    person_objects = response.json()
    
    # Extract unique video UUIDs
    video_uuids = list(set([po['video_uuid'] for po in person_objects if 'video_uuid' in po]))
    
    print(f"   Found {len(person_objects)} person_objects in {len(video_uuids)} videos\n")
    return video_uuids

def create_tracking_session(token, video_uuids):
    """Create cross-video tracking session to process videos."""
    if not video_uuids:
        print("⚠️  No videos to process")
        return None
    
    print(f"🚀 Creating tracking session for {len(video_uuids)} videos...")
    print(f"   Collection: {COLLECTION_ID}\n")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f'{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions',
        headers=headers,
        json={
            'collections': [COLLECTION_ID],
            'video_uuids': video_uuids,
            'background_processing': True,
            'force_reprocess': True  # Force reprocessing to create MVR linkages
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create tracking session: {response.text}")
        return None
    
    result = response.json()
    session_uuid = result.get('session_uuid')
    
    print(f"✅ Tracking session created: {session_uuid}")
    print(f"   Status: {result.get('status', 'N/A')}")
    print(f"   Processing in background...\n")
    
    return session_uuid

def check_session_status(token, session_uuid):
    """Check status of tracking session."""
    print(f"🔍 Checking session status...")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        f'{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}',
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get session status: {response.text}")
        return None
    
    result = response.json()
    print(f"   Status: {result.get('status', 'N/A')}")
    print(f"   Individuals: {result.get('individuals_found', 0)}")
    print(f"   MVR People: {result.get('unique_mvr_people_count', 0)}")
    
    return result

def main():
    print("=" * 70)
    print("🚀 Batch Processing Trigger - Jan 9-12 Videos")
    print("=" * 70)
    print()
    
    # Step 1: Authenticate
    token = get_auth_token()
    if not token:
        return
    
    # Step 2: Get videos with person_objects from Jan 9-12
    video_uuids = get_videos_with_person_objects(token, '2026-01-09', '2026-01-12')
    if not video_uuids:
        return
    
    # Step 3: Create tracking session (this will process all videos)
    session_uuid = create_tracking_session(token, video_uuids)
    if not session_uuid:
        return
    
    # Step 4: Check initial status
    check_session_status(token, session_uuid)
    
    print("\n" + "=" * 70)
    print("✅ Batch processing triggered!")
    print("=" * 70)
    print(f"\n💡 To check progress, run:")
    print(f"   curl -s 'http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}' \\")
    print(f"     -H 'Authorization: Bearer {token[:20]}...' | python3 -m json.tool")
    print()

if __name__ == "__main__":
    main()
