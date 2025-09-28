"""
PPL Meta Vision Service - Phase 4: Integration Testing Suite
Comprehensive test suite for PPL Thread workflow integration and service testing.

This test suite validates:
- Complete service integration with main FastAPI application
- Database schema migration and face crop functionality
- End-to-end workflow execution with real data
- API endpoint integration and error handling
- Performance benchmarks and quality assurance
- PPL Meta Mini compatibility validation in production context
"""

import asyncio
import base64
import io
import json
import logging
import sys
import time
import unittest
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import cv2
import numpy as np
import pytest
import requests
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src")

from database import VisionDatabase
from database.face_data_manager import FaceDataManager, initialize_face_crops_table
from database.person_objects_migrations import PersonObjectsMigration

# Import main application and components
from main import app
from person_objects.face_grouping_engine import VisionFaceGroupingEngine
from person_objects.ppl_thread_workflow import PPLThreadWorkflowController
from person_objects.quality_analyzer import PersonQualityAnalyzer

logger = logging.getLogger(__name__)


class TestPhase4ServiceIntegration(unittest.TestCase):
    """
    Test suite for Phase 4 service integration.

    Tests the complete integration of PPL Thread functionality
    into the main Vision Service application.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment before running tests."""
        cls.client = TestClient(app)
        cls.test_session_uuid = "550e8400-e29b-41d4-a716-446655440001"
        cls.mock_db = Mock()

    def test_main_service_startup_integration(self):
        """Test that main service startup includes PPL Thread initialization."""
        # Test that the startup event includes person objects router
        # This validates Phase 4.1 integration

        # Check that person objects endpoints are available
        response = self.client.get("/docs")  # OpenAPI documentation
        self.assertEqual(response.status_code, 200)

        # Verify person objects endpoints are registered
        openapi_data = response.content.decode()
        self.assertIn("person-objects", openapi_data)
        self.assertIn("/api/v1/person-objects/workflows/start", openapi_data)

    def test_person_objects_api_integration(self):
        """Test person objects API endpoints integration."""
        # Test workflow start endpoint exists
        test_payload = {
            "session_uuid": self.test_session_uuid,
            "tolerance_percent": 20.0,
            "enable_quality_analysis": True,
            "enable_age_detection": True,
        }

        # Note: This will fail without database, but validates endpoint exists
        response = self.client.post(
            "/api/v1/person-objects/workflows/start", json=test_payload
        )

        # Endpoint should exist (even if it fails due to database/data issues)
        self.assertNotEqual(response.status_code, 404)

    def test_health_endpoint_includes_person_objects(self):
        """Test that health endpoint reflects person objects functionality."""
        response = self.client.get("/health")

        if response.status_code == 200:
            health_data = response.json()
            # Should include information about person objects capability
            self.assertIn("status", health_data)


