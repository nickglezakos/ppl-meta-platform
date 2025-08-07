#!/usr/bin/env python3
"""
Test script to compare Mini Service vs Media Service face detection results.
This script tests the same frames on both services to identify differences.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

# Configuration
MINI_SERVICE_URL = "http://localhost:8004"
MEDIA_SERVICE_URL = "http://localhost:8000"
NGINX_PROXY_URL = "http://localhost"

# Test parameters
CONFIDENCE_THRESHOLD = 0.5
TEST_FRAMES = [
    105,
    108,
    111,
    114,
    117,
    120,
    135,
    141,
    150,
    180,
    255,
    330,
]  # Sample frames from your test


def test_mini_service_frame(frame_number: int, video_path: str) -> Dict[str, Any]:
    """Test a single frame using the Mini Service."""
    try:
        url = f"{MINI_SERVICE_URL}/faces/frame/{frame_number}"
        params = {
            "video_path": video_path,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
        }

        start_time = time.time()
        response = requests.get(url, params=params, timeout=10)
        request_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "faces": data.get("faces", []),
                "total_faces": data.get("total_faces", 0),
                "detection_time": data.get("detection_time", 0),
                "method": data.get("method", "unknown"),
                "request_time": request_time,
                "frame_number": frame_number,
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "request_time": request_time,
                "frame_number": frame_number,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "request_time": 0,
            "frame_number": frame_number,
        }


def test_media_service_frame(
    frame_number: int, video_uuid: str, auth_token: str = None
) -> Dict[str, Any]:
    """Test a single frame using the Media Service."""
    try:
        # Try both direct media service and nginx proxy
        urls_to_try = [
            f"{NGINX_PROXY_URL}/api/v1/stream/faces/{video_uuid}/frame/{frame_number}",
            f"{MEDIA_SERVICE_URL}/api/v1/stream/faces/{video_uuid}/frame/{frame_number}",
        ]

        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        params = {"confidence_threshold": CONFIDENCE_THRESHOLD}

        for url in urls_to_try:
            try:
                start_time = time.time()
                response = requests.get(url, params=params, headers=headers, timeout=10)
                request_time = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "faces": data.get("faces", []),
                        "total_faces": data.get("total_faces", 0),
                        "detection_time": data.get("detection_time", 0),
                        "method": data.get("method", "unknown"),
                        "request_time": request_time,
                        "frame_number": frame_number,
                        "url_used": url,
                    }
                elif response.status_code == 401 and auth_token:
                    continue  # Try next URL without auth
            except Exception:
                continue  # Try next URL

        return {
            "success": False,
            "error": f"All URLs failed. Last status: {response.status_code}",
            "request_time": request_time,
            "frame_number": frame_number,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "request_time": 0,
            "frame_number": frame_number,
        }


def compare_face_results(mini_result: Dict, media_result: Dict) -> Dict[str, Any]:
    """Compare face detection results between mini and media services."""
    comparison = {
        "frame_number": mini_result.get("frame_number"),
        "mini_faces": (
            mini_result.get("total_faces", 0) if mini_result.get("success") else 0
        ),
        "media_faces": (
            media_result.get("total_faces", 0) if media_result.get("success") else 0
        ),
        "difference": 0,
        "mini_success": mini_result.get("success", False),
        "media_success": media_result.get("success", False),
        "mini_method": mini_result.get("method", "unknown"),
        "media_method": media_result.get("method", "unknown"),
        "mini_detection_time": mini_result.get("detection_time", 0),
        "media_detection_time": media_result.get("detection_time", 0),
        "bbox_comparison": None,
    }

    if comparison["mini_success"] and comparison["media_success"]:
        comparison["difference"] = comparison["mini_faces"] - comparison["media_faces"]

        # Compare bounding boxes if both have faces
        if comparison["mini_faces"] > 0 and comparison["media_faces"] > 0:
            mini_faces = mini_result.get("faces", [])
            media_faces = media_result.get("faces", [])
            comparison["bbox_comparison"] = {
                "mini_bboxes": [face.get("bbox") for face in mini_faces],
                "media_bboxes": [face.get("bbox") for face in media_faces],
            }

    return comparison


def print_comparison_summary(comparisons: List[Dict[str, Any]]):
    """Print a summary of the comparison results."""
    print("\n" + "=" * 80)
    print("🔍 MINI SERVICE vs MEDIA SERVICE COMPARISON SUMMARY")
    print("=" * 80)

    successful_comparisons = [
        c for c in comparisons if c["mini_success"] and c["media_success"]
    ]

    if not successful_comparisons:
        print("❌ No successful comparisons found!")
        return

    print(f"\n📊 Successfully compared {len(successful_comparisons)} frames")

    # Count differences
    identical_results = [c for c in successful_comparisons if c["difference"] == 0]
    mini_higher = [c for c in successful_comparisons if c["difference"] > 0]
    media_higher = [c for c in successful_comparisons if c["difference"] < 0]

    print(f"✅ Identical results: {len(identical_results)} frames")
    print(f"🔵 Mini service detected more: {len(mini_higher)} frames")
    print(f"🔴 Media service detected more: {len(media_higher)} frames")

    # Show frame-by-frame comparison
    print(f"\n📋 FRAME-BY-FRAME COMPARISON:")
    print(
        f"{'Frame':<6} {'Mini':<5} {'Media':<6} {'Diff':<5} {'Mini Method':<25} {'Media Method':<25}"
    )
    print("-" * 80)

    for c in successful_comparisons:
        diff_str = f"{c['difference']:+d}" if c["difference"] != 0 else "0"
        print(
            f"{c['frame_number']:<6} {c['mini_faces']:<5} {c['media_faces']:<6} {diff_str:<5} "
            f"{c['mini_method'][:24]:<25} {c['media_method'][:24]:<25}"
        )

    # Show significant differences
    significant_diffs = [c for c in successful_comparisons if abs(c["difference"]) > 0]
    if significant_diffs:
        print(f"\n⚠️  SIGNIFICANT DIFFERENCES FOUND:")
        for c in significant_diffs:
            print(
                f"   Frame {c['frame_number']}: Mini={c['mini_faces']}, Media={c['media_faces']} "
                f"(diff: {c['difference']:+d})"
            )

            # Show bounding box details if available
            if c.get("bbox_comparison"):
                print(f"     Mini BBs: {c['bbox_comparison']['mini_bboxes']}")
                print(f"     Media BBs: {c['bbox_comparison']['media_bboxes']}")

    # Performance comparison
    mini_avg_time = sum(c["mini_detection_time"] for c in successful_comparisons) / len(
        successful_comparisons
    )
    media_avg_time = sum(
        c["media_detection_time"] for c in successful_comparisons
    ) / len(successful_comparisons)

    print(f"\n⚡ PERFORMANCE COMPARISON:")
    print(f"   Mini service avg detection time: {mini_avg_time:.3f}s")
    print(f"   Media service avg detection time: {media_avg_time:.3f}s")
    print(f"   Performance difference: {(mini_avg_time - media_avg_time)*1000:.1f}ms")


def main():
    """Main comparison function."""
    print("🚀 PPL Meta Face Detection Service Comparison")
    print("=" * 60)

    # Get parameters from command line or use defaults
    if len(sys.argv) < 2:
        print(
            "Usage: python test_mini_vs_media_comparison.py <video_path> [video_uuid] [auth_token]"
        )
        print("\nExample:")
        print("  python test_mini_vs_media_comparison.py /path/to/video.mp4")
        print(
            "  python test_mini_vs_media_comparison.py /path/to/video.mp4 170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
        )
        return

    video_path = sys.argv[1]
    video_uuid = (
        sys.argv[2] if len(sys.argv) > 2 else "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
    )
    auth_token = sys.argv[3] if len(sys.argv) > 3 else None

    # Verify video file exists for mini service
    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        return

    print(f"📹 Video path: {video_path}")
    print(f"🆔 Video UUID: {video_uuid}")
    print(f"🔑 Auth token: {'Provided' if auth_token else 'None'}")
    print(f"🎯 Testing {len(TEST_FRAMES)} frames: {TEST_FRAMES}")
    print(f"⚡ Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print()

    comparisons = []

    for i, frame_number in enumerate(TEST_FRAMES, 1):
        print(f"📸 Testing frame {frame_number} ({i}/{len(TEST_FRAMES)})")

        # Test Mini Service
        print(f"   🔵 Testing Mini Service...")
        mini_result = test_mini_service_frame(frame_number, video_path)

        # Test Media Service
        print(f"   🔴 Testing Media Service...")
        media_result = test_media_service_frame(frame_number, video_uuid, auth_token)

        # Compare results
        comparison = compare_face_results(mini_result, media_result)
        comparisons.append(comparison)

        # Print immediate result
        if mini_result.get("success") and media_result.get("success"):
            mini_faces = mini_result.get("total_faces", 0)
            media_faces = media_result.get("total_faces", 0)
            diff = mini_faces - media_faces
            status = "✅ MATCH" if diff == 0 else f"⚠️  DIFF: {diff:+d}"
            print(f"   {status} - Mini: {mini_faces}, Media: {media_faces}")
        else:
            mini_status = (
                "✅"
                if mini_result.get("success")
                else f"❌ {mini_result.get('error', 'Unknown error')}"
            )
            media_status = (
                "✅"
                if media_result.get("success")
                else f"❌ {media_result.get('error', 'Unknown error')}"
            )
            print(f"   Mini: {mini_status}")
            print(f"   Media: {media_status}")

        print()

        # Small delay to avoid overwhelming services
        time.sleep(0.1)

    # Print comprehensive summary
    print_comparison_summary(comparisons)

    # Save detailed results to file
    output_file = "mini_vs_media_comparison_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "test_config": {
                    "video_path": video_path,
                    "video_uuid": video_uuid,
                    "test_frames": TEST_FRAMES,
                    "confidence_threshold": CONFIDENCE_THRESHOLD,
                    "timestamp": time.time(),
                },
                "comparisons": comparisons,
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
