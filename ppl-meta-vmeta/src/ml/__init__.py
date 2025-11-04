"""
ML Processing Modules for MVR-People
PPL Meta Platform - vmeta service

Machine learning models for face recognition, age estimation, and gender classification.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

from .facenet_processor import FaceNetProcessor
from .age_estimator import AgeEstimator
from .gender_classifier import GenderClassifier
from .mvr_processor import MVRProcessor

__all__ = [
    'FaceNetProcessor',
    'AgeEstimator', 
    'GenderClassifier',
    'MVRProcessor'
]
