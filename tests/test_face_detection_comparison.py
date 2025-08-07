#!/usr/bin/env python3
"""
Comparison test to verify Mini and Media services use identical face detection
"""

import os
import sys

import cv2
import numpy as np

# Add the service paths
sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-mini/src")
sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src")
sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code")

from core.face_detection import MiniFaceDetectionService
from services.face_detection_service import MediaFaceDetectionService


def create_test_frame():
    """Create a synthetic test frame with face-like patterns"""
    # Create a 640x480 frame
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

    # Add some face-like rectangular patterns
    # Pattern 1: Larger rectangle (more likely to be detected)
    cv2.rectangle(frame, (150, 100), (350, 300), (200, 200, 200), -1)
    cv2.rectangle(frame, (170, 130), (200, 160), (100, 100, 100), -1)  # Eye
    cv2.rectangle(frame, (250, 130), (280, 160), (100, 100, 100), -1)  # Eye
    cv2.rectangle(frame, (200, 220), (250, 250), (100, 100, 100), -1)  # Mouth

    return frame


def compare_face_detection():
    """Compare face detection between Mini and Media services"""

    print("🔍 PPL Meta Face Detection Comparison Test")
    print("=" * 50)

    # Initialize services
    print("1️⃣ Initializing Mini Face Detection Service...")
    mini_service = MiniFaceDetectionService()
    print(f"   Mini service ready: {mini_service.is_ready()}")

    print("2️⃣ Initializing Media Face Detection Service...")
    media_service = MediaFaceDetectionService()
    print(f"   Media service ready: {media_service.is_face_detection_enabled()}")

    # Get detection info
    print("\n3️⃣ Service Capabilities:")
    mini_info = mini_service.get_face_detection_info()
    media_info = media_service.get_face_detection_info()

    print(f"   Mini available methods: {mini_info.get('available_methods', [])}")
    print(f"   Media available methods: {media_info.get('available_methods', [])}")

    # Create test frame
    print("\n4️⃣ Creating test frame...")
    test_frame = create_test_frame()

    # Test both services
    print("\n5️⃣ Testing face detection...")

    # Mini service detection
    try:
        mini_detections = mini_service.detect_faces_vision_compatible(
            test_frame, confidence_threshold=0.5
        )
        print(f"   Mini service: {len(mini_detections)} faces detected")
        for i, detection in enumerate(mini_detections):
            print(
                f"     Face {i+1}: bbox={detection['bbox']}, conf={detection['confidence']}, method={detection['method']}"
            )
    except Exception as e:
        print(f"   ❌ Mini service error: {e}")
        mini_detections = []

    # Media service detection
    try:
        media_detections = media_service.detect_faces_vision_compatible(
            test_frame, confidence_threshold=0.5
        )
        print(f"   Media service: {len(media_detections)} faces detected")
        for i, detection in enumerate(media_detections):
            print(
                f"     Face {i+1}: bbox={detection['bbox']}, conf={detection['confidence']}, method={detection['method']}"
            )
    except Exception as e:
        print(f"   ❌ Media service error: {e}")
        media_detections = []

    # Compare results
    print("\n6️⃣ Comparison Results:")
    if len(mini_detections) == len(media_detections):
        print("   ✅ Same number of faces detected")

        # Compare individual detections
        matches = 0
        for i, (mini_det, media_det) in enumerate(
            zip(mini_detections, media_detections)
        ):
            if (
                mini_det["bbox"] == media_det["bbox"]
                and mini_det["confidence"] == media_det["confidence"]
                and mini_det["method"] == media_det["method"]
            ):
                matches += 1
                print(f"   ✅ Face {i+1}: Identical detection")
            else:
                print(f"   ⚠️ Face {i+1}: Different results")
                print(f"      Mini: {mini_det}")
                print(f"      Media: {media_det}")

        if matches == len(mini_detections):
            print("\n🎉 PERFECT MATCH: Both services produce identical results!")
            return True
        else:
            print(f"\n⚠️ PARTIAL MATCH: {matches}/{len(mini_detections)} faces matched")
            return False
    else:
        print(
            f"   ❌ Different number of faces: Mini={len(mini_detections)}, Media={len(media_detections)}"
        )
        return False


if __name__ == "__main__":
    success = compare_face_detection()
    print(
        f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}: Face detection comparison"
    )
