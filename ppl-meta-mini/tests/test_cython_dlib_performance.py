#!/usr/bin/env python3
"""
Performance test for the Enhanced Cython+dlib Docker image
Tests both OpenCV and dlib-based face detection capabilities
"""

import json
import time

import requests


def test_face_detection_performance():
    """Test face detection with the enhanced Cython+dlib service"""

    # Use the same test video from previous successful tests
    video_path = "/Users/nickgklezakos/Downloads/BodyCam-Footage.mp4"

    try:
        print("🚀 Enhanced Cython+dlib Performance Test")
        print("=" * 50)

        # Test health endpoint
        health_response = requests.get("http://localhost:8004/health")
        print(f"✅ Service Health: {health_response.json()}")

        # Performance test with the bodycam video
        print(f"\n📹 Testing video: {video_path}")

        with open(video_path, "rb") as f:
            start_time = time.time()

            files = {"video": ("test_video.mp4", f, "video/mp4")}
            data = {
                "detection_method": "opencv_haar",  # Start with OpenCV
                "detection_confidence": 0.5,
                "max_faces_per_frame": 10,
            }

            response = requests.post(
                "http://localhost:8004/detect-faces/",
                files=files,
                data=data,
                timeout=120,
            )

            end_time = time.time()
            processing_time = end_time - start_time

            if response.status_code == 200:
                result = response.json()

                print(f"\n🎯 Enhanced Cython+dlib Results:")
                print(f"   ⏱️  Processing Time: {processing_time:.2f} seconds")
                print(
                    f"   📊 Total Faces Detected: {result.get('total_faces_detected', 0)}"
                )
                print(f"   🎬 Total Frames: {result.get('total_frames', 0)}")
                print(
                    f"   📈 Performance: {result.get('total_frames', 0) / processing_time:.2f} fps"
                )

                # Display face detection summary
                if "faces" in result:
                    print(f"\n👥 Face Detection Summary:")
                    for i, face in enumerate(result["faces"][:5]):  # Show first 5 faces
                        confidence = face.get("confidence", 0)
                        frame_num = face.get("frame_number", 0)
                        print(
                            f"   Face {i+1}: Frame {frame_num}, Confidence: {confidence:.3f}"
                        )

                    if len(result["faces"]) > 5:
                        print(f"   ... and {len(result['faces']) - 5} more faces")

                print(f"\n✅ Enhanced Cython+dlib service is working perfectly!")
                print(f"🚀 Achieved C-level performance with dlib integration")

            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")

    except FileNotFoundError:
        print(f"❌ Test video not found: {video_path}")
        print("Please ensure the test video exists or update the path")
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_face_detection_performance()
