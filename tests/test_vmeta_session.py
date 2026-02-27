#!/usr/bin/env python3#!/usr/bin/env python3

""""""Test vmeta session creation to see error logs"""

Test vmeta tracking session endpoints with exact Flutter parameters

This tests what the backend actually returns for session status and individualsimport requests

"""import json

import requests

import json# Get token

from datetime import datetime, timedeltalogin_url = "http://localhost:8001/api/v1/users/login"

login_data = {

# Configuration (same as Flutter)    "username": "fresh.user@example.com",

VMETA_URL = "http://localhost:8008"    "password": "NewPassword234!"

USERNAME = "admin"}

PASSWORD = "admin"  # Change if different

response = requests.post(login_url, data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"})

# Flutter request parameterstoken = response.json()["access_token"]

COLLECTION_NAME = "usb_camera_0 Collection"

START_TIME = "2025-10-13T18:45:00.000"print(f"✅ Token obtained: {token[:50]}...")

END_TIME = "2025-11-01T18:45:00.000"

# Create session

session_url = "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions"

def authenticate():session_data = {

    """Get authentication token"""    "collections": ["usb_camera_0 Collection"],

    print("🔐 Authenticating...")    "start_time": "2025-10-01T00:00:00Z",

    response = requests.post(    "end_time": "2025-10-31T23:59:59Z",

        f"{VMETA_URL}/api/v1/auth/login",    "background_processing": False

        json={"username": USERNAME, "password": PASSWORD},}

        timeout=10

    )headers = {

    response.raise_for_status()    "Authorization": f"Bearer {token}",

    token = response.json()["access_token"]    "Content-Type": "application/json"

    print(f"✅ Got token: {token[:50]}...")}

    return token

print("\n📡 Creating tracking session...")

response = requests.post(session_url, json=session_data, headers=headers)

def create_tracking_session(token):

    """Create tracking session with exact Flutter parameters"""print(f"\n📊 Response status: {response.status_code}")

    print("\n📝 Creating tracking session...")print(f"📋 Response data:")

    print(f"   Collection: {COLLECTION_NAME}")print(json.dumps(response.json(), indent=2))

    print(f"   Date range: {START_TIME} to {END_TIME}")

    # Check database

    request_data = {session_uuid = response.json().get("session_uuid")

        "collections": [COLLECTION_NAME],if session_uuid:

        "start_time": START_TIME,    import psycopg2

        "end_time": END_TIME,    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/ppl_meta_vmeta")

        "background_processing": True,    cur = conn.cursor()

        "algorithm_config": {    cur.execute(

            "max_gap_seconds": 10,        "SELECT session_uuid, status, total_videos, individuals_found, processed_videos "

            "iou_threshold": 0.3,        "FROM tracking_sessions WHERE session_uuid = %s",

            "min_overlap_confidence": 0.5        (session_uuid,)

        }    )

    }    row = cur.fetchone()

        if row:

    print(f"\n📤 Request body:")        print(f"\n🗄️  Database Status:")

    print(json.dumps(request_data, indent=2))        print(f"   UUID: {row[0]}")

            print(f"   Status: {row[1]}")

    response = requests.post(        print(f"   Total Videos: {row[2]}")

        f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions",        print(f"   Individuals Found: {row[3]}")

        headers={"Authorization": f"Bearer {token}"},        print(f"   Processed Videos: {row[4]}")

        json=request_data,    conn.close()

        timeout=10
    )
    response.raise_for_status()
    result = response.json()
    
    print(f"\n✅ Session created:")
    print(json.dumps(result, indent=2))
    
    return result["session_uuid"]


def get_session_status(token, session_uuid):
    """Get session status (Counter 1 source)"""
    print(f"\n📊 Getting session status for {session_uuid}...")
    
    response = requests.get(
        f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    response.raise_for_status()
    status = response.json()
    
    print(f"\n📡 SESSION STATUS RESPONSE:")
    print("=" * 80)
    print(json.dumps(status, indent=2))
    print("=" * 80)
    
    individuals_found = status.get("individuals_found", 0)
    session_status = status.get("status", "unknown")
    
    print(f"\n🎯 KEY FIELDS:")
    print(f"   Status: {session_status}")
    print(f"   individuals_found (COUNTER 1): {individuals_found}")
    
    return status


def get_session_individuals(token, session_uuid):
    """Get session individuals list (for batch merge)"""
    print(f"\n👥 Getting individuals list for {session_uuid}...")
    
    response = requests.get(
        f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    response.raise_for_status()
    result = response.json()
    
    print(f"\n📡 INDIVIDUALS LIST RESPONSE:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print("=" * 80)
    
    individuals = result.get("individuals", [])
    
    print(f"\n🎯 KEY FIELDS:")
    print(f"   Individual count: {len(individuals)}")
    
    if individuals:
        print(f"\n   First individual:")
        print(f"     UUID: {individuals[0].get('individual_uuid')}")
        print(f"     MVR Person UUID: {individuals[0].get('mvr_person_uuid')}")
    
    return result


def test_with_existing_session(token, session_uuid):
    """Test with a session UUID from Flutter"""
    print(f"\n🧪 TESTING EXISTING SESSION: {session_uuid}")
    print("=" * 80)
    
    # Get status
    status = get_session_status(token, session_uuid)
    
    # Get individuals
    individuals_data = get_session_individuals(token, session_uuid)
    
    # Compare
    individuals_found = status.get("individuals_found", 0)
    individuals_list_count = len(individuals_data.get("individuals", []))
    
    print(f"\n📊 COMPARISON:")
    print("=" * 80)
    print(f"Session Status 'individuals_found': {individuals_found}")
    print(f"Individuals List count: {individuals_list_count}")
    
    if individuals_found != individuals_list_count:
        print(f"\n⚠️ MISMATCH DETECTED!")
        print(f"   Status says {individuals_found} but list has {individuals_list_count}")
    else:
        print(f"\n✅ Counts match!")
    
    if individuals_found == 0:
        print(f"\n⚠️ ZERO INDIVIDUALS FOUND!")
        print(f"   This explains the 0 -> 0 in Flutter")
        print(f"   Session status: {status.get('status')}")
        print(f"\n   Possible causes:")
        print(f"   - Videos don't have face detection run")
        print(f"   - No faces detected in the videos")
        print(f"   - Session processing failed")
        print(f"   - Date range doesn't include processed videos")


def main():
    print("🧪 PPL Meta vmeta Session Endpoint Test")
    print("=" * 80)
    print("This tests what the backend actually returns")
    print("Using EXACT parameters from Flutter app")
    print("=" * 80)
    
    try:
        # Authenticate
        token = authenticate()
        
        # Option 1: Test with existing session UUID from Flutter
        print("\n" + "=" * 80)
        print("OPTION 1: Test existing session from Flutter")
        print("=" * 80)
        print("\nIf you have a session UUID from Flutter, enter it here")
        print("Otherwise, press Enter to create a new session")
        session_uuid = input("\nSession UUID (or Enter to skip): ").strip()
        
        if session_uuid:
            test_with_existing_session(token, session_uuid)
        else:
            # Option 2: Create new session
            print("\n" + "=" * 80)
            print("OPTION 2: Create new session with Flutter parameters")
            print("=" * 80)
            
            session_uuid = create_tracking_session(token)
            
            print(f"\n⏳ Session created with UUID: {session_uuid}")
            print(f"   Status check in 5 seconds...")
            
            import time
            time.sleep(5)
            
            # Check status
            status = get_session_status(token, session_uuid)
            
            session_status = status.get("status")
            
            if session_status == "completed":
                print(f"\n✅ Session already completed!")
                test_with_existing_session(token, session_uuid)
            elif session_status in ["pending", "processing"]:
                print(f"\n⏳ Session still {session_status}")
                print(f"   Wait for it to complete, then run:")
                print(f"   python3 test_vmeta_session.py")
                print(f"   And enter UUID: {session_uuid}")
            else:
                print(f"\n❌ Session status: {session_status}")
        
        print("\n" + "=" * 80)
        print("✅ Test complete!")
        print("=" * 80)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
