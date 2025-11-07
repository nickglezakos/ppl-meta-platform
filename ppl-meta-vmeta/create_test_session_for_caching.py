"""
Create a new tracking session with the same collection/time to test caching
"""

import requests
import json
from datetime import datetime

# Use Gateway service endpoint (proxies to vmeta)
GATEWAY_URL = "http://localhost:8080"
NODE_URL = "http://localhost:8001"

def get_auth_token():
    """Get authentication token from the Node service."""
    print("🔑 Obtaining authentication token...")
    
    try:
        response = requests.post(
            f'{NODE_URL}/api/v1/users/login',
            data={
                'username': 'fresh.user@example.com',
                'password': 'NewPassword234!'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')
            print("✅ Authentication successful")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Failed to get auth token: {e}")
        return None

# Use same collection and time range as original session
payload = {
    "collections": ["usb_camera_0"],
    "start_time": "2025-11-05T08:40:00",
    "end_time": "2025-11-05T10:49:00",
    "algorithm_config": {
        "batch_size": 100,
        "is_default": False,
        "config_name": "test_caching_nov5",
        "description": "Test video-level caching with real data",
        "iou_threshold": 0.3,
        "max_collections": 10,
        "max_gap_seconds": 3,
        "min_appearances": 1,
        "min_sequence_length": 2,
        "confidence_weight_iou": 0.4,
        "min_overlap_confidence": 0.5,
        "confidence_weight_spatial": 0.3,
        "confidence_weight_temporal": 0.3
    }
}

print("="*70)
print("CREATING TEST SESSION TO VERIFY CACHING")
print("="*70)

# Get authentication token first
auth_token = get_auth_token()
if not auth_token:
    print("\n❌ ERROR: Cannot proceed without authentication token")
    print("Make sure the Node service is running at http://localhost:8001")
    exit(1)

print("\n📋 Request:")
print(f"   Collection: {payload['collections'][0]}")
print(f"   Time: {payload['start_time']} → {payload['end_time']}")
print("   Expected: Should find same 4 videos")
print("   Expected: Should cache individual ind_e147b0a0")

print("\n🚀 Sending authenticated request to Gateway (port 8080)...")

headers = {
    "Authorization": f"Bearer {auth_token}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{GATEWAY_URL}/api/v1/cross-video/individuals/tracking/sessions",
    json=payload,
    headers=headers,
    timeout=120
)

print(f"\n📊 Response ({response.status_code}):")

if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
    
    session_uuid = result.get("session_uuid")
    cache_hit_rate = result.get("cache_hit_rate", 0)
    
    print("\n" + "="*70)
    print("SESSION CREATED SUCCESSFULLY!")
    print("="*70)
    print(f"\nSession UUID: {session_uuid}")
    print(f"Cache Hit Rate: {cache_hit_rate * 100:.1f}%")
    
    print("\n🔍 Next: Check cache statistics:")
    print(f"\n   psql -U postgres -d ppl_meta_vmeta -c \"")
    print(f"       SELECT video_uuid, cache_hit, "
          f"individuals_reused, individuals_created")
    print(f"       FROM individual_cache_stats")
    print(f"       WHERE session_uuid = '{session_uuid}'")
    print(f"       ORDER BY timestamp;")
    print(f"   \"")
    
    if cache_hit_rate == 1.0:
        print("\n✅ SUCCESS: 100% cache hit rate!")
        print("   All 4 videos reused existing individual")
    elif cache_hit_rate > 0:
        print(f"\n⚠️  PARTIAL: {cache_hit_rate*100}% cache hit rate")
        print("   Some videos reused, others created new")
    else:
        print("\n❌ NO CACHING: 0% cache hit rate")
        print("   Caching code may not be active")
        
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
