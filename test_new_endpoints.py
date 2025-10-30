#!/usr/bin/env python3
"""
Test script for new Phase 5 & 6 endpoints
Tests the individuals list and aggregated analysis endpoints

Usage:
    python test_new_endpoints.py [--create-session]
    
    If --create-session is provided, creates a new tracking session first
    Otherwise, uses existing session UUID from command line
"""

import sys
import requests
import json
from datetime import datetime
import time


def get_jwt_token():
    """Get JWT token by logging in to Node service"""
    print("\n" + "="*60)
    print("AUTHENTICATION: Getting JWT Token")
    print("="*60)
    
    url = "http://localhost:8001/api/v1/users/login"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "username": "fresh.user@example.com",
        "password": "NewPassword234!"
    }
    
    print(f"\n📡 POST {url}")
    print(f"👤 User: fresh.user@example.com")
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            jwt_token = token_data.get('access_token')
            print(f"\n✅ SUCCESS! Got JWT token")
            print(f"Token: {jwt_token[:30]}... (truncated)")
            return jwt_token
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return None


def create_tracking_session(jwt_token):
    """Create a new tracking session with the specified parameters"""
    print("\n" + "="*60)
    print("SESSION CREATION: Creating Tracking Session")
    print("="*60)
    
    url = "http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    # Using the exact parameters from the document
    payload = {
        "collections": ["usb_camera_0"],
        "start_time": "2025-10-13T08:06:00",  # Athens time (naive)
        "end_time": "2025-10-29T08:06:00",    # Athens time (naive)
        "background_processing": True,
        "algorithm_config": {
            "max_gap_seconds": 10,
            "iou_threshold": 0.3,
            "min_overlap_confidence": 0.5
        }
    }
    
    print(f"\n📡 POST {url}")
    print(f"📋 Collections: {payload['collections']}")
    print(f"📅 Start Time: {payload['start_time']}")
    print(f"📅 End Time: {payload['end_time']}")
    print(f"🔄 Background Processing: {payload['background_processing']}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            session_uuid = data.get('session_uuid')
            status = data.get('status')
            
            print(f"\n✅ SUCCESS! Session created")
            print(f"Session UUID: {session_uuid}")
            print(f"Status: {status}")
            print(f"Message: {data.get('message')}")
            
            # Wait for session to complete
            print(f"\n⏳ Waiting for session to complete...")
            completed_session = wait_for_session_completion(session_uuid, jwt_token)
            
            return session_uuid if completed_session else None
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return None


def wait_for_session_completion(session_uuid, jwt_token, max_wait=60):
    """Poll session status until completed or timeout"""
    url = f"http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    poll_count = 0
    
    while time.time() - start_time < max_wait:
        poll_count += 1
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                total_videos = data.get('total_videos', 0)
                individuals_found = data.get('individuals_found', 0)
                
                print(f"  Poll #{poll_count}: status={status}, videos={total_videos}, individuals={individuals_found}")
                
                if status == 'completed':
                    print(f"\n✅ Session completed!")
                    print(f"   Total Videos: {total_videos}")
                    print(f"   Individuals Found: {individuals_found}")
                    print(f"   Processing Time: {time.time() - start_time:.2f}s")
                    return data
                elif status == 'failed':
                    print(f"\n❌ Session failed!")
                    return None
                
                # Wait before next poll
                time.sleep(2)
            else:
                print(f"\n❌ Status check failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"\n❌ Polling error: {e}")
            return None
    
    print(f"\n⚠️  Timeout waiting for session completion ({max_wait}s)")
    return None


def test_phase_5_individuals_list(session_uuid, jwt_token):
    """Test Phase 5: Get individuals list from session"""
    print("\n" + "="*60)
    print("PHASE 5 TEST: Get Session Individuals")
    print("="*60)
    
    url = f"http://localhost:8080/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n📡 GET {url}")
    print(f"🔑 Auth: Bearer {jwt_token[:20]}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Session UUID: {data.get('session_uuid')}")
            print(f"Total Individuals: {data.get('total_individuals')}")
            
            individuals = data.get('individuals', [])
            if individuals:
                print(f"\n📋 Individuals Found:")
                for i, ind in enumerate(individuals, 1):
                    print(f"\n  Individual #{i}:")
                    print(f"    UUID: {ind.get('individual_uuid')}")
                    print(f"    ID: {ind.get('individual_id')}")
                    print(f"    Appearances: {ind.get('total_appearances')}")
                    print(f"    Videos: {ind.get('total_videos')}")
                    print(f"    Confidence: {ind.get('confidence_score'):.2f}")
                    print(f"    First Seen: {ind.get('first_seen')}")
                    print(f"    Last Seen: {ind.get('last_seen')}")
                
                # Return first individual UUID for Phase 6 test
                return individuals[0].get('individual_uuid')
            else:
                print("\n⚠️  No individuals found in session")
                return None
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return None


def test_phase_6_aggregated_analysis(session_uuid, individual_uuid, jwt_token):
    """Test Phase 6: Get aggregated individual analysis"""
    print("\n" + "="*60)
    print("PHASE 6 TEST: Get Aggregated Individual Analysis")
    print("="*60)
    
    url = f"http://localhost:8080/api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis"
    params = {"session_uuid": session_uuid}
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n📡 GET {url}")
    print(f"🔑 Auth: Bearer {jwt_token[:20]}...")
    print(f"📋 Params: session_uuid={session_uuid}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Individual UUID: {data.get('individual_uuid')}")
            print(f"Individual ID: {data.get('individual_id')}")
            print(f"Session UUID: {data.get('session_uuid')}")
            
            # Aggregated Metrics
            print(f"\n📊 Aggregated Metrics:")
            print(f"  Total Appearances: {data.get('total_appearances')}")
            print(f"  Unique Videos: {data.get('unique_videos')}")
            print(f"  First Seen: {data.get('first_seen')}")
            print(f"  Last Seen: {data.get('last_seen')}")
            print(f"  Total Duration: {data.get('total_duration_seconds')} seconds")
            print(f"  Average Confidence: {data.get('average_confidence')}")
            
            # Appearances
            appearances = data.get('appearances', [])
            print(f"\n📹 Appearances: {len(appearances)}")
            for i, app in enumerate(appearances[:3], 1):  # Show first 3
                print(f"\n  Appearance #{i}:")
                print(f"    Individual UUID: {app.get('individual_uuid')}")
                print(f"    Video UUID: {app.get('video_uuid')}")
                print(f"    Person Object UUID: {app.get('person_object_uuid')}")
                print(f"    Start: {app.get('start_timestamp')}")
                print(f"    End: {app.get('end_timestamp')}")
                print(f"    Confidence: {app.get('confidence_score')}")
                if app.get('entry_bbox'):
                    print(f"    Entry BBox: {app.get('entry_bbox')}")
                if app.get('exit_bbox'):
                    print(f"    Exit BBox: {app.get('exit_bbox')}")
            
            if len(appearances) > 3:
                print(f"\n  ... and {len(appearances) - 3} more appearances")
            
            # Person Object UUIDs
            person_uuids = data.get('person_object_uuids', [])
            print(f"\n👤 Person Object UUIDs: {len(person_uuids)}")
            for i, uuid in enumerate(person_uuids[:3], 1):
                print(f"  {i}. {uuid}")
            if len(person_uuids) > 3:
                print(f"  ... and {len(person_uuids) - 3} more")
            
            print(f"\n📅 Analysis Timestamp: {data.get('analysis_timestamp')}")
            
            return True
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    """Main test runner"""
    
    print("\n" + "="*60)
    print("PPL Meta Platform - New Endpoints Test")
    print("Phase 5 & 6 Implementation Verification")
    print("="*60)
    print(f"Test Time: {datetime.now().isoformat()}")
    print(f"Gateway URL: http://localhost:8080")
    print(f"Node URL: http://localhost:8001")
    print(f"vmeta URL: http://localhost:8008")
    
    # Step 1: Get JWT token
    jwt_token = get_jwt_token()
    if not jwt_token:
        print("\n❌ Failed to get JWT token. Exiting.")
        sys.exit(1)
    
    # Step 2: Create tracking session with document parameters
    print("\n" + "="*60)
    print("Creating tracking session with document parameters:")
    print("  Collections: usb_camera_0")
    print("  Start Time: 2025-10-13 08:06:00 (Athens time)")
    print("  End Time: 2025-10-29 08:06:00 (Athens time)")
    print("="*60)
    
    session_uuid = create_tracking_session(jwt_token)
    if not session_uuid:
        print("\n❌ Failed to create tracking session. Exiting.")
        sys.exit(1)
    
    # Step 3: Test Phase 5
    individual_uuid = test_phase_5_individuals_list(session_uuid, jwt_token)
    
    # Step 4: Test Phase 6
    if individual_uuid:
        test_phase_6_aggregated_analysis(session_uuid, individual_uuid, jwt_token)
    else:
        print("\n⚠️  Skipping Phase 6 test - no individuals found")
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
