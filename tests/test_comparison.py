#!/usr/bin/env python3
"""
Comprehensive test script to compare Mini Service vs Media Service face detection.
Tests the entire video with configurable frame intervals.
"""

import json
import os
import time
import urllib.parse

import cv2
import requests

# Configuration
MINI_SERVICE_URL = "http://localhost:8004"
NGINX_BASE_URL = "http://localhost"

# Test credentials (update these with valid credentials)
TEST_USER_EMAIL = "fresh.user@example.com"
TEST_USER_PASSWORD = "NewPassword234!"


def authenticate_user(email: str, password: str):
    """
    Authenticate user using the EXACT method from the main application.
    """
    print(f"🔐 Authenticating user: {email}")
    print(f"📡 Using nginx proxy endpoint: {NGINX_BASE_URL}/api/v1/users/login")

    try:
        auth_url = f"{NGINX_BASE_URL}/api/v1/users/login"

        # OAuth2PasswordRequestForm format with proper URL encoding
        auth_data = {"username": email, "password": password}

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(auth_url, data=auth_data, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            access_token = result.get("access_token")
            token_type = result.get("token_type", "bearer")

            print(f"   ✅ Authentication successful!")
            print(f"   🔑 Token type: {token_type}")

            return {
                "success": True,
                "access_token": access_token,
                "token_type": token_type,
                "response": result,
            }
        else:
            print(f"   ❌ Authentication failed: HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "status_code": response.status_code,
            }

    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return {"success": False, "error": str(e)}


def get_video_info(video_path):
    """Get video information including total frames."""
    cap = cv2.VideoCapture(video_path)
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        return {
            "total_frames": total_frames,
            "fps": fps,
            "duration": total_frames / fps if fps > 0 else 0,
        }
    finally:
        cap.release()


def test_mini_service(frame_number, video_path, confidence_threshold=0.5):
    """Test mini service autonomous face detection."""
    try:
        url = f"{MINI_SERVICE_URL}/api/v1/faces/frame/{frame_number}"
        params = {
            "video_path": video_path,
            "confidence_threshold": confidence_threshold,
        }
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "face_count": data.get("total_faces", len(data.get("faces", []))),
                "method": data.get("method", "unknown"),
                "detection_time": data.get("detection_time", 0),
                "raw_response": data,
                "via": "nginx",
            }
        else:
            # Fallback to direct service
            url = f"http://localhost:8004/faces/frame/{frame_number}"
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "face_count": data.get("total_faces", len(data.get("faces", []))),
                    "method": data.get("method", "unknown"),
                    "detection_time": data.get("detection_time", 0),
                    "raw_response": data,
                    "via": "direct",
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": response.text[:200],
                }
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_media_service(
    frame_number, video_uuid, confidence_threshold=0.5, auth_token=None
):
    """Test media service face detection via nginx proxy with authentication."""
    try:
        if not auth_token:
            return {
                "success": False,
                "faces": 0,
                "error": "No authentication token provided",
            }

        # All API requests go through gateway via nginx routing
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        # Try to get face detection for specific frame via gateway
        frame_url = f"{NGINX_BASE_URL}/api/v1/media/stream/faces/{video_uuid}/frame/{frame_number}"
        frame_params = {"confidence_threshold": confidence_threshold}
        frame_response = requests.get(
            frame_url, params=frame_params, headers=headers, timeout=10
        )

        if frame_response.status_code == 200:
            data = frame_response.json()
            return {
                "success": True,
                "faces": data.get("total_faces", len(data.get("faces", []))),
                "detection_time": data.get("detection_time", 0),
                "method": data.get("method", "media_service"),
                "raw_response": data,
            }
        else:
            return {
                "success": False,
                "faces": 0,
                "error": f"Frame detection failed: HTTP {frame_response.status_code}",
            }
    except Exception as e:
        return {
            "success": False,
            "faces": 0,
            "error": f"Media service error: {str(e)}",
        }


