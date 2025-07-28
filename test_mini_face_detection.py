#!/usr/bin/env python3
"""
Test script to verify Mini service face detection is working
"""

import os
import sys

import cv2
import numpy as np

# Add the mini service to the path
sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-mini/src")

from core.face_detection import MiniFaceDetectionService


def test_face_detection():
    """Test the face detection service directly"""

    # Initialize the service
    print("🔧 Initializing Mini Face Detection Service...")
    service = MiniFaceDetectionService()

    # Check if it's ready
    print(f"📋 Service ready: {service.is_ready()}")

    # Get detection info
    info = service.get_face_detection_info()
    print(f"🔍 Detection info: {info}")

    # Test with a simple test image (create a synthetic frame)
    print("🖼️ Creating test frame...")
    test_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128  # Gray image

    # Add a simple white rectangle to simulate a face-like region
    cv2.rectangle(test_frame, (200, 150), (400, 350), (255, 255, 255), -1)

    # Test the vision-compatible detection method
    print("🎯 Testing detect_faces_vision_compatible method...")
    try:
        detections = service.detect_faces_vision_compatible(
            test_frame, confidence_threshold=0.5
        )
        print(f"✅ Vision-compatible detection successful!")
        print(f"📊 Found {len(detections)} faces")
        for i, detection in enumerate(detections):
            print(f"   Face {i+1}: {detection}")

        return True

    except Exception as e:
        print(f"❌ Vision-compatible detection failed: {e}")
        return False


if __name__ == "__main__":
    success = test_face_detection()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Mini face detection test")
