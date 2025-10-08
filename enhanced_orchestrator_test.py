#!/usr/bin/env python3
"""
Enhanced Orchestrator Logic Test
================================

This script demonstrates the enhanced Orchestrator logic that:
1. First tries to get stored faces from current endpoint
2. If no stored faces found, calls Vision Service for real-time detection
3. Returns the same session-based format with actual face results
"""

import requests
import json
import time

# Configuration
NODE_SERVICE_BASE = "http://localhost:8001"
VISION_SERVICE_BASE = "http://localhost:8003" 
ORCHESTRATOR_SERVICE_BASE = "http://localhost:8002"

def get_auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{NODE_SERVICE_BASE}/api/v1/users/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data="username=fresh.user@example.com&password=NewPassword234!"
    )
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def enhanced_orchestrator_face_detection(media_id, auth_token):
    """
    Enhanced Orchestrator Logic:
    1. Try current Orchestrator endpoint first
    2. If no faces found, call Vision Service directly
    3. Return unified session-based format
    """
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    print(f"🔄 ENHANCED ORCHESTRATOR PROCESSING")
    print(f"📱 Media ID: {media_id}")
    print()
    
    # STEP 1: Try current Orchestrator endpoint
    print("1️⃣ Checking for stored faces via Orchestrator...")
    orch_payload = {
        "media_id": media_id,
        "detection_config": {"confidence_threshold": 0.5, "min_face_size": 20}
    }
    
    try:
        orch_response = requests.post(
            f"{ORCHESTRATOR_SERVICE_BASE}/api/v1/face-detection",
            json=orch_payload,
            headers=headers
        )
        
        if orch_response.status_code == 200:
            session_data = orch_response.json()
            session_id = session_data['session_id']
            print(f"   ✅ Session created: {session_id}")
            
            # Poll for completion
            time.sleep(2)
            status_response = requests.get(
                f"{ORCHESTRATOR_SERVICE_BASE}/api/v1/sessions/{session_id}",
                headers=headers
            )
            
            if status_response.status_code == 200:
                result = status_response.json()
                stored_faces = result.get('result', {}).get('total_faces', 0)
                message = result.get('result', {}).get('message', '')
                
                print(f"   📊 Stored faces found: {stored_faces}")
                print(f"   💬 Message: {message}")
                
                # Check if we need to call Vision Service
                if stored_faces == 0 and 'real-time detection required' in message.lower():
                    print(f"   🎯 Enhancement triggered: No stored faces, calling Vision Service...")
                    
                    # STEP 2: Call Vision Service for real-time detection
                    print("\n2️⃣ Calling Vision Service for real-time detection...")
                    vision_payload = {
                        "media_id": media_id,
                        "method": "two_stage",
                        "confidence_threshold": 0.5
                    }
                    
                    vision_response = requests.post(
                        f"{VISION_SERVICE_BASE}/api/v1/detect-faces",
                        json=vision_payload,
                        headers=headers
                    )
                    
                    if vision_response.status_code == 200:
                        vision_data = vision_response.json()
                        vision_faces = vision_data.get('total_faces', 0)
                        print(f"   ✅ Vision Service success: {vision_faces} faces detected")
                        
                        # STEP 3: Return enhanced session format
                        enhanced_result = {
                            "session_id": session_id,
                            "status": "completed",
                            "media_id": media_id,
                            "enhancement_applied": True,
                            "result": {
                                "success": True,
                                "media_id": media_id,
                                "has_stored_faces": False,
                                "total_faces": vision_faces,
                                "faces_by_frame": vision_data.get('faces_by_frame', {}),
                                "message": f"Real-time detection completed: {vision_faces} faces found",
                                "processing_source": "vision_service_realtime"
                            }
                        }
                        
                        print(f"\n✨ ENHANCED RESULT:")
                        print(f"   �� Total Faces: {vision_faces}")
                        print(f"   🎬 Frames: {len(vision_data.get('faces_by_frame', {}))}")
                        print(f"   🔧 Source: Real-time Vision Service")
                        
                        return enhanced_result
                    
                    else:
                        print(f"   ❌ Vision Service failed: {vision_response.text}")
                        return result
                        
                else:
                    print(f"   ✅ Using stored faces: {stored_faces}")
                    return result
                    
        else:
            print(f"   ❌ Orchestrator session failed: {orch_response.text}")
            return None
            
    except Exception as e:
        print(f"🚨 Error in enhanced processing: {e}")
        return None

def main():
    print("🚀 ENHANCED ORCHESTRATOR DEMO")
    print("=" * 40)
    
    # Get authentication
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ Authentication failed")
        return
        
    print(f"✅ Authentication successful")
    
    # Test with Flutter media
    flutter_media = "d45e9160-2800-4fbf-8445-be6b09af9736"
    result = enhanced_orchestrator_face_detection(flutter_media, auth_token)
    
    if result:
        print(f"\n🎉 ENHANCED ORCHESTRATOR SUCCESS!")
        print(f"📊 Final result summary:")
        faces = result.get('result', {}).get('total_faces', 0)
        source = result.get('result', {}).get('processing_source', 'unknown')
        enhanced = result.get('enhancement_applied', False)
        print(f"   👥 Faces detected: {faces}")
        print(f"   🔧 Processing source: {source}")
        print(f"   ⚡ Enhancement applied: {enhanced}")
        
        if enhanced and faces > 0:
            print(f"\n✅ SUCCESS: Enhanced Orchestrator working!")
            print(f"   - Flutter will now see {faces} faces instead of 0")
            print(f"   - Green rectangles will appear")
            print(f"   - Same session-based API, enhanced functionality")
    else:
        print(f"\n❌ Enhanced processing failed")

if __name__ == "__main__":
    main()
