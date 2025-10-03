#!/usr/bin/env python3
"""
Test script for frame rate optimization in face detection endpoints.
"""
import asyncio
import json
import time
from typing import Any, Dict

import aiohttp


async def test_frame_rate_optimization():
    """Test the frame rate optimization feature."""

    # Test configurations
    test_cases = [
        {"frames_per_second": 1, "description": "1 FPS - Maximum optimization"},
        {"frames_per_second": 3, "description": "3 FPS - Default setting"},
        {"frames_per_second": 10, "description": "10 FPS - Higher quality"},
        {"frames_per_second": 30, "description": "30 FPS - Maximum quality"},
    ]

    # Use a test video (assuming we have one from previous tests)
    test_video_path = "/Users/nickgklezakos/Documents/ppl-meta-code/test_video.mp4"

    print("🧪 Frame Rate Optimization Test")
    print("=" * 50)
    print(f"Test video: {test_video_path}")
    print()

    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            fps = test_case["frames_per_second"]
            description = test_case["description"]

            print(f"Test {i}: {description}")
            print(f"Target FPS: {fps}")

            # Prepare the workflow request
            workflow_data = {
                "workflow_name": f"frame_rate_test_{fps}_fps",
                "media_ids": [],  # Will add programmatically if needed
                "detection_method": "two_stage",
                "confidence_threshold": 0.5,
                "frames_per_second": fps,  # 🎯 KEY: Test the new parameter
                "auto_trigger_ppl_thread": False,  # Skip PPL thread for faster testing
            }

            start_time = time.time()

            try:
                # Test via the single media workflow endpoint
                url = (
                    "http://localhost:8000/api/v1/face-detection/workflows/single-media"
                )

                # For testing, we'll create a minimal workflow request
                # In practice, you'd upload media first, but for testing we can use direct service call

                print(f"  📡 Testing with {fps} FPS...")

                async with session.post(
                    url,
                    json=workflow_data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        elapsed = time.time() - start_time

                        print(f"  ✅ Success! Processing time: {elapsed:.2f}s")

                        # Extract processing statistics if available
                        if "workflow_results" in result:
                            workflow_results = result["workflow_results"]
                            if workflow_results and len(workflow_results) > 0:
                                first_result = workflow_results[0]
                                if "detection_result" in first_result:
                                    metadata = first_result["detection_result"].get(
                                        "metadata", {}
                                    )
                                    total_frames = metadata.get("total_frames", "N/A")
                                    processed_frames = metadata.get(
                                        "processed_frames", "N/A"
                                    )
                                    actual_skip = metadata.get(
                                        "actual_skip_interval", "N/A"
                                    )

                                    print(
                                        f"  📊 Frames: {processed_frames}/{total_frames} processed"
                                    )
                                    print(f"  📊 Skip interval: {actual_skip}")

                    else:
                        error_text = await response.text()
                        print(f"  ❌ Error {response.status}: {error_text[:200]}...")

            except Exception as e:
                print(f"  ❌ Exception: {e}")

            print()

    print("🎯 Frame Rate Test Completed!")


if __name__ == "__main__":
    asyncio.run(test_frame_rate_optimization())
