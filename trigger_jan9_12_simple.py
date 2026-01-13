#!/usr/bin/env python3
"""
Trigger Batch Processing for Jan 9-12 Videos
Simple script to manually trigger batch processing for existing videos
"""

import requests
import json

# Configuration
VMETA_URL = "http://localhost:8008"
NODE_URL = "http://localhost:8001"
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

def trigger_batch(token):
    """Manually trigger batch processing for the collection."""
    print(f"🚀 Triggering batch processing for {COLLECTION_ID}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f'{VMETA_URL}/api/v1/batch-processing/trigger',
        headers=headers,
        json={
            'collection_id': COLLECTION_ID,
            'force_trigger': True,
            'min_videos': 1
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to trigger batch: {response.text}")
        return None
    
    result = response.json()
    print(f"✅ Batch triggered:")
    print(f"   Batch UUID: {result.get('batch_uuid', 'N/A')}")
    print(f"   Status: {result.get('status', 'N/A')}")
    print(f"   Video count: {result.get('video_count', 0)}")
    print(f"   Message: {result.get('message', '')}\n")
    
    return result

def create_tracking_session_for_date_range(token, start_date, end_date):
    """Create tracking session for specific date range."""
    print(f"🚀 Creating tracking session for {start_date} to {end_date}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f'{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions',
        headers=headers,
        json={
            'collections': [COLLECTION_ID],
            'start_time': f'{start_date}T00:00:00Z',
            'end_time': f'{end_date}T23:59:59Z',
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

def main():
    print("=" * 70)
    print("🚀 Batch Processing Trigger - Jan 9-12 Videos")
    print("=" * 70)
    print()
    print("This script will create a tracking session for all videos")
    print("from Jan 9-12 to generate MVR people linkages.\n")
    
    # Step 1: Authenticate
    token = get_auth_token()
    if not token:
        return
    
    # Step 2: Try batch trigger first (if there's an active batch)
    print("📋 Option 1: Try triggering existing batch...")
    batch_result = trigger_batch(token)
    
    # Step 3: Create tracking session for date range
    print("📋 Option 2: Create tracking session for Jan 9-12...")
    session_uuid = create_tracking_session_for_date_range(token, '2026-01-09', '2026-01-12')
    
    if session_uuid:
        print("\n" + "=" * 70)
        print("✅ Processing started!")
        print("=" * 70)
        print(f"\n💡 To check progress, run:")
        print(f"   curl -s 'http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}' \\")
        print(f"     -H 'Authorization: Bearer {token[:20]}...' | python3 -m json.tool")
        print()
        print("💡 Or wait a few minutes and re-run your search in the Flutter app!")
        print()
    else:
        print("\n⚠️  Could not start processing. Check the logs above for errors.")

if __name__ == "__main__":
    main()
