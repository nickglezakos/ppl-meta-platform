#!/usr/bin/env python3
"""
Test script for Instant Temporal Detection

Tests the instant detection API endpoints and validates results.
"""

import requests
import time
import json
from typing import Dict


BASE_URL = "http://localhost:8005"
CAMERA_ID = "usb_camera_0"


def test_status():
    """Test status endpoint"""
    print("\n🧪 Testing status endpoint...")
    
    response = requests.get(f"{BASE_URL}/api/v1/instant-detection/status")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_start_detection():
    """Test starting instant detection"""
    print(f"\n🧪 Testing start detection for camera {CAMERA_ID}...")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/instant-detection/start/{CAMERA_ID}"
    )
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Started: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_get_results(iterations: int = 3):
    """Test getting instant detection results"""
    print(f"\n🧪 Testing results endpoint ({iterations} iterations)...")
    
    for i in range(iterations):
        print(f"\n📊 Iteration {i+1}/{iterations}")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/instant-detection/results/{CAMERA_ID}"
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Print summary
            print(f"✅ Got results:")
            print(f"   Timestamp: {data.get('timestamp')}")
            print(f"   Faces detected: {data.get('total_faces_detected', 0)}")
            print(f"   People detected: {len(data.get('person_objects', []))}")
            print(f"   Processing time: {data.get('processing_time_seconds', 0):.2f}s")
            
            # Print person details
            for idx, person in enumerate(data.get('person_objects', [])):
                age_gender = person.get('age_gender', {})
                print(f"   Person {idx+1}:")
                print(f"     - Faces: {person.get('face_count', 0)}")
                print(f"     - Confidence: {person.get('avg_confidence', 0):.2f}")
                print(f"     - Age: {age_gender.get('age_range', 'unknown')}")
                print(f"     - Gender: {age_gender.get('gender', 'unknown')}")
        
        elif response.status_code == 404:
            print("⚠️  No results yet (waiting for next iteration)")
        else:
            print(f"❌ Error: {response.text}")
        
        # Wait before next check
        if i < iterations - 1:
            time.sleep(6)  # Wait 6 seconds (sampling interval is 5s)


def test_stop_detection():
    """Test stopping instant detection"""
    print("\n🧪 Testing stop detection...")
    
    response = requests.post(f"{BASE_URL}/api/v1/instant-detection/stop")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Stopped: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def full_test_workflow():
    """Run complete test workflow"""
    print("=" * 60)
    print("INSTANT TEMPORAL DETECTION - TEST SCRIPT")
    print("=" * 60)
    
    # Test 1: Check status
    if not test_status():
        print("\n❌ Status check failed")
        return
    
    # Test 2: Start detection
    if not test_start_detection():
        print("\n❌ Failed to start detection")
        return
    
    print("\n⏳ Waiting 10 seconds for first results...")
    time.sleep(10)
    
    # Test 3: Get results (3 iterations over ~18 seconds)
    test_get_results(iterations=3)
    
    # Test 4: Stop detection
    if not test_stop_detection():
        print("\n❌ Failed to stop detection")
        return
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    try:
        full_test_workflow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        test_stop_detection()
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
