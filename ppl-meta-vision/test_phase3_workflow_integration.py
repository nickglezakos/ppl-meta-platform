"""
PPL Meta Vision Service - Phase 3 Workflow Integration Tests
Comprehensive test suite for PPL Thread workflow controller and API integration.

This test suite validates the complete Phase 3 workflow integration:
- PPLThreadWorkflowController workflow orchestration
- Database integration with Phase 1 schema
- Algorithm integration with Phase 2 engines
- PPL Meta Mini compatibility validation
- Error handling and edge case testing

Test Categories:
1. Workflow Controller Tests - Core workflow orchestration
2. Database Integration Tests - Phase 1 schema integration
3. Algorithm Integration Tests - Phase 2 engine integration
4. PPL Mini Compatibility Tests - Output format validation
5. Error Handling Tests - Failure scenarios and recovery
6. End-to-End Integration Tests - Complete workflow validation
"""

import asyncio
import json
import os
import sys
import unittest
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

# Add the src directory to Python path for imports
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

# Import components directly to avoid relative import issues
try:
    from person_objects.face_grouping_engine import VisionFaceGroupingEngine
    from person_objects.ppl_thread_workflow import PPLThreadWorkflowController
    from person_objects.quality_analyzer import PersonQualityAnalyzer
except ImportError:
    # Create mock classes for testing if imports fail
    class VisionFaceGroupingEngine:
        async def apply_percentage_based_tracking(self, faces, tolerance):
            return {
                "person_objects": [],
                "face_mappings": [],
                "statistics": {"total_faces": 0, "total_persons": 0},
            }

    class PersonQualityAnalyzer:
        async def analyze_person_quality(self, person_objects, face_detections):
            return {}

    class PPLThreadWorkflowController:
        def __init__(self, db):
            self.db = db
            self.face_grouping_engine = VisionFaceGroupingEngine()
            self.quality_analyzer = PersonQualityAnalyzer()
            self.default_tolerance_percent = 20.0
            self.max_processing_time_minutes = 30
            self.batch_size = 100


class MockVisionDatabase:
    """Mock database for testing without real database connection."""

    def __init__(self):
        self.connection = Mock()
        self.connection.cursor = AsyncMock()
        self.connection.commit = AsyncMock()
        self.connection.rollback = AsyncMock()

        # Mock data storage
        self.face_detection_sessions = {}
        self.face_detections = {}
        self.person_objects = {}
        self.person_face_mappings = {}
        self.person_workflows = {}

    def setup_test_session(self, session_uuid: str, face_detections: List[Dict]):
        """Setup mock test session with face detections."""
        self.face_detection_sessions[session_uuid] = {
            "session_uuid": session_uuid,
            "created_at": datetime.now(),
        }

        for face in face_detections:
            face["session_uuid"] = session_uuid
            self.face_detections[face["id"]] = face


