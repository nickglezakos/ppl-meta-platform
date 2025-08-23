#!/usr/bin/env python3
"""
Test script to validate Cython-compiled face detection performance
"""

import json
import os
import time

import requests

# Configuration
CYTHON_URL = "http://localhost:8005"
VIDEO_PATH = "/Users/nickgklezakos/Documents/ppl-meta-code/docs/archive/009-indoors-bodycam-line.mp4"


def test_cython_service():
    """Test the Cython-optimized service"""
    print("=== Testing Cython-Optimized PPL Meta Mini ===")

    # Check if video file exists
    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Video file not found at {VIDEO_PATH}")
        return

    print(f"Video file: {VIDEO_PATH}")
    print(f"Video size: {os.path.getsize(VIDEO_PATH) / (1024*1024):.2f} MB")

    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{CYTHON_URL}/health", timeout=5)
        print(f"Health Status: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # Test root endpoint
    print("\n2. Testing service info...")
    try:
        response = requests.get(f"{CYTHON_URL}/", timeout=5)
        info = response.json()
        print(f"Service: {info['service']} v{info['version']}")
        print(f"Available endpoints: {list(info['endpoints'].keys())}")
    except Exception as e:
        print(f"Service info failed: {e}")
        return

    # Test face detection with video upload
    print("\n3. Testing face detection with Cython-compiled modules...")
    print("Uploading video for analysis...")

    start_time = time.time()

    try:
        with open(VIDEO_PATH, "rb") as video_file:
            files = {"file": ("test_video.mp4", video_file, "video/mp4")}
            data = {
                "max_faces_per_frame": 10,
                "proximity_threshold": 50.0,
                "confidence_threshold": 0.5,
                "frame_interval": 15,
            }

            print("Sending request to Cython service...")
            response = requests.post(
                f"{CYTHON_URL}/api/v1/upload-and-analyze",
                files=files,
                data=data,
                timeout=300,  # 5 minute timeout for processing
            )

            processing_time = time.time() - start_time
            print(f"Processing completed in {processing_time:.2f} seconds")

            if response.status_code == 200:
                result = response.json()

                print("\n=== CYTHON ANALYSIS RESULTS ===")
                print(f"Status: {result.get('status', 'unknown')}")
                print(f"Message: {result.get('message', 'no message')}")

                if "analysis_results" in result:
                    analysis = result["analysis_results"]
                    print(f"Total faces detected: {analysis.get('total_faces', 0)}")
                    print(
                        f"Unique individuals: {analysis.get('unique_individuals', 0)}"
                    )
                    print(f"Frames processed: {analysis.get('frames_processed', 0)}")
                    print(
                        f"Processing time: {analysis.get('processing_time_seconds', 0):.2f}s"
                    )

                    if "face_groups" in analysis:
                        print(f"Face groups: {len(analysis['face_groups'])}")
                        for i, group in enumerate(
                            analysis["face_groups"][:3]
                        ):  # Show first 3 groups
                            print(f"  Group {i+1}: {group.get('face_count', 0)} faces")

                print(f"\nTotal request time: {processing_time:.2f} seconds")
                print("SUCCESS: Cython-compiled modules processed video successfully!")

                # Save results for comparison
                with open("cython_test_results.json", "w") as f:
                    json.dump(
                        {
                            "processing_time": processing_time,
                            "results": result,
                            "timestamp": time.time(),
                        },
                        f,
                        indent=2,
                    )

            else:
                print(f"ERROR: Request failed with status {response.status_code}")
                print(f"Response: {response.text}")

    except requests.exceptions.Timeout:
        print("ERROR: Request timed out - video processing took too long")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    test_cython_service()
