#!/usr/bin/env python3
"""Test vmeta session creation to see error logs"""

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

print(f"✅ Token obtained: {token[:50]}...")

# Create session
session_url = "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions"
session_data = {
    "collections": ["usb_camera_0 Collection"],
    "start_time": "2025-10-01T00:00:00Z",
    "end_time": "2025-10-31T23:59:59Z",
    "background_processing": False
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("\n📡 Creating tracking session...")
response = requests.post(session_url, json=session_data, headers=headers)

print(f"\n📊 Response status: {response.status_code}")
print(f"📋 Response data:")
print(json.dumps(response.json(), indent=2))

# Check database
session_uuid = response.json().get("session_uuid")
if session_uuid:
    import psycopg2
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/ppl_meta_vmeta")
    cur = conn.cursor()
    cur.execute(
        "SELECT session_uuid, status, total_videos, individuals_found, processed_videos "
        "FROM tracking_sessions WHERE session_uuid = %s",
        (session_uuid,)
    )
    row = cur.fetchone()
    if row:
        print(f"\n🗄️  Database Status:")
        print(f"   UUID: {row[0]}")
        print(f"   Status: {row[1]}")
        print(f"   Total Videos: {row[2]}")
        print(f"   Individuals Found: {row[3]}")
        print(f"   Processed Videos: {row[4]}")
    conn.close()
