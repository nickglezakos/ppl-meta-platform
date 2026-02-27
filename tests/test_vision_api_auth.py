#!/usr/bin/env python3
"""Test Vision API with authentication"""

import requests
import json

# Get token
login_url = "http://localhost:8001/api/v1/users/login"
login_data = {
    "username": "fresh.user@example.com",
    "password": "NewPassword234!"
}

response = requests.post(login_url, data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
token = response.json()["access_token"]

print(f"✅ Token obtained: {token[:50]}...\n")

# Test video UUID (from earlier tests)
video_uuid = "9e8ceb5b-8b77-46d4-83ab-38e06ce1919e"

# Test 1: Get Vision session for video
print(f"🔍 Test 1: Getting Vision session for video {video_uuid}")
session_url = f"http://localhost:8003/api/v1/person-objects/media/{video_uuid}/session"

# WITHOUT auth
print("  → Testing WITHOUT auth:")
response = requests.get(session_url)
print(f"     Status: {response.status_code}")
if response.status_code == 200:
    print(f"     Session UUID: {response.json().get('session_uuid')}")
else:
    print(f"     Error: {response.text[:100]}")

# WITH auth
print("\n  → Testing WITH auth:")
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(session_url, headers=headers)
print(f"     Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    session_uuid = data.get('session_uuid')
    print(f"     Session UUID: {session_uuid}")
    
    if session_uuid:
        # Test 2: Get person objects from session
        print(f"\n🔍 Test 2: Getting person objects from session {session_uuid}")
        objects_url = f"http://localhost:8003/api/v1/person-objects/sessions/{session_uuid}"
        
        # WITHOUT auth
        print("  → Testing WITHOUT auth:")
        response = requests.get(objects_url)
        print(f"     Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"     Group tracking entries: {len(data.get('group_tracking', []))}")
        else:
            print(f"     Error: {response.text[:100]}")
        
        # WITH auth
        print("\n  → Testing WITH auth:")
        response = requests.get(objects_url, headers=headers)
        print(f"     Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"     Group tracking entries: {len(data.get('group_tracking', []))}")
            print(f"     Success: {data.get('success')}")
        else:
            print(f"     Error: {response.text[:100]}")
else:
    print(f"     Error: {response.text[:100]}")

print("\n✅ Tests complete")
