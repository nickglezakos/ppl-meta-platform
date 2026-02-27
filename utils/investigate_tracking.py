#!/usr/bin/env python3
"""
Investigation script for tracking session 843e7d29-36fc-4542-9fc5-194a7a1fbc11
Created: Nov 17, 2025
Purpose: Find the individual and MVR person created, trace back to videos
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8008"
NODE_URL = "http://localhost:8001"
SESSION_UUID = "843e7d29-36fc-4542-9fc5-194a7a1fbc11"

# Video UUIDs from our recording
VIDEO_UUIDS = [
    "8c77cf47-1db0-4b91-ab86-2f873307c52d",
    "52fa4969-cfe5-4252-9c87-10745b675c15",
    "cc62d890-cc0c-4738-ae37-ae06783de1d1",
    "5066a8c3-de30-46e7-9e5d-8d7352947181",
    "8135343f-c0cd-47a4-9ccb-a1441e355d95",
    "42b39201-e0dd-41d9-a195-cfa330df9f86",
    "9bbbff74-0286-470a-ad02-3b7b079d1f81",
    "011fb0dd-a27c-4c7c-a47d-2761361b8fd7"
]

def get_token():
    """Authenticate and get token"""
    response = requests.post(
        f"{NODE_URL}/api/v1/users/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data="username=fresh.user@example.com&password=NewPassword234!"
    )
    return response.json()["access_token"]

def search_mvr_people(token, start_time, end_time):
    """Search for MVR people in time range"""
    response = requests.post(
        f"{BASE_URL}/api/v1/mvr-people/search/by-collection",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "collection_name": "usb_camera_0",
            "start_time": start_time,
            "end_time": end_time,
            "limit": 500
        }
    )
    return response.json()

def main():
    print("=" * 70)
    print("TRACKING SESSION INVESTIGATION")
    print("=" * 70)
    print(f"Session UUID: {SESSION_UUID}")
    print(f"Session created: 2025-11-16 14:19:49")
    print(f"Videos processed: 8")
    print()
    
    # Get token
    print("1. Authenticating...")
    token = get_token()
    print("   ✓ Token obtained")
    print()
    
    # Search for MVR people created during tracking session
    print("2. Searching for MVR people created during tracking session...")
    print("   Time range: 2025-11-16 14:19:00 to 14:21:00")
    results = search_mvr_people(token, "2025-11-16T14:19:00", "2025-11-16T14:21:00")
    
    total = results.get("total_results", 0)
    print(f"   Found: {total} MVR people")
    print()
    
    if total == 0:
        print("❌ NO MVR PEOPLE FOUND!")
        print()
        print("Expanding search to entire day...")
        results = search_mvr_people(token, "2025-11-16T00:00:00", "2025-11-16T23:59:59")
        total = results.get("total_results", 0)
        print(f"   Found: {total} MVR people for entire day")
        print()
    
    if total > 0:
        print("3. MVR People Details:")
        print("-" * 70)
        for idx, mvr in enumerate(results.get("mvr_people", []), 1):
            print(f"\n   MVR #{idx}:")
            print(f"   UUID: {mvr['mvr_people_uuid']}")
            print(f"   Individuals: {len(mvr['individual_uuids'])}")
            print(f"   Total appearances: {mvr['total_appearances']}")
            print(f"   Unique videos: {mvr['unique_videos']}")
            print(f"   First seen: {mvr['first_seen']}")
            print(f"   Last seen: {mvr['last_seen']}")
            
            # Check which of our videos this MVR appears in
            print(f"\n   Video appearances:")
            our_videos_found = []
            for appearance in mvr.get('appearances', []):
                video_uuid = appearance['video_uuid']
                if video_uuid in VIDEO_UUIDS:
                    our_videos_found.append(video_uuid)
                    idx_in_list = VIDEO_UUIDS.index(video_uuid) + 1
                    print(f"      ✓ Video {idx_in_list}: {video_uuid[:8]}... "
                          f"(timestamp: {appearance['start_timestamp']})")
            
            if our_videos_found:
                print(f"\n   ✓ THIS MVR APPEARS IN {len(our_videos_found)}/8 OF OUR VIDEOS!")
            else:
                print(f"\n   ✗ This MVR does NOT appear in any of our 8 videos")
            
            print("-" * 70)
    else:
        print("❌ NO MVR PEOPLE FOUND FOR NOV 16!")
        print()
        print("CONCLUSION: Despite tracking session reporting '1 MVR person created',")
        print("            no MVR person actually exists in the database.")
        print("            This confirms the session's counter is wrong.")
    
    print()
    print("=" * 70)
    print("INVESTIGATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
