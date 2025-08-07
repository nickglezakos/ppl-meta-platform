#!/usr/bin/env python3
"""
Quick test of the new aggressive preprocessing logic
"""

import os

import requests


def test_preprocessing_decision():
    """Test if preprocessing logic now correctly identifies need for processing"""

    print("🧪 Testing Aggressive Preprocessing Logic")
    print("=" * 50)

    # Test the video info endpoint first to see analysis
    test_video = (
        "/Users/nickgklezakos/Documents/ppl-meta-code/009-indoors-bodycam-line.mp4"
    )

    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        print("Please ensure you have the test video file")
        return False

    try:
        print(f"📁 Testing with video: {os.path.basename(test_video)}")
        print(
            f"📊 Original file size: {os.path.getsize(test_video):,} bytes ({os.path.getsize(test_video)/1024/1024:.1f}MB)"
        )

        # Upload and analyze with new preprocessing
        print("\n🔄 Testing upload-and-analyze with aggressive preprocessing...")

        with open(test_video, "rb") as f:
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
                timeout=300,  # 5 minutes for processing
            )

        if response.status_code == 200:
            result = response.json()

            print("✅ Analysis completed!")

            detection_summary = result.get("detection_summary", {})
            print(f"\n📊 Detection Results:")
            print(
                f"   • Total faces detected: {detection_summary.get('total_faces_detected', 'N/A')}"
            )
            print(
                f"   • Frames analyzed: {detection_summary.get('frames_analyzed', 'N/A')}"
            )

            # Check if file was processed
            file_info = result.get("file_info", {})
            final_size = file_info.get("file_size", 0)
            print(
                f"   • Final file size: {final_size:,} bytes ({final_size/1024/1024:.1f}MB)"
            )

            pipeline_steps = result.get("pipeline_steps", [])
            print(f"\n🔄 Pipeline Steps:")
            for step in pipeline_steps:
                print(f"   {step}")

            # Check for preprocessing indicators
            preprocessing_mentioned = any(
                "preprocess" in step.lower() for step in pipeline_steps
            )
            print(
                f"\n🔧 Preprocessing occurred: {'✅ YES' if preprocessing_mentioned else '❌ NO'}"
            )

            return detection_summary.get("total_faces_detected", 0) > 0

        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_preprocessing_decision()
    if success:
        print("\n🎉 SUCCESS: Face detection working with preprocessing!")
    else:
        print("\n❌ FAILED: Still no faces detected")
