#!/usr/bin/env python3
"""
Progressive Face Detection Terminal Test
Test the progressive endpoint directly using Python requests
"""

import json
import time

import requests

# Configuration
NGINX_BASE_URL = "http://localhost"
TEST_USER_EMAIL = "fresh.user@example.com"
TEST_USER_PASSWORD = "NewPassword234!"
TARGET_VIDEO_ID = "11"  # From previous notebook testing


def main():
    print("🔍 === PROGRESSIVE FACE DETECTION TERMINAL TEST ===")

    # Step 1: Authenticate
    print("Step 1: Authenticating...")
    auth_url = f"{NGINX_BASE_URL}/api/v1/users/login"
    auth_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        auth_response = requests.post(
            auth_url, data=auth_data, headers=auth_headers, timeout=10
        )
        print(f"Auth status: {auth_response.status_code}")

        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            auth_token = auth_result.get("access_token")
            print(f"✅ Authentication successful!")
            print(f"Token preview: {auth_token[:50]}...")

            # Step 2: Test frame-based face detection (the actual progressive endpoint)
            print("\nStep 2: Testing frame-based face detection...")
            frame_number = 150  # Test frame 150 (known to have faces)
            progressive_url = f"{NGINX_BASE_URL}/api/v1/stream/faces/{TARGET_VIDEO_ID}/frame/{frame_number}"
            print(f"Endpoint: {progressive_url}")

            headers = {
                "Authorization": f"Bearer {auth_token}",
            }

            params = {
                "confidence_threshold": 0.5,
            }

            print(
                f"Testing frame {frame_number} with confidence_threshold: {params['confidence_threshold']}"
            )

            start_time = time.time()
            progressive_response = requests.get(
                progressive_url, headers=headers, params=params, timeout=30
            )
            processing_time = time.time() - start_time

            print(f"Response status: {progressive_response.status_code}")
            print(f"Processing time: {processing_time:.2f}s")

            if progressive_response.status_code == 200:
                results = progressive_response.json()
                print("\n🎉 SUCCESS! Frame-based face detection worked!")
                print("Results summary:")
                print(f"  - Frame number: {results.get('frame_number', frame_number)}")
                print(f"  - Total faces detected: {results.get('total_faces', 0)}")
                print(f"  - Detection time: {results.get('detection_time', 0):.3f}s")
                print(f"  - Method used: {results.get('method', 'unknown')}")

                # Show detected faces
                faces = results.get("faces", [])
                if faces:
                    print(f"\nDetected faces in frame {frame_number}:")
                    for j, face in enumerate(faces):
                        confidence = face.get("confidence", 0)
                        bbox = face.get("bounding_box", [])
                        method = face.get("method", "unknown")
                        print(
                            f"  Face {j+1}: confidence={confidence:.3f}, "
                            f"method={method}, bbox={bbox}"
                        )
                else:
                    print(f"\nNo faces detected in frame {frame_number}")

                print("\n✅ TERMINAL TEST SUCCESSFUL!")
                return True

            else:
                print(
                    f"❌ Progressive detection failed: {progressive_response.status_code}"
                )
                print(f"Response: {progressive_response.text[:200]}...")
                return False

        else:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(f"Response: {auth_response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"⏱️ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
