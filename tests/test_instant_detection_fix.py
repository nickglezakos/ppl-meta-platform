#!/usr/bin/env python3
"""
Test script to verify instant detection fix is working correctly.

This script:
1. Tests the single-frame endpoint with known frames containing faces
2. Compares results with Enhanced Logic V2 to ensure consistency
3. Provides clear pass/fail results

Usage:
    cd ppl-meta-cameras
    source venv/bin/activate
    python ../test_instant_detection_fix.py
"""

import requests
import cv2
import sys

def test_instant_detection_fix():
    """Test that single-frame endpoint now detects faces correctly."""
    
    print("=" * 80)
    print("🧪 INSTANT DETECTION FIX VERIFICATION TEST")
    print("=" * 80)
    print()
    
    # Login
    print("1️⃣ Authenticating...")
    try:
        auth_response = requests.post(
            'http://localhost:8001/api/v1/users/login',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data='username=fresh.user@example.com&password=NewPassword234!',
            timeout=5
        )
        TOKEN = auth_response.json()['access_token']
        print("   ✅ Authentication successful\n")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return False
    
    # Use a known video with faces
    video_uuid = "fd84de88-8824-4bf1-830e-6469a1afd2ec"
    
    # Get Enhanced Logic V2 results
    print("2️⃣ Getting Enhanced Logic V2 baseline results...")
    try:
        response = requests.get(
            f'http://localhost:8002/person-objects/{video_uuid}',
            headers={'Authorization': f'Bearer {TOKEN}'},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed to get Enhanced Logic V2 results: {response.status_code}")
            return False
        
        result = response.json()
        total_faces = result.get('total_faces', 0)
        print(f"   ✅ Enhanced Logic V2: {total_faces} faces detected\n")
        
        if total_faces == 0:
            print("   ⚠️  Warning: Test video has 0 faces. Using different video may be needed.")
            return False
        
        # Extract frame numbers where faces were detected
        face_frames = []
        if result.get('person_groups'):
            for person in result['person_groups']:
                if person.get('representative_faces'):
                    for face_obj in person['representative_faces']:
                        face_data = face_obj.get('face_data', {})
                        frame_num = face_data.get('frame_number')
                        if frame_num is not None:
                            face_frames.append({
                                'frame': frame_num,
                                'bbox': face_data.get('bbox'),
                                'confidence': face_data.get('confidence')
                            })
        
        if not face_frames:
            print("   ❌ No frame numbers found in Enhanced Logic V2 results")
            return False
        
        print(f"   Found {len(face_frames)} faces across multiple frames")
        print(f"   Testing with frames: {[f['frame'] for f in face_frames[:3]]}\n")
        
    except Exception as e:
        print(f"   ❌ Error getting Enhanced Logic V2 results: {e}")
        return False
    
    # Download video
    print("3️⃣ Downloading test video...")
    try:
        video_response = requests.get(
            f'http://localhost:8000/api/v1/media/stream/{video_uuid}',
            headers={'Authorization': f'Bearer {TOKEN}'},
            stream=True,
            timeout=30
        )
        
        with open('/tmp/test_instant_detection.mp4', 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("   ✅ Video downloaded\n")
    except Exception as e:
        print(f"   ❌ Failed to download video: {e}")
        return False
    
    # Test single-frame endpoint
    print("4️⃣ Testing single-frame endpoint with frames containing faces...\n")
    print("-" * 80)
    
    cap = cv2.VideoCapture('/tmp/test_instant_detection.mp4')
    test_frames = face_frames[:3]  # Test first 3 frames
    
    success_count = 0
    fail_count = 0
    
    for face_info in test_frames:
        frame_num = face_info['frame']
        expected_bbox = face_info['bbox']
        
        # Extract frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            print(f"Frame {frame_num}: ❌ Failed to extract frame")
            fail_count += 1
            continue
        
        # Test single-frame endpoint
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            files = {'file': ('frame.jpg', buffer.tobytes(), 'image/jpeg')}
            
            single_response = requests.post(
                'http://localhost:8003/faces/detect-single-frame',
                files=files,
                timeout=10
            )
            
            if single_response.status_code == 200:
                single_result = single_response.json()
                detected = single_result.get('total_faces', 0)
                
                if detected > 0:
                    print(f"Frame {frame_num}: ✅ PASS - Detected {detected} face(s)")
                    print(f"             Enhanced Logic V2 bbox: {expected_bbox}")
                    if single_result.get('faces'):
                        sf = single_result['faces'][0]
                        print(f"             Single-frame bbox:     {sf['bbox']}")
                    success_count += 1
                else:
                    print(f"Frame {frame_num}: ❌ FAIL - Detected 0 faces")
                    print(f"             Enhanced Logic V2 found face at: {expected_bbox}")
                    fail_count += 1
            else:
                print(f"Frame {frame_num}: ❌ FAIL - API error {single_response.status_code}")
                fail_count += 1
                
        except Exception as e:
            print(f"Frame {frame_num}: ❌ FAIL - Exception: {e}")
            fail_count += 1
        
        print("-" * 80)
    
    cap.release()
    
    # Results
    print()
    print("=" * 80)
    print("📊 TEST RESULTS")
    print("=" * 80)
    print(f"Total tests:  {success_count + fail_count}")
    print(f"Passed:       {success_count} ✅")
    print(f"Failed:       {fail_count} ❌")
    print()
    
    if fail_count == 0:
        print("🎉 SUCCESS! Single-frame endpoint is working correctly!")
        print()
        print("Next steps:")
        print("  1. Start a recording with instant detection enabled")
        print("  2. Verify the instant detection counter shows >0 people")
        print("  3. Confirm saved video still processes correctly")
        print()
        return True
    else:
        print("⚠️  PARTIAL SUCCESS: Some tests failed.")
        print()
        print("This could mean:")
        print("  • Vision Service needs restart")
        print("  • Dlib validation is too strict for some frames")
        print("  • Further debugging needed")
        print()
        return False


if __name__ == "__main__":
    success = test_instant_detection_fix()
    sys.exit(0 if success else 1)
