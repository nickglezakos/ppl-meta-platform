#!/usr/bin/env python3
"""
Simple test for frame rate optimization using requests.
"""
import time

import requests


def test_frame_rate_optimization():
    """Test the frame rate optimization feature."""

    print("🧪 Frame Rate Optimization Test")
    print("=" * 50)
    print()

    # Test creating a simple workflow with different FPS settings
    test_cases = [
        {"fps": 1, "desc": "1 FPS - Maximum optimization"},
        {"fps": 3, "desc": "3 FPS - Default setting"},
        {"fps": 10, "desc": "10 FPS - Higher quality"},
    ]

    for i, test in enumerate(test_cases, 1):
        fps = test["fps"]
        desc = test["desc"]

        print(f"Test {i}: {desc}")

        # Test workflow creation with frame rate parameter
        workflow_data = {
            "workflow_name": f"fps_test_{fps}",
            "media_ids": [],
            "detection_method": "two_stage",
            "confidence_threshold": 0.5,
            "frames_per_second": fps,  # 🎯 KEY: Test parameter
            "auto_trigger_ppl_thread": False,
        }

        start_time = time.time()

        try:
            url = "http://localhost:8000/api/v1/face-detection/workflows"
            response = requests.post(
                url,
                json=workflow_data,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                workflow_id = result.get("workflow_id", "N/A")
                print(f"  ✅ Created workflow {workflow_id} in {elapsed:.2f}s")
                print(f"  📊 FPS setting: {fps}")
            else:
                print(f"  ❌ Error {response.status_code}: {response.text[:100]}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")

        print()

    print("🎯 Frame Rate Test Completed!")


if __name__ == "__main__":
    test_frame_rate_optimization()
