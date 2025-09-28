#!/usr/bin/env python3
"""
Manually trigger PPL Thread workflow for specific media ID
"""
import json
from datetime import datetime

import requests

# Use the media ID from our Flutter app that has faces
MEDIA_ID = "e9681a10-7e5f-4d05-ad74-b025cc25bc78"


def get_auth_token():
    """Get auth token from file"""
    try:
        with open("auth_token.json", "r") as f:
            token_data = json.load(f)
            return token_data.get("token")
    except:
        return None


def trigger_ppl_workflow_direct():
    """Trigger PPL Thread workflow via Orchestrator (bypassing session requirement)"""
    token = get_auth_token()
    if not token:
        print("❌ No auth token found")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Direct trigger via Orchestrator API
    url = f"http://localhost:8002/person-objects/{MEDIA_ID}"

    print(f"🔄 Triggering PPL Thread workflow for media: {MEDIA_ID}")
    print(f"📡 URL: {url}")

    try:
        # Use PUT to trigger processing (matches our backend API)
        response = requests.put(url, headers=headers)

        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Workflow triggered successfully!")
            print(f"📈 Total persons: {data.get('total_persons', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to trigger workflow: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error triggering workflow: {e}")
        return False


def check_existing_data():
    """Check if person objects data already exists"""
    token = get_auth_token()
    if not token:
        print("❌ No auth token found")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Check via Orchestrator API
    url = f"http://localhost:8002/person-objects/{MEDIA_ID}"

    print(f"🔍 Checking existing person objects data for: {MEDIA_ID}")

    try:
        response = requests.get(url, headers=headers)

        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Data exists!")
            print(f"📈 Status: {data.get('status', 'N/A')}")
            print(f"📈 Total persons: {data.get('total_persons', 'N/A')}")
            return True
        else:
            print(f"ℹ️ No existing data found (status: {response.status_code})")
            return False

    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False


if __name__ == "__main__":
    print("🎯 PPL Thread Workflow Trigger Test")
    print("=" * 50)
    print()

    # Step 1: Check if data already exists
    print("1️⃣ Checking for existing person objects data...")
    exists = check_existing_data()
    print()

    # Step 2: If no data, trigger workflow
    if not exists:
        print("2️⃣ No existing data found, triggering workflow...")
        success = trigger_ppl_workflow_direct()
        if success:
            print()
            print("3️⃣ Re-checking data after workflow trigger...")
            check_existing_data()
    else:
        print("✅ Data already exists, no need to trigger workflow!")

    print()
    print("🎉 Test complete!")