def main():
    """Run the comparison test using EXACT notebook frame sampling strategy."""
    print("🔍 Mini Service vs Media Service Comparison Test")
    print("=" * 60)

    # Test configuration - EXACT MATCH to notebook
    video_uuid = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
    video_path = "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/storage/media/4cf362b1-3e05-4e85-81c7-c08a98c7e41b/video/2025/07/54c4666b56ff8b9dbb55abcafbb3c23f.mp4"
    confidence_threshold = 0.5

    # Verify video file exists
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return

    # Get video information
    print("📹 Analyzing video...")
    video_info = get_video_info(video_path)
    total_frames = video_info["total_frames"]
    print(f"   Total frames: {total_frames}")
    print(f"   Duration: {video_info['duration']:.2f} seconds")
    print(f"   FPS: {video_info['fps']:.2f}")

    # Use EXACT notebook sampling strategy: every 10 frames starting from 0
    frame_interval = 10
    frames_to_test = list(range(0, total_frames, frame_interval))

    print(f"🎯 EXACT NOTEBOOK REPLICATION:")
    print(f"   Frame range: 0 to {total_frames}")
    print(f"   Interval: Every {frame_interval} frames")
    print(f"   Generated frames: {len(frames_to_test)}")
    print(f"   Sample frames: {frames_to_test[:10]}...")
    print()

    # Authenticate for media service
    print("🔐 Authenticating for media service...")
    auth_result = authenticate_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
    auth_token = auth_result.get("access_token") if auth_result["success"] else None

    if not auth_token:
        print("❌ Authentication failed, will test mini service only")
        print(f"   Error: {auth_result.get('error', 'Unknown error')}")

    print()

    # Test the ENTIRE video with frame interval 10
    print(f"🚀 FULL VIDEO TEST - Processing all {len(frames_to_test)} frames...")
    print("📊 This will take several minutes to complete the entire video...")
    print()

    results = []
    mini_faces_total = 0
    media_faces_total = 0
    mini_face_frames = 0
    media_face_frames = 0

    for i, frame in enumerate(frames_to_test):
        # Test Mini Service
        mini_result = test_mini_service(frame, video_path, confidence_threshold)
        mini_faces = mini_result.get("face_count", 0) if mini_result["success"] else 0

        # Test Media Service if authenticated
        if auth_token:
            media_result = test_media_service(
                frame, video_uuid, confidence_threshold, auth_token
            )
            media_faces = media_result.get("faces", 0) if media_result["success"] else 0
        else:
            media_result = {"success": False, "faces": 0, "error": "No authentication"}
            media_faces = 0

        # Track results
        if mini_result["success"]:
            mini_faces_total += mini_faces
            if mini_faces > 0:
                mini_face_frames += 1

        if media_result["success"]:
            media_faces_total += media_faces
            if media_faces > 0:
                media_face_frames += 1

        results.append({"frame": frame, "mini": mini_result, "media": media_result})

        # Progress reporting every 10 frames
        if (i + 1) % 10 == 0:
            print(
                f"📈 Progress: {i+1}/{len(frames_to_test)} frames ({(i+1)/len(frames_to_test)*100:.1f}%)"
            )
            print(
                f"   Running totals - Mini: {mini_faces_total} faces, Media: {media_faces_total} faces"
            )

    # Final summary
    print()
    print("📊 COMPLETE VIDEO RESULTS:")
    print(f"   Frames tested: {len(results)}")
    print(
        f"   Mini service total: {mini_faces_total} faces in {mini_face_frames} frames"
    )
    print(
        f"   Media service total: {media_faces_total} faces in {media_face_frames} frames"
    )
    print()

    # Save results
    output_file = "comparison_results_full_video.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_config": {
                    "video_uuid": video_uuid,
                    "video_path": video_path,
                    "confidence_threshold": confidence_threshold,
                    "total_frames": total_frames,
                    "frames_tested": len(frames_to_test),
                    "sampling_strategy": f"every_{frame_interval}_frames_from_0",
                },
                "summary": {
                    "mini_faces_total": mini_faces_total,
                    "mini_face_frames": mini_face_frames,
                    "media_faces_total": media_faces_total,
                    "media_face_frames": media_face_frames,
                },
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\nResults saved to: {output_file}")
    print("✅ FULL VIDEO TEST COMPLETED!")


if __name__ == "__main__":
    main()
