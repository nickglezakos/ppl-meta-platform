"""
PPL Meta Shared Face Detection Module
Provides face detection capabilities across services without cross-service API calls.
"""

from .shared_face_detector import SharedFaceDetector

__all__ = ["SharedFaceDetector"]
