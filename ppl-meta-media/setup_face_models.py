#!/usr/bin/env python3
"""
PPL Meta Media Service - Face Detection Models Setup
Downloads and sets up face detection models for embedded face detection.
"""

import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def setup_face_detection_models():
    """Download and setup face detection models for Media service."""

    models_dir = os.path.join(os.path.dirname(__file__), "models", "face_detection")
    os.makedirs(models_dir, exist_ok=True)

    print(f"📁 Setting up face detection models in: {models_dir}")

    # Model files to download
    models = {
        "haarcascade_frontalface_default.xml": {
            "url": "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml",
            "description": "OpenCV Haar cascade for face detection",
        },
        "opencv_face_detector.pbtxt": {
            "url": "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/opencv_face_detector.pbtxt",
            "description": "OpenCV DNN face detector configuration",
        },
    }

    for filename, info in models.items():
        filepath = os.path.join(models_dir, filename)

        if os.path.exists(filepath):
            print(f"✅ {filename} already exists")
            continue

        try:
            print(f"⬇️  Downloading {filename}...")
            print(f"   {info['description']}")

            urllib.request.urlretrieve(info["url"], filepath)

            # Verify file was downloaded
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                print(f"✅ {filename} downloaded successfully")
            else:
                print(f"❌ {filename} download failed")

        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")

    # Note about DNN weights file
    print("\n📝 Note: For better accuracy, you can manually download:")
    print("   opencv_face_detector_uint8.pb from:")
    print(
        "   https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb"
    )
    print("   and place it in the models/face_detection directory")

    print(f"\n🎯 Face detection models setup complete!")
    print(f"   Models directory: {models_dir}")
    print(f"   The Media service can now provide real-time face detection")
    print(f"   without requiring cross-service API calls to Vision service.")


if __name__ == "__main__":
    setup_face_detection_models()
