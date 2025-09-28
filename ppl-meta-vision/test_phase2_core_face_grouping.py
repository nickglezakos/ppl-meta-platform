"""
PPL Meta Vision Service - Phase 2 Core Face Grouping Engine Tests
Comprehensive test suite for the independent face grouping and quality analysis implementation.

This test suite validates the Phase 2 core functionality including:
- VisionFaceGroupingEngine percentage-based tracking algorithm
- PersonQualityAnalyzer quality scoring and best face selection
- End-to-end person object workflow
- Algorithm compatibility with PPL Meta Mini (same logic, independent code)

Test Categories:
1. Face Grouping Algorithm Tests
2. Quality Analysis Tests
3. Integration Tests
4. Edge Case Handling
5. Performance Validation
6. Data Integrity Tests
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime
from typing import Any, Dict, List

# Add the src directory to Python path for imports
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

from person_objects import PersonQualityAnalyzer, VisionFaceGroupingEngine


class TestVisionFaceGroupingEngine(unittest.TestCase):
    """Test suite for the VisionFaceGroupingEngine class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.engine = VisionFaceGroupingEngine()

        # Sample face detection data for testing
        self.sample_faces = [
            {
                "id": "face_001",
                "frame_number": 1,
                "position_x": 100.0,
                "position_y": 150.0,
                "detection_confidence": 0.95,
                "bbox_x1": 90,
                "bbox_y1": 140,
                "bbox_x2": 110,
                "bbox_y2": 160,
            },
            {
                "id": "face_002",
                "frame_number": 2,
                "position_x": 105.0,  # Close to face_001 - should group
                "position_y": 155.0,
                "detection_confidence": 0.88,
                "bbox_x1": 95,
                "bbox_y1": 145,
                "bbox_x2": 115,
                "bbox_y2": 165,
            },
            {
                "id": "face_003",
                "frame_number": 3,
                "position_x": 300.0,  # Far from others - new person
                "position_y": 200.0,
                "detection_confidence": 0.92,
                "bbox_x1": 290,
                "bbox_y1": 190,
                "bbox_x2": 310,
                "bbox_y2": 210,
            },
            {
                "id": "face_004",
                "frame_number": 4,
                "position_x": 102.0,  # Close to face_001/002 - should group
                "position_y": 148.0,
                "detection_confidence": 0.91,
                "bbox_x1": 92,
                "bbox_y1": 138,
                "bbox_x2": 112,
                "bbox_y2": 158,
            },
        ]

    def test_position_distance_calculation(self):
        """Test the position distance calculation algorithm."""
        pos1 = {"x": 100.0, "y": 150.0}
        pos2 = {"x": 105.0, "y": 155.0}

        result = self.engine.calculate_position_distance(pos1, pos2)

        # Validate result structure
        required_keys = [
            "x_distance",
            "y_distance",
            "euclidean_distance",
            "combined_distance",
            "within_tolerance",
            "x_tolerance_used",
            "y_tolerance_used",
        ]
        for key in required_keys:
            self.assertIn(key, result)

        # Validate calculations
        self.assertEqual(result["x_distance"], 5.0)
        self.assertEqual(result["y_distance"], 5.0)
        self.assertAlmostEqual(result["euclidean_distance"], 7.071, places=3)

        # With 20% tolerance: x_tolerance = 100 * 0.2 = 20, y_tolerance = 150 * 0.2 = 30
        self.assertEqual(result["x_tolerance_used"], 20.0)
        self.assertEqual(result["y_tolerance_used"], 30.0)

        # 5 <= 20 and 5 <= 30, so should be within tolerance
        self.assertTrue(result["within_tolerance"])

    def test_position_distance_outside_tolerance(self):
        """Test position distance calculation when outside tolerance."""
        pos1 = {"x": 100.0, "y": 150.0}
        pos2 = {"x": 200.0, "y": 250.0}  # Far away

        result = self.engine.calculate_position_distance(pos1, pos2)

        # Should be outside tolerance
        self.assertFalse(result["within_tolerance"])
        self.assertEqual(result["x_distance"], 100.0)
        self.assertEqual(result["y_distance"], 100.0)

    def test_face_position_extraction(self):
        """Test face position extraction from different data formats."""
        # Test with explicit position fields
        face1 = {"position_x": 100.0, "position_y": 150.0}
        pos1 = self.engine._extract_face_position(face1)
        self.assertEqual(pos1, {"x": 100.0, "y": 150.0})

        # Test with bbox coordinates
        face2 = {"bbox_x1": 90, "bbox_y1": 140, "bbox_x2": 110, "bbox_y2": 160}
        pos2 = self.engine._extract_face_position(face2)
        self.assertEqual(pos2, {"x": 90.0, "y": 140.0})

        # Test with missing data (should default to 0,0)
        face3 = {"id": "test"}
        pos3 = self.engine._extract_face_position(face3)
        self.assertEqual(pos3, {"x": 0.0, "y": 0.0})

    def test_face_detection_validation(self):
        """Test face detection data validation."""
        # Valid face data
        valid_faces = [
            {
                "id": "face_001",
                "frame_number": 1,
                "position_x": 100.0,
                "position_y": 150.0,
            }
        ]

        errors = self.engine.validate_face_detections(valid_faces)
        self.assertEqual(len(errors), 0)

        # Invalid face data - missing required fields
        invalid_faces = [
            {
                "position_x": 100.0,
                "position_y": 150.0,
                # Missing id and frame_number
            }
        ]

        errors = self.engine.validate_face_detections(invalid_faces)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Missing required field" in error for error in errors))

    def test_async_percentage_based_tracking(self):
        """Test the main percentage-based tracking algorithm."""

        async def run_test():
            # Run face grouping algorithm
            result = await self.engine.apply_percentage_based_tracking(
                self.sample_faces, tolerance_percent=20.0
            )

            # Validate result structure
            self.assertIn("person_objects", result)
            self.assertIn("face_mappings", result)
            self.assertIn("statistics", result)

            person_objects = result["person_objects"]
            face_mappings = result["face_mappings"]
            statistics = result["statistics"]

            # Should create 2 persons (faces 001,002,004 grouped + face 003 separate)
            self.assertEqual(len(person_objects), 2)

            # Should have 4 face mappings (one per input face)
            self.assertEqual(len(face_mappings), 4)

            # Validate statistics
            self.assertEqual(statistics["total_faces"], 4)
            self.assertEqual(statistics["total_persons"], 2)
            self.assertEqual(statistics["tolerance_percent"], 20.0)
            self.assertEqual(statistics["algorithm"], "percentage_based_tracking")

            # Check that faces 001, 002, 004 are grouped together (close positions)
            person_ids = set()
            for mapping in face_mappings:
                if mapping["face_detection_id"] in ["face_001", "face_002", "face_004"]:
                    person_ids.add(mapping["person_id"])

            # These 3 faces should belong to the same person
            self.assertEqual(
                len(person_ids), 1, "Faces 001, 002, 004 should be grouped together"
            )

            # Face 003 should be in a different person (far position)
            face_003_person = None
            for mapping in face_mappings:
                if mapping["face_detection_id"] == "face_003":
                    face_003_person = mapping["person_id"]
                    break

            self.assertIsNotNone(face_003_person)
            self.assertNotIn(
                face_003_person, person_ids, "Face 003 should be separate person"
            )

        # Run async test
        asyncio.run(run_test())

    def test_empty_face_list(self):
        """Test algorithm behavior with empty face detection list."""

        async def run_test():
            result = await self.engine.apply_percentage_based_tracking([])

            self.assertEqual(len(result["person_objects"]), 0)
            self.assertEqual(len(result["face_mappings"]), 0)
            self.assertEqual(result["statistics"]["total_faces"], 0)
            self.assertEqual(result["statistics"]["total_persons"], 0)

        asyncio.run(run_test())

    def test_single_face(self):
        """Test algorithm behavior with single face detection."""

        async def run_test():
            single_face = [self.sample_faces[0]]

            result = await self.engine.apply_percentage_based_tracking(single_face)

            self.assertEqual(len(result["person_objects"]), 1)
            self.assertEqual(len(result["face_mappings"]), 1)
            self.assertEqual(result["statistics"]["total_faces"], 1)
            self.assertEqual(result["statistics"]["total_persons"], 1)

            # Should be marked as new track
            self.assertEqual(result["face_mappings"][0]["match_type"], "new_track")

        asyncio.run(run_test())

    def test_chronological_processing(self):
        """Test that faces are processed in chronological order by frame."""
        # Create faces with non-sequential frame numbers
        unordered_faces = [
            {
                "id": "face_frame_5",
                "frame_number": 5,
                "position_x": 100.0,
                "position_y": 150.0,
            },
            {
                "id": "face_frame_1",
                "frame_number": 1,
                "position_x": 105.0,
                "position_y": 155.0,
            },
            {
                "id": "face_frame_3",
                "frame_number": 3,
                "position_x": 102.0,
                "position_y": 148.0,
            },
        ]

        async def run_test():
            result = await self.engine.apply_percentage_based_tracking(unordered_faces)

            # Should still group properly despite input order
            self.assertEqual(
                len(result["person_objects"]), 1
            )  # All should group together
            self.assertEqual(result["statistics"]["frames_processed"], 3)

        asyncio.run(run_test())


