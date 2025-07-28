#!/usr/bin/env python3
"""
Test the new video preprocessing functionality in Mini service.
"""

import json
import sys

import requests


def test_video_preprocessing():
    """Test video preprocessing with the problematic video."""

    print("🧪 Testing Mini Service Video Preprocessing")
    print("=" * 50)

    # Test file path (assuming you have the problematic video)
    test_video_path = (
        "/Users/nickgklezakos/Documents/ppl-meta-code/test-videos/sample_video.mp4"
    )

    try:
        # Check if Mini service is running
        health_response = requests.get("http://localhost:8004/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Mini service not responding")
            return False

        print("✅ Mini service is healthy")

        # Test upload-and-analyze with preprocessing
        print("\n📤 Testing upload-and-analyze with video preprocessing...")

        with open(test_video_path, "rb") as f:
            files = {"file": f}
            params = {
                "confidence_threshold": 0.5,
                "max_faces_per_frame": 10,
                "proximity_threshold": 50.0,
            }

            response = requests.post(
                "http://localhost:8004/api/v1/upload-and-analyze",
                files=files,
                params=params,
                timeout=120,  # 2 minutes for processing
            )

        if response.status_code == 200:
            result = response.json()

            print("✅ Analysis completed successfully!")
            print(f"📊 Results Summary:")

            detection_summary = result.get("detection_summary", {})
            print(f"   • Total frames: {detection_summary.get('total_frames', 'N/A')}")
            print(
                f"   • Frames analyzed: {detection_summary.get('frames_analyzed', 'N/A')}"
            )
            print(
                f"   • Total faces detected: {detection_summary.get('total_faces_detected', 'N/A')}"
            )

            grouping_summary = result.get("face_grouping", {}).get("summary", {})
            print(f"   • Face groups: {grouping_summary.get('total_groups', 'N/A')}")

            pipeline_steps = result.get("pipeline_steps", [])
            print(f"\n🔄 Pipeline Steps:")
            for step in pipeline_steps:
                print(f"   {step}")

            return True
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False

    except FileNotFoundError:
        print(f"❌ Test video not found: {test_video_path}")
        print("Please provide a test video file")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_video_preprocessing()
    sys.exit(0 if success else 1)
