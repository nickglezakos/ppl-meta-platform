"""
PPL Meta Vision Service - Person Objects Module
Complete PPL Thread workflow implementation for person object functionality.

This module provides the complete Phase 1-3 implementation:
- Phase 1: Database schema (person_objects_migrations.py in ../database/)
- Phase 2: Core algorithms (face_grouping_engine.py, quality_analyzer.py)
- Phase 3: Workflow integration (ppl_thread_workflow.py, person_objects_api.py)

Components:
- VisionFaceGroupingEngine: Percentage-based face tracking algorithm
- PersonQualityAnalyzer: Quality scoring and best face selection
- PPLThreadWorkflowController: Complete workflow orchestration
"""

# Phase 2: Core algorithms - independent implementation
from .face_grouping_engine import VisionFaceGroupingEngine

# Phase 3: Workflow orchestration and integration
from .ppl_thread_workflow import PPLThreadWorkflowController
from .quality_analyzer import PersonQualityAnalyzer

__all__ = [
    "VisionFaceGroupingEngine",
    "PersonQualityAnalyzer",
    "PPLThreadWorkflowController",
]
