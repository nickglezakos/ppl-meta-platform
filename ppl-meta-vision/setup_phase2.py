#!/usr/bin/env python3
"""
PPL Meta Vision Service - Phase 2 Setup Script
Sets up and validates the Core Face Grouping Engine implementation.

This script:
1. Validates Phase 2 module structure
2. Tests core face grouping engine functionality
3. Tests quality analyzer functionality
4. Runs comprehensive integration tests
5. Provides setup status and recommendations

Usage:
    python setup_phase2.py
"""

import os
import sys
import traceback
from pathlib import Path


def setup_python_path():
    """Setup Python path for module imports."""
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"

    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
    else:
        print(f"❌ Source directory not found: {src_dir}")
        return False

    return True


def validate_module_structure():
    """Validate that Phase 2 module structure is correct."""
    print("🔍 Validating Phase 2 module structure...")

    required_files = [
        "src/person_objects/__init__.py",
        "src/person_objects/face_grouping_engine.py",
        "src/person_objects/quality_analyzer.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print("❌ Missing required Phase 2 files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False

    print("✅ All Phase 2 module files present")
    return True


def test_imports():
    """Test that Phase 2 modules can be imported successfully."""
    print("📦 Testing Phase 2 module imports...")

    try:
        from person_objects import PersonQualityAnalyzer, VisionFaceGroupingEngine

        print("✅ VisionFaceGroupingEngine import successful")
        print("✅ PersonQualityAnalyzer import successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def test_face_grouping_engine():
    """Test basic VisionFaceGroupingEngine functionality."""
    print("⚙️ Testing VisionFaceGroupingEngine core functionality...")

    try:
        from person_objects import VisionFaceGroupingEngine

        engine = VisionFaceGroupingEngine()

        # Test 1: Position distance calculation
        pos1 = {"x": 100.0, "y": 150.0}
        pos2 = {"x": 105.0, "y": 155.0}

        distance_result = engine.calculate_position_distance(pos1, pos2)

        required_keys = [
            "x_distance",
            "y_distance",
            "euclidean_distance",
            "combined_distance",
            "within_tolerance",
        ]

        for key in required_keys:
            if key not in distance_result:
                print(f"❌ Missing key in distance result: {key}")
                return False

        print("✅ Position distance calculation working")

        # Test 2: Face position extraction
        test_face = {"position_x": 100.0, "position_y": 150.0, "id": "test_face"}

        position = engine._extract_face_position(test_face)

        if position != {"x": 100.0, "y": 150.0}:
            print(f"❌ Face position extraction failed: {position}")
            return False

        print("✅ Face position extraction working")

        # Test 3: Face detection validation
        valid_face = {
            "id": "test_face",
            "frame_number": 1,
            "position_x": 100.0,
            "position_y": 150.0,
        }

        errors = engine.validate_face_detections([valid_face])
        if len(errors) != 0:
            print(f"❌ Valid face failed validation: {errors}")
            return False

        print("✅ Face detection validation working")

        return True

    except Exception as e:
        print(f"❌ VisionFaceGroupingEngine test failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def test_quality_analyzer():
    """Test basic PersonQualityAnalyzer functionality."""
    print("📊 Testing PersonQualityAnalyzer core functionality...")

    try:
        from person_objects import PersonQualityAnalyzer

        analyzer = PersonQualityAnalyzer()

        # Test 1: Quality score calculation
        test_face = {
            "id": "test_face",
            "detection_confidence": 0.95,
            "brightness": 128,
            "width": 200,
            "height": 200,
        }

        quality_result = analyzer.calculate_quality_score(test_face)

        required_keys = [
            "overall_score",
            "component_scores",
            "quality_category",
            "recommendations",
        ]

        for key in required_keys:
            if key not in quality_result:
                print(f"❌ Missing key in quality result: {key}")
                return False

        # Score should be between 0 and 1
        score = quality_result["overall_score"]
        if not (0.0 <= score <= 1.0):
            print(f"❌ Quality score out of range: {score}")
            return False

        print("✅ Quality score calculation working")

        # Test 2: Quality component scoring
        sharpness = analyzer._calculate_sharpness_score(test_face)
        if not (0.0 <= sharpness <= 1.0):
            print(f"❌ Sharpness score out of range: {sharpness}")
            return False

        print("✅ Quality component scoring working")

        # Test 3: Quality distribution analysis
        face_list = [test_face]
        distribution = analyzer.get_quality_distribution_analysis(face_list)

        if distribution["total_faces"] != 1:
            print(f"❌ Distribution analysis failed: {distribution}")
            return False

        print("✅ Quality distribution analysis working")

        return True

    except Exception as e:
        print(f"❌ PersonQualityAnalyzer test failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between face grouping and quality analysis."""
    print("🔗 Testing Phase 2 integration...")

    try:
        import asyncio

        from person_objects import PersonQualityAnalyzer, VisionFaceGroupingEngine

        # Create test data
        test_faces = [
            {
                "id": "face_001",
                "frame_number": 1,
                "position_x": 100.0,
                "position_y": 150.0,
                "detection_confidence": 0.95,
                "width": 200,
                "height": 200,
            },
            {
                "id": "face_002",
                "frame_number": 2,
                "position_x": 105.0,  # Close to face_001
                "position_y": 155.0,
                "detection_confidence": 0.88,
                "width": 180,
                "height": 180,
            },
        ]

        async def run_integration_test():
            engine = VisionFaceGroupingEngine()
            analyzer = PersonQualityAnalyzer()

            # Step 1: Face grouping
            grouping_result = await engine.apply_percentage_based_tracking(test_faces)

            if len(grouping_result["person_objects"]) != 1:
                print(
                    f"❌ Expected 1 person, got {len(grouping_result['person_objects'])}"
                )
                return False

            if len(grouping_result["face_mappings"]) != 2:
                print(
                    f"❌ Expected 2 face mappings, got {len(grouping_result['face_mappings'])}"
                )
                return False

            print("✅ Face grouping successful")

            # Step 2: Quality analysis
            quality_result = analyzer.select_best_face_per_person(
                grouping_result["person_objects"],
                test_faces,
                grouping_result["face_mappings"],
            )

            if len(quality_result["best_faces"]) != 1:
                print(
                    f"❌ Expected 1 best face, got {len(quality_result['best_faces'])}"
                )
                return False

            print("✅ Quality analysis successful")

            # Step 3: Validate integration
            person_id = list(quality_result["best_faces"].keys())[0]
            best_face_data = quality_result["best_faces"][person_id]

            if "quality_score" not in best_face_data:
                print("❌ Missing quality score in best face data")
                return False

            if not (0.0 <= best_face_data["quality_score"] <= 1.0):
                print(f"❌ Invalid quality score: {best_face_data['quality_score']}")
                return False

            print("✅ Integration validation successful")
            return True

        # Run the async test
        success = asyncio.run(run_integration_test())

        if success:
            print("✅ Phase 2 integration test passed")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def print_setup_summary(results):
    """Print Phase 2 setup summary with results."""
    print("\n" + "=" * 80)
    print("PPL META VISION SERVICE - PHASE 2 SETUP SUMMARY")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    print(f"\nSetup Tests: {passed_tests}/{total_tests} passed")
    print("\nTest Results:")

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")

    print("\n" + "=" * 80)

    if all(results.values()):
        print("🎉 PHASE 2 SETUP SUCCESSFUL!")
        print("\nCore Face Grouping Engine is ready for use.")
        print("\nNext Steps:")
        print("- Run full test suite: python test_phase2_core_face_grouping.py")
        print("- Integrate with PPL Meta Vision Service")
        print("- Test with real face detection data")

        print("\nPhase 2 Features Available:")
        print("✅ VisionFaceGroupingEngine - Percentage-based face tracking")
        print("✅ PersonQualityAnalyzer - Quality scoring and best face selection")
        print("✅ Independent implementation (no PPL Mini dependencies)")
        print("✅ Full algorithm compatibility with PPL Meta Mini")
    else:
        print("⚠️ PHASE 2 SETUP INCOMPLETE")
        print("\nSome components failed validation. Please review and fix:")

        for test_name, passed in results.items():
            if not passed:
                print(f"❌ {test_name}")

        print("\nRecommendations:")
        print("- Check import paths and module structure")
        print("- Verify all required files are present")
        print("- Review error messages above for specific issues")

    print("=" * 80)

    return all(results.values())


def main():
    """Main Phase 2 setup function."""
    print("🚀 PPL Meta Vision Service - Phase 2 Setup")
    print("Setting up Core Face Grouping Engine...")
    print()

    # Track test results
    results = {}

    # Setup Python path
    if not setup_python_path():
        print("❌ Failed to setup Python path")
        return False

    # Run setup tests
    results["Module Structure"] = validate_module_structure()
    results["Module Imports"] = test_imports() if results["Module Structure"] else False
    results["Face Grouping Engine"] = (
        test_face_grouping_engine() if results["Module Imports"] else False
    )
    results["Quality Analyzer"] = (
        test_quality_analyzer() if results["Module Imports"] else False
    )
    results["Integration Test"] = (
        test_integration()
        if all([results["Face Grouping Engine"], results["Quality Analyzer"]])
        else False
    )

    # Print summary
    success = print_setup_summary(results)

    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during setup: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)