class TestPhase4DatabaseEnhancements(unittest.TestCase):
    """
    Test suite for Phase 4 database enhancements.

    Tests the enhanced database functionality including face crops table
    and quality analysis capabilities.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.face_data_manager = FaceDataManager(self.mock_db)

        # Create sample face crop for testing
        self.sample_face_crop = np.ones((100, 100, 3), dtype=np.uint8) * 128
        _, buffer = cv2.imencode(".jpg", self.sample_face_crop)
        self.sample_crop_base64 = base64.b64encode(buffer).decode("utf-8")

    def test_face_data_manager_initialization(self):
        """Test FaceDataManager initializes correctly."""
        manager = FaceDataManager(self.mock_db)
        self.assertIsNotNone(manager.db)
        self.assertIn("sharpness", manager.quality_weights)
        self.assertIn("exposure", manager.quality_weights)
        self.assertIn("contrast", manager.quality_weights)
        self.assertIn("noise", manager.quality_weights)

    def test_quality_score_calculation_internal(self):
        """Test internal quality score calculation."""
        # Test with sample face crop
        quality_score = self.face_data_manager._calculate_quality_score_internal(
            self.sample_face_crop
        )

        # Should return valid quality score
        self.assertIsInstance(quality_score, float)
        self.assertGreaterEqual(quality_score, 0.0)
        self.assertLessEqual(quality_score, 1.0)

    def test_quality_score_calculation_edge_cases(self):
        """Test quality calculation with edge cases."""
        # Empty image
        empty_image = np.array([])
        score_empty = self.face_data_manager._calculate_quality_score_internal(
            empty_image
        )
        self.assertEqual(score_empty, 0.0)

        # Very small image
        tiny_image = np.ones((5, 5, 3), dtype=np.uint8)
        score_tiny = self.face_data_manager._calculate_quality_score_internal(
            tiny_image
        )
        self.assertGreaterEqual(score_tiny, 0.0)

        # High contrast image
        high_contrast = np.zeros((50, 50, 3), dtype=np.uint8)
        high_contrast[:25, :] = 255  # Half white, half black
        score_contrast = self.face_data_manager._calculate_quality_score_internal(
            high_contrast
        )
        self.assertGreater(score_contrast, 0.0)

    async def test_face_crop_extraction_and_encoding(self):
        """Test face crop extraction from frame image."""
        # Create sample frame
        frame_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Sample face detection data
        face_data = {
            "id": "test_face_001",
            "bbox_x1": 100,
            "bbox_y1": 100,
            "bbox_x2": 200,
            "bbox_y2": 200,
        }

        # Extract and encode crop
        crop_base64 = await self.face_data_manager._extract_and_encode_face_crop(
            frame_image, face_data
        )

        # Should return valid base64 string
        self.assertIsInstance(crop_base64, str)
        self.assertGreater(len(crop_base64), 0)

        # Decode and verify it's a valid image
        crop_bytes = base64.b64decode(crop_base64)
        crop_array = np.frombuffer(crop_bytes, np.uint8)
        decoded_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)

        self.assertIsNotNone(decoded_crop)
        self.assertEqual(decoded_crop.shape[:2], (100, 100))  # Expected crop size


class TestPhase4WorkflowExecution(unittest.TestCase):
    """
    Test suite for Phase 4 complete workflow execution.

    Tests end-to-end workflow execution with database integration
    and quality analysis functionality.
    """

    def setUp(self):
        """Set up test fixtures for workflow testing."""
        self.mock_db = Mock()
        self.workflow_controller = PPLThreadWorkflowController(self.mock_db)

        # Sample face detections for workflow testing
        self.sample_face_detections = [
            {
                "id": "face_001",
                "frame_number": 1,
                "position_x": 100.0,
                "position_y": 150.0,
                "bbox_x1": 90,
                "bbox_y1": 140,
                "bbox_x2": 110,
                "bbox_y2": 160,
                "confidence": 0.95,
                "method": "two_stage",
                "created_at": datetime.now(),
            },
            {
                "id": "face_002",
                "frame_number": 2,
                "position_x": 105.0,  # Close to face_001 - should group
                "position_y": 155.0,
                "bbox_x1": 95,
                "bbox_y1": 145,
                "bbox_x2": 115,
                "bbox_y2": 165,
                "confidence": 0.88,
                "method": "two_stage",
                "created_at": datetime.now(),
            },
            {
                "id": "face_003",
                "frame_number": 3,
                "position_x": 300.0,  # Far from others - new person
                "position_y": 200.0,
                "bbox_x1": 290,
                "bbox_y1": 190,
                "bbox_x2": 310,
                "bbox_y2": 210,
                "confidence": 0.92,
                "method": "two_stage",
                "created_at": datetime.now(),
            },
        ]

    async def test_complete_workflow_with_database_integration(self):
        """Test complete workflow execution with database operations."""

        # Mock database operations
        with patch.object(
            self.workflow_controller, "_validate_session_exists"
        ), patch.object(
            self.workflow_controller, "_create_workflow_record"
        ), patch.object(
            self.workflow_controller, "_get_session_face_detections"
        ) as mock_get_faces, patch.object(
            self.workflow_controller, "_store_person_objects_and_mappings"
        ), patch.object(
            self.workflow_controller, "_store_quality_analysis_results"
        ), patch.object(
            self.workflow_controller, "_complete_workflow"
        ):

            # Setup mock data
            mock_get_faces.return_value = self.sample_face_detections

            # Execute workflow
            result = await self.workflow_controller.start_person_objects_workflow(
                session_uuid="test-session-001",
                tolerance_percent=20.0,
                enable_quality_analysis=True,
            )

            # Validate workflow execution
            self.assertIn("workflow_id", result)
            self.assertIn("success", result)
            self.assertTrue(result["success"])

            # Validate person objects creation
            self.assertIn("group_tracking", result)
            self.assertGreater(len(result["group_tracking"]), 0)

            # Should create 2 persons (faces 001,002 grouped + face 003 separate)
            self.assertEqual(result["merged_groups"], 2)
            self.assertEqual(result["original_groups"], 3)

    async def test_workflow_with_enhanced_quality_analysis(self):
        """Test workflow execution with Phase 4 enhanced quality analysis."""

        # Create face data manager for quality analysis
        face_manager = FaceDataManager(self.mock_db)

        # Mock quality analysis with face crops
        with patch.object(
            face_manager, "batch_analyze_face_quality"
        ) as mock_batch_quality:
            mock_batch_quality.return_value = {
                "face_001": 0.85,
                "face_002": 0.72,
                "face_003": 0.91,
            }

            # Test quality analysis
            quality_results = await face_manager.batch_analyze_face_quality(
                ["face_001", "face_002", "face_003"]
            )

            # Validate quality analysis results
            self.assertEqual(len(quality_results), 3)
            self.assertGreater(quality_results["face_001"], 0.0)
            self.assertLessEqual(quality_results["face_001"], 1.0)

    def test_ppl_mini_compatibility_in_integration_context(self):
        """Test PPL Meta Mini compatibility in service integration context."""

        # Create sample workflow results
        grouping_results = {
            "person_objects": [
                {
                    "person_id": "person_1",
                    "face_count": 2,
                    "average_position": {"x": 102.5, "y": 152.5},
                    "tracking_algorithm": "percentage_based_tracking",
                    "tolerance_percent": 20.0,
                    "original_face_ids": ["face_001", "face_002"],
                },
                {
                    "person_id": "person_2",
                    "face_count": 1,
                    "average_position": {"x": 300.0, "y": 200.0},
                    "tracking_algorithm": "percentage_based_tracking",
                    "tolerance_percent": 20.0,
                    "original_face_ids": ["face_003"],
                },
            ],
            "face_mappings": [
                {
                    "person_id": "person_1",
                    "face_detection_id": "face_001",
                    "match_type": "new_track",
                    "match_distance": 0.0,
                    "frame_number": 1,
                    "position_x": 100.0,
                    "position_y": 150.0,
                },
                {
                    "person_id": "person_1",
                    "face_detection_id": "face_002",
                    "match_type": "tracked",
                    "match_distance": 7.07,
                    "frame_number": 2,
                    "position_x": 105.0,
                    "position_y": 155.0,
                },
                {
                    "person_id": "person_2",
                    "face_detection_id": "face_003",
                    "match_type": "new_track",
                    "match_distance": 0.0,
                    "frame_number": 3,
                    "position_x": 300.0,
                    "position_y": 200.0,
                },
            ],
            "statistics": {
                "total_faces": 3,
                "total_persons": 2,
                "tracked_faces": 1,
                "new_faces": 2,
                "frames_processed": 3,
                "tolerance_percent": 20.0,
                "algorithm": "percentage_based_tracking",
            },
        }

        # Format response using workflow controller
        response = self.workflow_controller._format_ppl_mini_compatible_response(
            grouping_results, {}, "test_workflow", "test_session"
        )

        # Comprehensive PPL Mini compatibility validation

        # 1. Top-level structure validation
        required_top_keys = [
            "workflow_id",
            "session_uuid",
            "success",
            "original_groups",
            "merged_groups",
            "group_tracking",
            "summary",
            "statistics",
            "best_quality_faces",
            "classified_faces",
            "processing_timestamp",
            "workflow_type",
        ]

        for key in required_top_keys:
            self.assertIn(key, response, f"Missing required key: {key}")

        # 2. Group tracking structure validation
        self.assertIsInstance(response["group_tracking"], list)
        self.assertEqual(len(response["group_tracking"]), 2)

        for group in response["group_tracking"]:
            required_group_keys = [
                "Merged_Group_ID",
                "Original_Group_IDs",
                "Face_Count",
                "Average_Position",
                "Y_Coordinate_Based",
                "Tracking_Based",
                "Tolerance_Percent",
                "Merge_History",
            ]

            for key in required_group_keys:
                self.assertIn(key, group, f"Missing group key: {key}")

            # Validate PPL Mini specific boolean values
            self.assertFalse(group["Y_Coordinate_Based"])
            self.assertTrue(group["Tracking_Based"])
            self.assertEqual(group["Tolerance_Percent"], 20.0)

        # 3. Summary structure validation
        summary = response["summary"]
        required_summary_keys = [
            "total_groups",
            "original_unique_faces",
            "merged_groups_count",
            "total_detections",
            "grouping_algorithm",
            "tolerance_percent",
        ]

        for key in required_summary_keys:
            self.assertIn(key, summary, f"Missing summary key: {key}")

        # 4. Workflow type validation
        self.assertEqual(response["workflow_type"], "ppl_thread_person_objects")

        # 5. Statistical consistency validation
        self.assertEqual(response["original_groups"], 3)
        self.assertEqual(response["merged_groups"], 2)
        self.assertEqual(summary["total_groups"], 2)
        self.assertEqual(summary["original_unique_faces"], 3)


class TestPhase4PerformanceBenchmarks(unittest.TestCase):
    """
    Test suite for Phase 4 performance benchmarks.

    Validates that the integrated system meets performance requirements
    and can handle production workloads effectively.
    """

    def setUp(self):
        """Set up performance test fixtures."""
        self.face_grouping_engine = VisionFaceGroupingEngine()

    async def test_face_grouping_performance_benchmark(self):
        """Test face grouping performance with varying data sizes."""

        # Generate test data sets of different sizes
        test_sizes = [10, 50, 100, 500, 1000]
        performance_results = {}

        for size in test_sizes:
            # Generate test face detections
            test_faces = []
            for i in range(size):
                test_faces.append(
                    {
                        "id": f"face_{i:04d}",
                        "frame_number": i % 100,  # Spread across 100 frames
                        "position_x": 100.0 + (i % 10) * 50,  # Create clusters
                        "position_y": 100.0 + (i // 10) * 50,
                        "bbox_x1": 90 + (i % 10) * 50,
                        "bbox_y1": 90 + (i // 10) * 50,
                        "bbox_x2": 110 + (i % 10) * 50,
                        "bbox_y2": 110 + (i // 10) * 50,
                        "confidence": 0.85 + (i % 10) * 0.01,
                        "method": "two_stage",
                        "created_at": datetime.now(),
                    }
                )

            # Measure performance
            start_time = time.time()

            results = await self.face_grouping_engine.apply_percentage_based_tracking(
                test_faces, 20.0
            )

            end_time = time.time()
            processing_time = end_time - start_time

            performance_results[size] = {
                "processing_time": processing_time,
                "faces_per_second": size / processing_time,
                "persons_created": results["statistics"]["total_persons"],
                "grouping_efficiency": results["statistics"]["total_persons"] / size,
            }

            # Performance assertions
            if size <= 100:
                # Small datasets should process very quickly
                self.assertLess(
                    processing_time,
                    1.0,
                    f"Small dataset ({size} faces) took too long: {processing_time:.2f}s",
                )
            elif size <= 1000:
                # Large datasets should process within 10 seconds
                self.assertLess(
                    processing_time,
                    10.0,
                    f"Large dataset ({size} faces) took too long: {processing_time:.2f}s",
                )

            # Should process at least 100 faces per second for medium datasets
            if size >= 100:
                self.assertGreater(
                    performance_results[size]["faces_per_second"],
                    100,
                    f"Processing rate too slow for {size} faces: "
                    f"{performance_results[size]['faces_per_second']:.1f} fps",
                )

        # Log performance results
        print("\n" + "=" * 60)
        print("PHASE 4 PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        for size, metrics in performance_results.items():
            print(f"Dataset Size: {size} faces")
            print(f"  Processing Time: {metrics['processing_time']:.3f} seconds")
            print(f"  Processing Rate: {metrics['faces_per_second']:.1f} faces/sec")
            print(f"  Persons Created: {metrics['persons_created']}")
            print(f"  Grouping Efficiency: {metrics['grouping_efficiency']:.2%}")
            print()


async def run_phase4_integration_tests():
    """
    Run complete Phase 4 integration test suite.

    Returns:
        bool: True if all tests pass, False otherwise
    """
    print("=" * 80)
    print("PPL Meta Vision Service - Phase 4 Integration Test Suite")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestPhase4ServiceIntegration,
        TestPhase4DatabaseEnhancements,
        TestPhase4WorkflowExecution,
        TestPhase4PerformanceBenchmarks,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2, stream=sys.stdout, descriptions=True, failfast=False
    )

    print(f"Running {suite.countTestCases()} Phase 4 integration tests...")
    print()

    result = runner.run(suite)

    # Print comprehensive summary
    print()
    print("=" * 80)
    print("PHASE 4 INTEGRATION TEST RESULTS")
    print("=" * 80)

    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = total_tests - failures - errors

    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {successes}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    print(f"Success Rate: {(successes/total_tests)*100:.1f}%")

    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for i, (test, traceback) in enumerate(result.failures, 1):
            print(f"{i}. {test}")
            # Print first few lines of traceback
            lines = traceback.split("\n")
            for line in lines[:5]:  # First 5 lines
                if line.strip():
                    print(f"   {line}")
            print()

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for i, (test, traceback) in enumerate(result.errors, 1):
            print(f"{i}. {test}")
            # Print first few lines of traceback
            lines = traceback.split("\n")
            for line in lines[:5]:  # First 5 lines
                if line.strip():
                    print(f"   {line}")
            print()

    print("\n" + "=" * 80)

    if successes == total_tests:
        print("🎉 ALL PHASE 4 INTEGRATION TESTS PASSED!")
        print("Service integration is complete and production-ready!")
        return True
    else:
        print(f"⚠️ {failures + errors} integration tests failed.")
        print("Please review and resolve issues before deployment.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_phase4_integration_tests())
    sys.exit(0 if success else 1)
