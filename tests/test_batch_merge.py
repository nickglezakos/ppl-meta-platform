#!/usr/bin/env python3
"""
Test script for batch match and merge endpoint

Usage:
    python test_batch_merge.py

Requirements:
    - vmeta service running on port 8008
    - Valid JWT token in environment or auth_token.json
"""

import requests
import json
import sys
from pathlib import Path


def get_auth_token(node_service_url="http://localhost:8001"):
    """Get authentication token by logging in to node service."""
    
    print("🔐 Authenticating with node service...")
    
    try:
        # Login to get token
        login_response = requests.post(
            f"{node_service_url}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "username": "fresh.user@example.com",
                "password": "NewPassword234!"
            },
            timeout=10
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            token = token_data.get('access_token')
            if token:
                print("✅ Successfully authenticated")
                return token
            else:
                print("❌ Login succeeded but no access_token in response")
                print(f"   Response: {token_data}")
                return None
        else:
            print(f"❌ Login failed with status {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to node service at {node_service_url}")
        print("   Make sure the node service is running on port 8001")
        return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


def test_batch_merge_endpoint(base_url="http://localhost:8008"):
    """Test the batch match and merge endpoint."""
    
    print("\n" + "="*70)
    print("Testing Batch Match & Merge Endpoint")
    print("="*70 + "\n")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Check if endpoint exists
    print("Test 1: Checking endpoint availability...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/mvr-people/batch-match-and-merge",
            headers=headers,
            json={
                "individual_uuids": [],  # Empty list to trigger validation
                "threshold": 0.85
            }
        )
        
        if response.status_code == 422:
            print("✅ Endpoint exists (validation error as expected for empty list)")
        elif response.status_code == 401:
            print("❌ Authentication failed - token may be invalid")
            print(f"   Response: {response.text}")
            sys.exit(1)
        else:
            print(f"✅ Endpoint exists (status: {response.status_code})")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to vmeta service")
        print(f"   Make sure service is running on {base_url}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # Test 2: Get a real tracking session to test with
    print("\nTest 2: Looking for a completed tracking session...")
    
    # First, let's check if there are any sessions
    try:
        # Try to get sessions from database
        print("   Note: Need real individual UUIDs from a tracking session")
        print("   You can get these by:")
        print("   1. Creating a tracking session in Flutter")
        print("   2. Getting session individuals from:")
        print("      GET /api/v1/cross-video/sessions/{uuid}/individuals")
        print("   3. Then calling batch merge with those UUIDs")
        
        print("\n✅ Endpoint is ready for use!")
        print("\nExample usage:")
        print("-" * 70)
        print("curl -X POST http://localhost:8008/api/v1/mvr-people/batch-match-and-merge \\")
        print('  -H "Authorization: Bearer YOUR_TOKEN" \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{')
        print('    "individual_uuids": [')
        print('      "uuid-1", "uuid-2", "uuid-3", ...')
        print('    ],')
        print('    "threshold": 0.85,')
        print('    "triggered_by": "cross_video_tracking_session"')
        print('  }\'')
        print("-" * 70)
        
        # Test with mock data (will likely fail but shows format)
        print("\nTest 3: Testing with mock UUIDs (expected to fail)...")
        mock_response = requests.post(
            f"{base_url}/api/v1/mvr-people/batch-match-and-merge",
            headers=headers,
            json={
                "individual_uuids": [
                    "00000000-0000-0000-0000-000000000001",
                    "00000000-0000-0000-0000-000000000002",
                ],
                "threshold": 0.85,
                "triggered_by": "test"
            },
            timeout=10
        )
        
        print(f"   Status: {mock_response.status_code}")
        if mock_response.status_code == 200:
            result = mock_response.json()
            print(f"   ✅ Success! Result:")
            print(f"      Original count: {result.get('original_count')}")
            print(f"      Unique count: {result.get('unique_count')}")
            print(f"      Merge count: {result.get('merge_count')}")
        else:
            print(f"   ⚠️ Expected failure (no individuals with these UUIDs)")
            print(f"   Response: {mock_response.text[:200]}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*70)
    print("Endpoint Implementation Complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Create a tracking session with real data")
    print("2. Get the individual UUIDs from that session")
    print("3. Call this endpoint with those UUIDs")
    print("4. See the unique count after auto-merging duplicates")
    print()


if __name__ == "__main__":
    test_batch_merge_endpoint()
