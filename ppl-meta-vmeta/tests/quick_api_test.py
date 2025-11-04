#!/usr/bin/env python3
"""Quick API integration test for Phase 6.6 validation"""

import requests
import random
import json

def test_api_endpoints():
    base_url = "http://localhost:8008"
    
    print("=" * 60)
    print("Phase 6.6: API Integration Tests")
    print("=" * 60)
    
    # Test 1: Health endpoint
    print("\n1. Testing Health Endpoint...")
    try:
        health = requests.get(f"{base_url}/health", timeout=5).json()
        print(f"✅ Health check: {health['status']}")
        print(f"   MVR-People available: {health['mvr_people']['mvr_people_available']}")
        print(f"   Total MVR-People: {health['mvr_people']['statistics']['total_mvr_people']}")
        print(f"   Active MVR-People: {health['mvr_people']['statistics']['active_mvr_people']}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Demographics search
    print("\n2. Testing Demographics Search...")
    try:
        search = requests.post(
            f"{base_url}/api/v1/mvr-people/search/demographics",
            json={"gender": "male", "limit": 5},
            timeout=5
        ).json()
        print(f"✅ Demographics search: {len(search.get('results', search))} results")
    except Exception as e:
        print(f"❌ Demographics search failed: {e}")
    
    # Test 3: Similarity search
    print("\n3. Testing Similarity Search...")
    try:
        embedding = [random.random() for _ in range(512)]
        similar = requests.post(
            f"{base_url}/api/v1/mvr-people/search/similar",
            json={"face_embedding": embedding, "similarity_threshold": 0.7, "limit": 5},
            timeout=5
        ).json()
        print(f"✅ Similarity search: {len(similar.get('results', similar))} results")
    except Exception as e:
        print(f"❌ Similarity search failed: {e}")
    
    # Test 4: Orphaned MVR query
    print("\n4. Testing Orphaned MVR Query...")
    try:
        orphaned = requests.get(f"{base_url}/api/v1/mvr-people/orphaned", timeout=5).json()
        print(f"✅ Orphaned MVR query: {len(orphaned.get('results', orphaned))} results")
    except Exception as e:
        print(f"❌ Orphaned MVR query failed: {e}")
    
    # Test 5: Matching config
    print("\n5. Testing Matching Configuration...")
    try:
        config = requests.get(f"{base_url}/api/v1/mvr-people/config/matching", timeout=5).json()
        print(f"✅ Matching config retrieved")
        print(f"   Similarity threshold: {config.get('similarity_threshold', 'N/A')}")
    except Exception as e:
        print(f"❌ Matching config failed: {e}")
    
    # Test 6: MVR-People health
    print("\n6. Testing MVR-People Health Endpoint...")
    try:
        mvr_health = requests.get(f"{base_url}/api/v1/mvr-people/health", timeout=5).json()
        print(f"✅ MVR-People health: {mvr_health.get('status', 'unknown')}")
    except Exception as e:
        print(f"❌ MVR-People health failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ API Integration Tests Complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_api_endpoints()
