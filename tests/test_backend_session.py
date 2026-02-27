#!/usr/bin/env python3
"""
Test vmeta backend with exact Flutter parameters
"""
import requests
import json

VMETA_URL = "http://localhost:8008"
NODE_URL = "http://localhost:8001"
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"

COLLECTION_NAME = "usb_camera_0 Collection"
START_TIME = "2025-10-13T18:45:00.000"
END_TIME = "2025-11-01T18:45:00.000"


def authenticate():
    print("🔐 Authenticating...")
    # Use Node service for authentication (as per notes.txt)
    response = requests.post(
        f"{NODE_URL}/api/v1/users/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": USERNAME, "password": PASSWORD},
        timeout=10
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    print(f"✅ Got token: {token[:50]}...")
    return token


def get_session_status(token, session_uuid):
    print(f"\n📊 Getting session status for {session_uuid}...")
    
    url = f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    response.raise_for_status()
    status = response.json()
    
    print("\n📡 SESSION STATUS RESPONSE:")
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
    print(f"\n👥 Getting individuals list for {session_uuid}...")
    
    url = f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    response.raise_for_status()
    result = response.json()
    
    print("\n📡 INDIVIDUALS LIST RESPONSE:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print("=" * 80)
    
    individuals = result.get("individuals", [])
    
    print(f"\n🎯 KEY FIELDS:")
    print(f"   Individual count: {len(individuals)}")
    
    if individuals:
        print(f"\n   First individual:")
        first = individuals[0]
        print(f"     UUID: {first.get('individual_uuid')}")
        print(f"     MVR Person UUID: {first.get('mvr_person_uuid')}")
    
    return result


def test_session(token, session_uuid):
    print(f"\n🧪 TESTING SESSION: {session_uuid}")
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
        print("\n⚠️ MISMATCH DETECTED!")
        print(f"   Status: {individuals_found}, List: {individuals_list_count}")
    else:
        print("\n✅ Counts match!")
    
    if individuals_found == 0:
        print("\n⚠️ ZERO INDIVIDUALS FOUND!")
        print(f"   This explains the 0 -> 0 in Flutter")
        print(f"   Session status: {status.get('status')}")
        print("\n   Possible causes:")
        print("   - Videos don't have face detection run")
        print("   - No faces detected in the videos")
        print("   - Session processing failed")


def main():
    print("🧪 PPL Meta vmeta Session Test")
    print("=" * 80)
    print("Tests what backend actually returns")
    print("=" * 80)
    
    try:
        token = authenticate()
        
        print("\nEnter session UUID from Flutter")
        print("(Look for it in Flutter debug output)")
        session_uuid = input("\nSession UUID: ").strip()
        
        if session_uuid:
            test_session(token, session_uuid)
        else:
            print("\n❌ No session UUID provided")
        
        print("\n" + "=" * 80)
        print("✅ Test complete!")
        print("=" * 80)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
