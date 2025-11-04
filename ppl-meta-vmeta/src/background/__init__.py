"""
Background Processing Module for MVR-People

This module provides background task processing for automatic
MVR-People creation and matching when new Individuals are created.
"""

from .mvr_background_processor import MVRBackgroundProcessor
from .mvr_integration_hook import MVRIntegrationHook
from . import mvr_helper

__all__ = [
    "MVRBackgroundProcessor",
    "MVRIntegrationHook",
    "mvr_helper"
]
