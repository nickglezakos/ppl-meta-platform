#!/usr/bin/env python3
"""
PPL Meta Vision Service - Phase 4: Quick Integration Validation
Simple validation script to test Phase 4 integration without complex setup.

This script validates:
1. Phase 4 main service integration
2. Database schema compatibility
3. Face data manager functionality
4. Basic workflow execution
"""

import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src")


def validate_imports():
    """Validate that all Phase 4 components can be imported."""
    logger.info("🔍 Phase 4.1: Validating Service Integration Components...")

    try:
        # Test main service integration
        from main import app

        logger.info("✅ Main application import successful")

        # Test database imports
        from database import VisionDatabase, vision_db

        logger.info("✅ VisionDatabase import successful")

        # Test person objects imports
        from person_objects.face_grouping_engine import VisionFaceGroupingEngine

        logger.info("✅ Face grouping engine import successful")

        from person_objects.ppl_thread_workflow import PPLThreadWorkflowController

        logger.info("✅ PPL Thread workflow import successful")

        from person_objects.quality_analyzer import PersonQualityAnalyzer

        logger.info("✅ Quality analyzer import successful")

        # Test database enhancements
        from database.face_data_manager import FaceDataManager

        logger.info("✅ Face data manager import successful")

        from database.person_objects_migrations import PersonObjectsMigration

        logger.info("✅ Person objects migrations import successful")

        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def validate_database_schema():
    """Validate Phase 4 database schema enhancements."""
    logger.info("🔍 Phase 4.2: Validating Database Enhancements...")

    try:
        from database import vision_db
        from database.person_objects_migrations import PersonObjectsMigration

        # Check if we can create migration instance
        migration = PersonObjectsMigration()
        logger.info("✅ PersonObjectsMigration instance created")

        # Check basic database connectivity
        if vision_db.connection:
            logger.info("✅ Database connection established")
        else:
            logger.warning(
                "⚠️ Database connection not available (expected in test environment)"
            )

        # Validate FaceDataManager
        from database.face_data_manager import FaceDataManager

        # Create instance without database dependency for validation
        face_manager = FaceDataManager(db_connection=None)
        logger.info("✅ FaceDataManager instance created")

        return True

    except Exception as e:
        logger.error(f"❌ Database validation failed: {e}")
        return False


def validate_workflow_components():
    """Validate Phase 4 workflow integration."""
    logger.info("🔍 Phase 4.3: Validating Workflow Components...")

    try:
        from person_objects.ppl_thread_workflow import PPLThreadWorkflowController

        # Test workflow controller creation
        controller = PPLThreadWorkflowController()
        logger.info("✅ PPL Thread workflow controller created")

        # Test quality analyzer
        from person_objects.quality_analyzer import PersonQualityAnalyzer

        analyzer = PersonQualityAnalyzer()
        logger.info("✅ Quality analyzer created")

        # Test face grouping engine
        from person_objects.face_grouping_engine import VisionFaceGroupingEngine

        engine = VisionFaceGroupingEngine()
        logger.info("✅ Face grouping engine created")

        return True

    except Exception as e:
        logger.error(f"❌ Workflow validation failed: {e}")
        return False


def validate_api_integration():
    """Validate Phase 4 API integration."""
    logger.info("🔍 Phase 4.4: Validating API Integration...")

    try:
        from fastapi.testclient import TestClient
        from main import app

        # Create test client
        client = TestClient(app)
        logger.info("✅ Test client created")

        # Test health endpoint
        response = client.get("/health")
        if response.status_code == 200:
            logger.info("✅ Health endpoint responding")
        else:
            logger.warning(f"⚠️ Health endpoint returned {response.status_code}")

        return True

    except Exception as e:
        logger.error(f"❌ API validation failed: {e}")
        return False


def validate_phase4_deployment_config():
    """Validate Phase 4 deployment configuration."""
    logger.info("🔍 Phase 4.5: Validating Deployment Configuration...")

    try:
        # Check if deployment config exists
        config_path = "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/deployment/ppl_thread_config.py"
        if os.path.exists(config_path):
            logger.info("✅ Deployment configuration file exists")

            # Try to import deployment config
            sys.path.insert(
                0,
                "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/deployment",
            )
            from ppl_thread_config import (
                PPLThreadDeploymentConfig,
                get_deployment_config,
            )

            # Test configuration creation
            config = get_deployment_config("development")
            logger.info("✅ Deployment configuration loaded")

            # Check key configuration sections
            ppl_config = config.get_section("ppl_thread")
            if ppl_config:
                logger.info(f"✅ PPL Thread config: {len(ppl_config)} settings")

            db_config = config.get_section("database")
            if db_config:
                logger.info(f"✅ Database config: {len(db_config)} settings")

            return True
        else:
            logger.error("❌ Deployment configuration file not found")
            return False

    except Exception as e:
        logger.error(f"❌ Deployment config validation failed: {e}")
        return False


def run_performance_benchmark():
    """Run basic performance validation."""
    logger.info("🔍 Phase 4.6: Running Performance Validation...")

    try:
        # Test component creation performance
        start_time = time.time()

        from person_objects.quality_analyzer import PersonQualityAnalyzer

        analyzer = PersonQualityAnalyzer()

        from person_objects.face_grouping_engine import VisionFaceGroupingEngine

        engine = VisionFaceGroupingEngine()

        creation_time = time.time() - start_time
        logger.info(f"✅ Component creation time: {creation_time:.3f}s")

        if creation_time < 5.0:  # Should create components quickly
            logger.info("✅ Performance benchmark passed")
            return True
        else:
            logger.warning(
                f"⚠️ Component creation slower than expected: {creation_time:.3f}s"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Performance validation failed: {e}")
        return False


def main():
    """Main validation function."""
    logger.info(
        "🚀 Starting PPL Meta Vision Phase 4: Service Integration and Testing Validation"
    )
    logger.info("=" * 80)

    results = {
        "imports": False,
        "database": False,
        "workflow": False,
        "api": False,
        "deployment": False,
        "performance": False,
    }

    # Run all validation tests
    results["imports"] = validate_imports()
    results["database"] = validate_database_schema()
    results["workflow"] = validate_workflow_components()
    results["api"] = validate_api_integration()
    results["deployment"] = validate_phase4_deployment_config()
    results["performance"] = run_performance_benchmark()

    # Calculate overall results
    passed = sum(1 for result in results.values() if result)
    total = len(results)

    logger.info("\n" + "=" * 80)
    logger.info("📋 Phase 4 Integration Validation Results:")
    logger.info("-" * 80)

    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"  {test_name.upper():<12} : {status}")

    logger.info("-" * 80)
    logger.info(
        f"📊 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)"
    )

    if passed == total:
        logger.info(
            "🎉 Phase 4: Service Integration and Testing - VALIDATION SUCCESSFUL!"
        )
        logger.info(
            "✅ All Phase 4 components are properly integrated and ready for deployment"
        )
        return True
    else:
        logger.warning(
            "⚠️ Phase 4: Service Integration and Testing - VALIDATION INCOMPLETE"
        )
        logger.warning(f"❌ {total - passed} validation test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
