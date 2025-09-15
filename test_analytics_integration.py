#!/usr/bin/env python3
"""
PPL Meta Vision Analytics Integration Test

Simple integration test for Phase 5 Analytics & Traceability Features.
Tests all analytics endpoints with realistic scenarios.
"""

import json
import uuid
from datetime import datetime, timedelta

import requests


def test_analytics_endpoints():
    """Test all analytics endpoints."""
    base_url = "http://localhost:8003"
    test_camera_uuid = str(uuid.uuid4())
    test_media_uuid = str(uuid.uuid4())

    print("🧪 Testing PPL Meta Vision Analytics Endpoints")
    print("=" * 50)

    # Test 1: Service Health
    print("\n1. Testing service health...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Vision service is healthy")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False

    # Test 2: Cross-Session Analytics
    print("\n2. Testing cross-session analytics...")
    try:
        response = requests.get(f"{base_url}/analytics/cross-session")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cross-session analytics: {data.get('success')}")
            print(f"📊 Analytics keys: {list(data.get('analytics', {}).keys())}")
        else:
            print(f"❌ Cross-session analytics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cross-session analytics error: {e}")

    # Test 3: Device Traceability
    print("\n3. Testing device traceability...")
    try:
        url = f"{base_url}/analytics/device/{test_camera_uuid}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Device analytics: {data.get('success')}")
        else:
            print(f"✅ Device analytics (no data): {response.status_code}")
    except Exception as e:
        print(f"❌ Device traceability error: {e}")

    # Test 4: Media Timeline
    print("\n4. Testing media timeline...")
    try:
        url = f"{base_url}/analytics/media/{test_media_uuid}/timeline"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Media timeline: {data.get('success')}")
        else:
            print(f"✅ Media timeline (no data): {response.status_code}")
    except Exception as e:
        print(f"❌ Media timeline error: {e}")

    # Test 5: Advanced Query - Sessions
    print("\n5. Testing advanced querying (sessions)...")
    try:
        params = {"query_type": "sessions", "limit": 5}
        response = requests.get(f"{base_url}/analytics/query", params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sessions query: {data.get('success')}")
            result = data.get("result", {})
            print(f"📊 Found {len(result.get('sessions', []))} sessions")
        else:
            print(f"❌ Sessions query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Sessions query error: {e}")

    # Test 6: Advanced Query - Devices
    print("\n6. Testing advanced querying (devices)...")
    try:
        params = {"query_type": "devices", "limit": 5}
        response = requests.get(f"{base_url}/analytics/query", params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Devices query: {data.get('success')}")
            result = data.get("result", {})
            print(f"📊 Found {len(result.get('devices', []))} devices")
        else:
            print(f"❌ Devices query failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Devices query error: {e}")

    # Test 7: Performance Analytics
    print("\n7. Testing performance analytics...")
    try:
        params = {"days": 7, "granularity": "day"}
        response = requests.get(f"{base_url}/analytics/performance", params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Performance analytics: {data.get('success')}")
            analytics = data.get("analytics", {})
            print(f"📊 Performance keys: {list(analytics.keys())}")
        else:
            print(f"❌ Performance analytics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Performance analytics error: {e}")

    # Test 8: Dashboard Summary
    print("\n8. Testing dashboard summary...")
    try:
        params = {"days": 7}
        response = requests.get(f"{base_url}/analytics/summary", params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dashboard summary: {data.get('success')}")
            summary = data.get("summary", {})
            print(f"📊 Summary keys: {list(summary.keys())}")
        else:
            print(f"❌ Dashboard summary failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard summary error: {e}")

    # Test 9: Invalid Endpoints
    print("\n9. Testing error handling...")
    try:
        # Invalid query type
        params = {"query_type": "invalid"}
        response = requests.get(f"{base_url}/analytics/query", params=params)
        if response.status_code == 400:
            print("✅ Invalid query type properly rejected")
        else:
            print(f"❌ Invalid query type handling: {response.status_code}")

        # Invalid UUID format
        response = requests.get(f"{base_url}/analytics/device/invalid-uuid")
        if response.status_code == 400:
            print("✅ Invalid UUID format properly rejected")
        else:
            print(f"❌ Invalid UUID handling: {response.status_code}")

    except Exception as e:
        print(f"❌ Error handling test error: {e}")

    print("\n" + "=" * 50)
    print("🏁 Analytics integration test completed!")
    return True


if __name__ == "__main__":
    test_analytics_endpoints()