class TestPersonQualityAnalyzer(unittest.TestCase):
    """Test suite for the PersonQualityAnalyzer class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.analyzer = PersonQualityAnalyzer()

        # Sample face data with quality metrics
        self.sample_face_high_quality = {
            "id": "face_hq_001",
            "detection_confidence": 0.95,
            "brightness": 128,  # Good exposure
            "pixel_std": 45,  # Good contrast
            "noise_level": 0.1,  # Low noise
            "width": 200,  # Good size
            "height": 200,
        }

        self.sample_face_low_quality = {
            "id": "face_lq_001",
            "detection_confidence": 0.45,  # Poor sharpness
            "brightness": 20,  # Poor exposure
            "pixel_std": 5,  # Poor contrast
            "noise_level": 0.8,  # High noise
            "width": 40,  # Small size
            "height": 40,
        }

    def test_quality_score_calculation(self):
        """Test comprehensive quality score calculation."""
        # Test high quality face
        hq_result = self.analyzer.calculate_quality_score(self.sample_face_high_quality)

        self.assertIn("overall_score", hq_result)
        self.assertIn("component_scores", hq_result)
        self.assertIn("quality_category", hq_result)
        self.assertIn("recommendations", hq_result)

        # High quality should score well
        self.assertGreater(hq_result["overall_score"], 0.6)
        self.assertIn(hq_result["quality_category"], ["good", "excellent"])

        # Test low quality face
        lq_result = self.analyzer.calculate_quality_score(self.sample_face_low_quality)

        # Low quality should score poorly
        self.assertLess(lq_result["overall_score"], 0.5)
        self.assertIn(lq_result["quality_category"], ["poor", "acceptable"])

        # Should have recommendations for improvement
        self.assertGreater(len(lq_result["recommendations"]), 0)

    def test_quality_component_scoring(self):
        """Test individual quality component calculations."""
        # Test sharpness scoring
        sharpness_score = self.analyzer._calculate_sharpness_score(
            self.sample_face_high_quality
        )
        self.assertGreater(
            sharpness_score, 0.8
        )  # High confidence should give good sharpness

        # Test exposure scoring
        exposure_score = self.analyzer._calculate_exposure_score(
            self.sample_face_high_quality
        )
        self.assertGreater(
            exposure_score, 0.5
        )  # Good brightness should give decent exposure

        # Test contrast scoring
        contrast_score = self.analyzer._calculate_contrast_score(
            self.sample_face_high_quality
        )
        self.assertGreater(
            contrast_score, 0.5
        )  # Good pixel std should give decent contrast

        # Test noise scoring
        noise_score = self.analyzer._calculate_noise_score(
            self.sample_face_high_quality
        )
        self.assertGreater(noise_score, 0.5)  # Low noise should give good score

        # Test size scoring
        size_score = self.analyzer._calculate_size_score(self.sample_face_high_quality)
        self.assertGreater(size_score, 0.5)  # Good dimensions should give good score

    def test_best_face_selection(self):
        """Test best face selection per person."""
        # Create test data
        person_objects = [{"person_id": "person_1"}, {"person_id": "person_2"}]

        face_detections = [
            {**self.sample_face_high_quality, "id": "face_p1_good"},
            {**self.sample_face_low_quality, "id": "face_p1_bad"},
            {**self.sample_face_high_quality, "id": "face_p2_good"},
        ]

        face_mappings = [
            {"person_id": "person_1", "face_detection_id": "face_p1_good"},
            {"person_id": "person_1", "face_detection_id": "face_p1_bad"},
            {"person_id": "person_2", "face_detection_id": "face_p2_good"},
        ]

        result = self.analyzer.select_best_face_per_person(
            person_objects, face_detections, face_mappings
        )

        # Validate result structure
        self.assertIn("best_faces", result)
        self.assertIn("quality_rankings", result)
        self.assertIn("selection_statistics", result)

        best_faces = result["best_faces"]

        # Should select best face for each person
        self.assertIn("person_1", best_faces)
        self.assertIn("person_2", best_faces)

        # Person 1 should have the good quality face selected (not the bad one)
        p1_best = best_faces["person_1"]
        self.assertEqual(p1_best["face_record"]["id"], "face_p1_good")
        self.assertGreater(p1_best["quality_score"], 0.6)

    def test_quality_filtering(self):
        """Test face filtering based on quality thresholds."""
        face_list = [self.sample_face_high_quality, self.sample_face_low_quality]

        result = self.analyzer.filter_faces_by_quality(face_list, minimum_score=0.5)

        # Validate result structure
        self.assertIn("passed_faces", result)
        self.assertIn("failed_faces", result)
        self.assertIn("filter_statistics", result)

        # High quality should pass, low quality should fail
        self.assertGreater(len(result["passed_faces"]), 0)
        self.assertGreater(len(result["failed_faces"]), 0)

        # Validate statistics
        stats = result["filter_statistics"]
        self.assertEqual(stats["total_faces"], 2)
        self.assertGreater(stats["pass_rate"], 0)

    def test_quality_distribution_analysis(self):
        """Test quality distribution analysis across faces."""
        face_list = [self.sample_face_high_quality, self.sample_face_low_quality]

        result = self.analyzer.get_quality_distribution_analysis(face_list)

        # Validate result structure
        required_keys = [
            "total_faces",
            "quality_statistics",
            "component_averages",
            "quality_categories",
            "category_percentages",
        ]
        for key in required_keys:
            self.assertIn(key, result)

        # Validate statistics
        self.assertEqual(result["total_faces"], 2)

        quality_stats = result["quality_statistics"]
        self.assertIn("average_score", quality_stats)
        self.assertIn("minimum_score", quality_stats)
        self.assertIn("maximum_score", quality_stats)


class TestPhase2Integration(unittest.TestCase):
    """Integration tests for Phase 2 face grouping and quality analysis."""

    def setUp(self):
        """Set up test fixtures for integration testing."""
        self.grouping_engine = VisionFaceGroupingEngine()
        self.quality_analyzer = PersonQualityAnalyzer()

        # Create comprehensive test dataset
        self.test_faces = [
            # Person 1 - High quality group
            {
                "id": "face_p1_f1",
                "frame_number": 1,
                "position_x": 100.0,
                "position_y": 150.0,
                "detection_confidence": 0.95,
                "brightness": 128,
                "width": 200,
                "height": 200,
            },
            {
                "id": "face_p1_f2",
                "frame_number": 3,
                "position_x": 105.0,
                "position_y": 155.0,  # Close position
                "detection_confidence": 0.88,
                "brightness": 135,
                "width": 190,
                "height": 195,
            },
            # Person 2 - Lower quality
            {
                "id": "face_p2_f1",
                "frame_number": 2,
                "position_x": 300.0,
                "position_y": 200.0,  # Far position
                "detection_confidence": 0.65,
                "brightness": 80,
                "width": 150,
                "height": 140,
            },
            # Person 1 again - Best quality
            {
                "id": "face_p1_f3",
                "frame_number": 4,
                "position_x": 98.0,
                "position_y": 152.0,  # Close to P1
                "detection_confidence": 0.98,
                "brightness": 140,  # Best quality
                "width": 220,
                "height": 210,
            },
        ]

    def test_end_to_end_workflow(self):
        """Test complete end-to-end person object workflow."""

        async def run_test():
            # Step 1: Face Grouping
            grouping_result = (
                await self.grouping_engine.apply_percentage_based_tracking(
                    self.test_faces
                )
            )

            # Step 2: Quality Analysis and Best Face Selection
            quality_result = self.quality_analyzer.select_best_face_per_person(
                grouping_result["person_objects"],
                self.test_faces,
                grouping_result["face_mappings"],
            )

            # Step 3: Validate integrated results

            # Should have 2 persons (P1 group + P2 individual)
            self.assertEqual(len(grouping_result["person_objects"]), 2)

            # Should have best faces for both persons
            self.assertEqual(len(quality_result["best_faces"]), 2)

            # Find person 1 (should have 3 faces: face_p1_f1, face_p1_f2, face_p1_f3)
            person_face_counts = {}
            for mapping in grouping_result["face_mappings"]:
                person_id = mapping["person_id"]
                if person_id not in person_face_counts:
                    person_face_counts[person_id] = 0
                person_face_counts[person_id] += 1

            # One person should have 3 faces, other should have 1
            face_counts = sorted(person_face_counts.values())
            self.assertEqual(face_counts, [1, 3])

            # Best face for person with 3 faces should be face_p1_f3 (highest confidence)
            person_with_3_faces = None
            for person_id, count in person_face_counts.items():
                if count == 3:
                    person_with_3_faces = person_id
                    break

            self.assertIsNotNone(person_with_3_faces)

            best_face_for_p1 = quality_result["best_faces"][person_with_3_faces]
            self.assertEqual(best_face_for_p1["face_record"]["id"], "face_p1_f3")

            # Validate quality scores are reasonable
            for person_id, best_face_data in quality_result["best_faces"].items():
                self.assertGreaterEqual(best_face_data["quality_score"], 0.0)
                self.assertLessEqual(best_face_data["quality_score"], 1.0)

        asyncio.run(run_test())

    def test_performance_with_large_dataset(self):
        """Test performance with larger face detection dataset."""
        # Generate larger test dataset
        large_dataset = []

        # Create 5 persons with 10 faces each
        for person_id in range(5):
            base_x = person_id * 200 + 100
            base_y = person_id * 150 + 100

            for face_id in range(10):
                face = {
                    "id": f"face_p{person_id}_f{face_id}",
                    "frame_number": face_id + 1,
                    "position_x": base_x + (face_id * 2),  # Slight movement
                    "position_y": base_y + (face_id * 2),
                    "detection_confidence": 0.8 + (face_id * 0.02),  # Improving quality
                    "brightness": 100 + (face_id * 5),
                    "width": 150 + face_id * 5,
                    "height": 150 + face_id * 5,
                }
                large_dataset.append(face)

        async def run_test():
            # Time the grouping operation
            start_time = datetime.now()

            grouping_result = (
                await self.grouping_engine.apply_percentage_based_tracking(
                    large_dataset
                )
            )

            grouping_time = (datetime.now() - start_time).total_seconds()

            # Time the quality analysis
            start_time = datetime.now()

            quality_result = self.quality_analyzer.select_best_face_per_person(
                grouping_result["person_objects"],
                large_dataset,
                grouping_result["face_mappings"],
            )

            quality_time = (datetime.now() - start_time).total_seconds()

            # Validate results
            self.assertEqual(len(grouping_result["person_objects"]), 5)  # 5 persons
            self.assertEqual(
                len(grouping_result["face_mappings"]), 50
            )  # 50 faces total

            # Performance should be reasonable (< 1 second for 50 faces)
            self.assertLess(grouping_time, 1.0, f"Grouping took {grouping_time:.3f}s")
            self.assertLess(
                quality_time, 1.0, f"Quality analysis took {quality_time:.3f}s"
            )

            # Each person should have best face selected
            self.assertEqual(len(quality_result["best_faces"]), 5)

        asyncio.run(run_test())

    def test_algorithm_consistency(self):
        """Test that algorithm produces consistent results across multiple runs."""

        async def run_test():
            results = []

            # Run algorithm multiple times
            for _ in range(3):
                result = await self.grouping_engine.apply_percentage_based_tracking(
                    self.test_faces
                )
                results.append(result)

            # Results should be identical across runs (deterministic algorithm)
            first_result = results[0]

            for i, result in enumerate(results[1:], 1):
                # Same number of persons and mappings
                self.assertEqual(
                    len(result["person_objects"]),
                    len(first_result["person_objects"]),
                    f"Run {i+1} has different person count",
                )

                self.assertEqual(
                    len(result["face_mappings"]),
                    len(first_result["face_mappings"]),
                    f"Run {i+1} has different mapping count",
                )

                # Same statistics
                self.assertEqual(
                    result["statistics"]["total_faces"],
                    first_result["statistics"]["total_faces"],
                    f"Run {i+1} has different face count",
                )

        asyncio.run(run_test())


def run_phase2_tests():
    """
    Run all Phase 2 tests and return comprehensive results.
    """
    print("=" * 80)
    print("PPL Meta Vision Service - Phase 2 Core Face Grouping Engine Tests")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestVisionFaceGroupingEngine,
        TestPersonQualityAnalyzer,
        TestPhase2Integration,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2, stream=sys.stdout, descriptions=True, failfast=False
    )

    print(f"Running {suite.countTestCases()} Phase 2 tests...")
    print()

    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 80)
    print("PHASE 2 TEST RESULTS SUMMARY")
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
        print("🎉 ALL PHASE 2 TESTS PASSED! Core face grouping engine is ready.")
        return True
    else:
        print("⚠️ Some Phase 2 tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    success = run_phase2_tests()
    sys.exit(0 if success else 1)