class TestPPLThreadWorkflowController(unittest.TestCase):
    """Test suite for the PPLThreadWorkflowController class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_db = MockVisionDatabase()
        self.controller = PPLThreadWorkflowController(self.mock_db)

        # Test session UUID
        self.test_session_uuid = "550e8400-e29b-41d4-a716-446655440002"

        # Sample face detection data for testing
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
            {
                "id": "face_004",
                "frame_number": 4,
                "position_x": 102.0,  # Close to face_001/002 - should group
                "position_y": 148.0,
                "bbox_x1": 92,
                "bbox_y1": 138,
                "bbox_x2": 112,
                "bbox_y2": 158,
                "confidence": 0.91,
                "method": "two_stage",
                "created_at": datetime.now(),
            },
        ]

    def test_workflow_controller_initialization(self):
        """Test that workflow controller initializes correctly."""
        self.assertIsNotNone(self.controller.db)
        self.assertIsNotNone(self.controller.face_grouping_engine)
        self.assertIsNotNone(self.controller.quality_analyzer)
        self.assertEqual(self.controller.default_tolerance_percent, 20.0)
        self.assertEqual(self.controller.max_processing_time_minutes, 30)
        self.assertEqual(self.controller.batch_size, 100)

    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._validate_session_exists"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._create_workflow_record"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._get_session_face_detections"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._store_person_objects_and_mappings"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._store_quality_analysis_results"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._complete_workflow"
    )
    def test_start_person_objects_workflow_success(
        self,
        mock_complete,
        mock_store_quality,
        mock_store_objects,
        mock_get_faces,
        mock_create_workflow,
        mock_validate_session,
    ):
        """Test successful workflow execution."""

        async def run_test():
            # Setup mocks
            mock_validate_session.return_value = True
            mock_create_workflow.return_value = None
            mock_get_faces.return_value = self.sample_face_detections
            mock_store_objects.return_value = None
            mock_store_quality.return_value = None
            mock_complete.return_value = None

            # Execute workflow
            result = await self.controller.start_person_objects_workflow(
                session_uuid=self.test_session_uuid,
                tolerance_percent=20.0,
                enable_quality_analysis=True,
            )

            # Validate result structure
            self.assertIn("workflow_id", result)
            self.assertIn("session_uuid", result)
            self.assertIn("success", result)
            self.assertIn("group_tracking", result)
            self.assertIn("summary", result)
            self.assertIn("best_quality_faces", result)
            self.assertIn("classified_faces", result)

            # Validate PPL Mini compatibility
            self.assertTrue(result["success"])
            self.assertEqual(result["session_uuid"], self.test_session_uuid)
            self.assertEqual(result["workflow_type"], "ppl_thread_person_objects")

            # Validate face grouping occurred
            self.assertGreater(len(result["group_tracking"]), 0)
            self.assertGreater(len(result["classified_faces"]), 0)

            # Should create 2 persons (faces 001,002,004 grouped + face 003 separate)
            self.assertEqual(result["merged_groups"], 2)
            self.assertEqual(result["original_groups"], 4)

        asyncio.run(run_test())

    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._validate_session_exists"
    )
    def test_workflow_session_not_found_error(self, mock_validate_session):
        """Test workflow failure when session doesn't exist."""

        async def run_test():
            # Setup mock to raise error
            mock_validate_session.side_effect = ValueError("Session not found")

            # Execute workflow and expect error
            with self.assertRaises(RuntimeError) as context:
                await self.controller.start_person_objects_workflow(
                    session_uuid="nonexistent-session"
                )

            self.assertIn("Session not found", str(context.exception))

        asyncio.run(run_test())

    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._validate_session_exists"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._create_workflow_record"
    )
    @patch(
        "person_objects.ppl_thread_workflow.PPLThreadWorkflowController._get_session_face_detections"
    )
    def test_workflow_no_face_detections_error(
        self, mock_get_faces, mock_create_workflow, mock_validate_session
    ):
        """Test workflow failure when no face detections exist."""

        async def run_test():
            # Setup mocks
            mock_validate_session.return_value = True
            mock_create_workflow.return_value = None
            mock_get_faces.return_value = []  # No face detections

            # Execute workflow and expect error
            with self.assertRaises(RuntimeError) as context:
                await self.controller.start_person_objects_workflow(
                    session_uuid=self.test_session_uuid
                )

            self.assertIn("No face detections found", str(context.exception))

        asyncio.run(run_test())

    def test_ppl_mini_response_format_compatibility(self):
        """Test that response format exactly matches PPL Meta Mini structure."""

        async def run_test():
            # Create mock grouping results
            grouping_results = {
                "person_objects": [
                    {
                        "person_id": "person_1",
                        "face_count": 3,
                        "average_position": {"x": 102.33, "y": 151.0},
                        "tracking_algorithm": "percentage_based_tracking",
                        "tolerance_percent": 20.0,
                        "original_face_ids": ["face_001", "face_002", "face_004"],
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
                ],
                "statistics": {
                    "total_faces": 4,
                    "total_persons": 2,
                    "tracked_faces": 2,
                    "new_faces": 2,
                    "frames_processed": 4,
                    "tolerance_percent": 20.0,
                    "algorithm": "percentage_based_tracking",
                },
            }

            best_quality_faces = {
                "person_1": {
                    "face_record": {
                        "id": "face_001",
                        "frame_number": 1,
                        "bbox_x1": 90,
                        "bbox_y1": 140,
                        "bbox_x2": 110,
                        "bbox_y2": 160,
                    },
                    "quality_score": 0.85,
                }
            }

            # Format response
            response = await self.controller._format_ppl_mini_compatible_response(
                grouping_results,
                best_quality_faces,
                "test_workflow",
                self.test_session_uuid,
            )

            # Validate PPL Mini format requirements
            required_top_level_keys = [
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

            for key in required_top_level_keys:
                self.assertIn(key, response, f"Missing required key: {key}")

            # Validate group tracking format (PPL Mini specific)
            group_tracking = response["group_tracking"]
            self.assertIsInstance(group_tracking, list)
            self.assertGreater(len(group_tracking), 0)

            first_group = group_tracking[0]
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
                self.assertIn(key, first_group, f"Missing group tracking key: {key}")

            # Validate summary format (PPL Mini specific)
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

            # Validate classified faces format
            classified_faces = response["classified_faces"]
            self.assertIsInstance(classified_faces, list)

            if classified_faces:
                first_classified = classified_faces[0]
                required_classified_keys = [
                    "face_id",
                    "person_id",
                    "match_type",
                    "match_distance",
                    "frame_number",
                    "position",
                ]

                for key in required_classified_keys:
                    self.assertIn(
                        key, first_classified, f"Missing classified face key: {key}"
                    )

        asyncio.run(run_test())

    def test_workflow_tolerance_parameter_validation(self):
        """Test that different tolerance percentages work correctly."""

        async def run_test():
            # Test various tolerance values
            tolerance_values = [5.0, 15.0, 20.0, 30.0, 45.0]

            for tolerance in tolerance_values:
                with patch.object(
                    self.controller, "_validate_session_exists"
                ), patch.object(
                    self.controller, "_create_workflow_record"
                ), patch.object(
                    self.controller, "_get_session_face_detections"
                ) as mock_get_faces, patch.object(
                    self.controller, "_store_person_objects_and_mappings"
                ), patch.object(
                    self.controller, "_store_quality_analysis_results"
                ), patch.object(
                    self.controller, "_complete_workflow"
                ):

                    mock_get_faces.return_value = self.sample_face_detections

                    result = await self.controller.start_person_objects_workflow(
                        session_uuid=self.test_session_uuid, tolerance_percent=tolerance
                    )

                    # Validate tolerance is properly applied
                    self.assertEqual(result["summary"]["tolerance_percent"], tolerance)

                    # All group tracking items should have correct tolerance
                    for group in result["group_tracking"]:
                        self.assertEqual(group["Tolerance_Percent"], tolerance)

        asyncio.run(run_test())


class TestWorkflowDatabaseIntegration(unittest.TestCase):
    """Test suite for database integration aspects of Phase 3."""

    def setUp(self):
        """Set up test fixtures for database integration testing."""
        self.mock_db = MockVisionDatabase()
        self.controller = PPLThreadWorkflowController(self.mock_db)
        self.test_session_uuid = "550e8400-e29b-41d4-a716-446655440002"

    def test_database_session_validation(self):
        """Test session existence validation in database."""

        async def run_test():
            # Mock cursor and database response
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = (1,)  # Session exists
            self.mock_db.connection.cursor.return_value = mock_cursor

            # Should not raise exception
            result = await self.controller._validate_session_exists(
                self.test_session_uuid
            )
            self.assertTrue(result)

            # Test session not found
            mock_cursor.fetchone.return_value = (0,)  # Session doesn't exist

            with self.assertRaises(ValueError):
                await self.controller._validate_session_exists("nonexistent-session")

        asyncio.run(run_test())

    def test_workflow_record_creation(self):
        """Test workflow record creation in database."""

        async def run_test():
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = (10,)  # 10 face detections
            self.mock_db.connection.cursor.return_value = mock_cursor

            workflow_id = str(uuid.uuid4())

            # Should not raise exception
            await self.controller._create_workflow_record(
                workflow_id, self.test_session_uuid, 20.0, {"test": "metadata"}
            )

            # Verify database operations were called
            mock_cursor.execute.assert_called()
            self.mock_db.connection.commit.assert_called_once()

        asyncio.run(run_test())

    def test_face_detections_retrieval(self):
        """Test face detections retrieval from database."""

        async def run_test():
            # Mock face detections data
            mock_face_data = [
                (
                    "face_001",
                    1,
                    90,
                    140,
                    110,
                    160,
                    0.95,
                    "two_stage",
                    100.0,
                    150.0,
                    datetime.now(),
                ),
                (
                    "face_002",
                    2,
                    95,
                    145,
                    115,
                    165,
                    0.88,
                    "two_stage",
                    105.0,
                    155.0,
                    datetime.now(),
                ),
            ]

            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = mock_face_data
            mock_cursor.description = [
                ("id",),
                ("frame_number",),
                ("bbox_x1",),
                ("bbox_y1",),
                ("bbox_x2",),
                ("bbox_y2",),
                ("confidence",),
                ("method",),
                ("position_x",),
                ("position_y",),
                ("created_at",),
            ]
            self.mock_db.connection.cursor.return_value = mock_cursor

            # Retrieve face detections
            face_detections = await self.controller._get_session_face_detections(
                self.test_session_uuid
            )

            # Validate results
            self.assertEqual(len(face_detections), 2)
            self.assertEqual(face_detections[0]["id"], "face_001")
            self.assertEqual(face_detections[0]["frame_number"], 1)
            self.assertEqual(face_detections[1]["id"], "face_002")
            self.assertEqual(face_detections[1]["frame_number"], 2)

            # Verify position data is properly set
            self.assertIsNotNone(face_detections[0]["position_x"])
            self.assertIsNotNone(face_detections[0]["position_y"])

        asyncio.run(run_test())

    def test_person_objects_storage(self):
        """Test storage of person objects and mappings in database."""

        async def run_test():
            mock_cursor = AsyncMock()
            self.mock_db.connection.cursor.return_value = mock_cursor

            # Sample grouping results
            grouping_results = {
                "person_objects": [
                    {
                        "person_id": "person_1",
                        "face_count": 2,
                        "average_position": {"x": 102.5, "y": 152.5},
                        "tracking_algorithm": "percentage_based_tracking",
                        "tolerance_percent": 20.0,
                    }
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
                        "match_distance": 3.54,
                        "frame_number": 2,
                        "position_x": 105.0,
                        "position_y": 155.0,
                    },
                ],
            }

            # Store in database
            await self.controller._store_person_objects_and_mappings(
                "test_workflow", self.test_session_uuid, grouping_results
            )

            # Verify database operations
            expected_calls = len(grouping_results["person_objects"]) + len(
                grouping_results["face_mappings"]
            )
            self.assertEqual(mock_cursor.execute.call_count, expected_calls)
            self.mock_db.connection.commit.assert_called_once()

        asyncio.run(run_test())


class TestPPLMiniCompatibility(unittest.TestCase):
    """Test suite specifically for PPL Meta Mini compatibility validation."""

    def setUp(self):
        """Set up test fixtures for compatibility testing."""
        self.mock_db = MockVisionDatabase()
        self.controller = PPLThreadWorkflowController(self.mock_db)

    def test_response_structure_exact_match(self):
        """Test that response structure exactly matches PPL Meta Mini format."""

        async def run_test():
            # Create response using our controller
            grouping_results = {
                "person_objects": [
                    {
                        "person_id": "person_1",
                        "face_count": 2,
                        "average_position": {"x": 100.0, "y": 150.0},
                        "tracking_algorithm": "percentage_based_tracking",
                        "tolerance_percent": 20.0,
                        "original_face_ids": ["face_1", "face_2"],
                    }
                ],
                "face_mappings": [
                    {
                        "person_id": "person_1",
                        "face_detection_id": "face_1",
                        "match_type": "new_track",
                        "match_distance": 0.0,
                        "frame_number": 1,
                        "position_x": 100.0,
                        "position_y": 150.0,
                    }
                ],
                "statistics": {
                    "total_faces": 2,
                    "total_persons": 1,
                    "tracked_faces": 1,
                    "new_faces": 1,
                    "frames_processed": 2,
                    "tolerance_percent": 20.0,
                    "algorithm": "percentage_based_tracking",
                },
            }

            response = await self.controller._format_ppl_mini_compatible_response(
                grouping_results, {}, "test_workflow", "test_session"
            )

            # Define expected PPL Mini structure
            expected_structure = {
                "workflow_id": str,
                "session_uuid": str,
                "success": bool,
                "original_groups": int,
                "merged_groups": int,
                "group_tracking": list,
                "summary": dict,
                "statistics": dict,
                "best_quality_faces": dict,
                "classified_faces": list,
                "processing_timestamp": str,
                "workflow_type": str,
            }

            # Validate each expected key and type
            for key, expected_type in expected_structure.items():
                self.assertIn(key, response, f"Missing required key: {key}")
                self.assertIsInstance(
                    response[key],
                    expected_type,
                    f"Wrong type for {key}: expected {expected_type}, got {type(response[key])}",
                )

            # Validate specific PPL Mini field requirements
            group_tracking = response["group_tracking"][0]
            required_group_fields = {
                "Merged_Group_ID": str,
                "Original_Group_IDs": list,
                "Face_Count": int,
                "Average_Position": dict,
                "Y_Coordinate_Based": bool,
                "Tracking_Based": bool,
                "Tolerance_Percent": float,
                "Merge_History": list,
            }

            for field, expected_type in required_group_fields.items():
                self.assertIn(field, group_tracking)
                self.assertIsInstance(group_tracking[field], expected_type)

            # Validate specific PPL Mini boolean values
            self.assertFalse(group_tracking["Y_Coordinate_Based"])
            self.assertTrue(group_tracking["Tracking_Based"])

        asyncio.run(run_test())

    def test_algorithm_result_consistency(self):
        """Test that our algorithm produces consistent results with PPL Mini logic."""
        # This test verifies that the same input produces the same logical grouping
        # as would be expected from PPL Meta Mini

        async def run_test():
            # Test data that should produce predictable grouping
            test_faces = [
                {
                    "id": "face_a1",
                    "frame_number": 1,
                    "position_x": 100.0,
                    "position_y": 100.0,
                    "bbox_x1": 90,
                    "bbox_y1": 90,
                    "bbox_x2": 110,
                    "bbox_y2": 110,
                    "confidence": 0.9,
                    "method": "test",
                },
                {
                    "id": "face_a2",
                    "frame_number": 2,
                    "position_x": 110.0,  # 10% change - within 20% tolerance
                    "position_y": 110.0,  # 10% change - within 20% tolerance
                    "bbox_x1": 100,
                    "bbox_y1": 100,
                    "bbox_x2": 120,
                    "bbox_y2": 120,
                    "confidence": 0.85,
                    "method": "test",
                },
                {
                    "id": "face_b1",
                    "frame_number": 3,
                    "position_x": 300.0,  # Far away - should be different person
                    "position_y": 300.0,
                    "bbox_x1": 290,
                    "bbox_y1": 290,
                    "bbox_x2": 310,
                    "bbox_y2": 310,
                    "confidence": 0.88,
                    "method": "test",
                },
            ]

            # Use the actual face grouping engine (not mocked)
            engine = VisionFaceGroupingEngine()
            results = await engine.apply_percentage_based_tracking(test_faces, 20.0)

            # Should group faces a1 and a2 together, b1 separate
            self.assertEqual(results["statistics"]["total_persons"], 2)
            self.assertEqual(results["statistics"]["total_faces"], 3)

            # Find the person with 2 faces (should be person with face_a1 and face_a2)
            person_with_2_faces = None
            person_with_1_face = None

            for person in results["person_objects"]:
                if person["face_count"] == 2:
                    person_with_2_faces = person
                elif person["face_count"] == 1:
                    person_with_1_face = person

            self.assertIsNotNone(
                person_with_2_faces, "Should have one person with 2 faces"
            )
            self.assertIsNotNone(
                person_with_1_face, "Should have one person with 1 face"
            )

            # Verify face mappings are correct
            person_2_faces_id = person_with_2_faces["person_id"]
            person_1_face_id = person_with_1_face["person_id"]

            # Get face IDs for each person
            person_2_face_ids = [
                fm["face_detection_id"]
                for fm in results["face_mappings"]
                if fm["person_id"] == person_2_faces_id
            ]
            person_1_face_ids = [
                fm["face_detection_id"]
                for fm in results["face_mappings"]
                if fm["person_id"] == person_1_face_id
            ]

            # Validate grouping logic
            self.assertIn("face_a1", person_2_face_ids)
            self.assertIn("face_a2", person_2_face_ids)
            self.assertIn("face_b1", person_1_face_ids)

        asyncio.run(run_test())


class TestErrorHandlingAndEdgeCases(unittest.TestCase):
    """Test suite for error handling and edge case scenarios."""

    def setUp(self):
        """Set up test fixtures for error handling tests."""
        self.mock_db = MockVisionDatabase()
        self.controller = PPLThreadWorkflowController(self.mock_db)

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors."""

        async def run_test():
            # Mock database error
            self.mock_db.connection.cursor.side_effect = Exception(
                "Database connection failed"
            )

            with self.assertRaises(RuntimeError):
                await self.controller.start_person_objects_workflow(
                    session_uuid="test-session"
                )

        asyncio.run(run_test())

    def test_empty_session_handling(self):
        """Test handling of sessions with no face detections."""

        async def run_test():
            with patch.object(
                self.controller, "_validate_session_exists"
            ), patch.object(self.controller, "_create_workflow_record"), patch.object(
                self.controller, "_get_session_face_detections"
            ) as mock_get_faces:

                mock_get_faces.return_value = []  # No faces

                with self.assertRaises(RuntimeError) as context:
                    await self.controller.start_person_objects_workflow(
                        session_uuid="empty-session"
                    )

                self.assertIn("No face detections found", str(context.exception))

        asyncio.run(run_test())

    def test_invalid_tolerance_parameter_handling(self):
        """Test handling of invalid tolerance parameters."""

        async def run_test():
            with patch.object(
                self.controller, "_validate_session_exists"
            ), patch.object(self.controller, "_create_workflow_record"), patch.object(
                self.controller, "_get_session_face_detections"
            ) as mock_get_faces:

                mock_get_faces.return_value = [
                    {
                        "id": "test",
                        "frame_number": 1,
                        "position_x": 100,
                        "position_y": 100,
                    }
                ]

                # Test very low tolerance (should still work but produce different results)
                result_low = await self.controller.start_person_objects_workflow(
                    session_uuid="test-session", tolerance_percent=1.0
                )
                self.assertEqual(result_low["summary"]["tolerance_percent"], 1.0)

                # Test very high tolerance (should still work)
                result_high = await self.controller.start_person_objects_workflow(
                    session_uuid="test-session", tolerance_percent=50.0
                )
                self.assertEqual(result_high["summary"]["tolerance_percent"], 50.0)

        asyncio.run(run_test())


def run_phase3_tests():
    """
    Run all Phase 3 tests and return comprehensive results.
    """
    print("=" * 80)
    print("PPL Meta Vision Service - Phase 3 Workflow Integration Tests")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestPPLThreadWorkflowController,
        TestWorkflowDatabaseIntegration,
        TestPPLMiniCompatibility,
        TestErrorHandlingAndEdgeCases,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2, stream=sys.stdout, descriptions=True, failfast=False
    )

    print(f"Running {suite.countTestCases()} Phase 3 integration tests...")
    print()

    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 80)
    print("PHASE 3 TEST RESULTS SUMMARY")
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
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    print("\n" + "=" * 80)

    if successes == total_tests:
        print("🎉 ALL PHASE 3 TESTS PASSED! Workflow integration is complete.")
        return True
    else:
        print("⚠️ Some Phase 3 tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    success = run_phase3_tests()
    sys.exit(0 if success else 1)
