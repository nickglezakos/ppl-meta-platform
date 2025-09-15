#!/usr/bin/env python3
"""
Face Detection Workflow 5 - Phase 5: Comprehensive Validation Test Suite
=========================================================================

FINAL VALIDATION FRAMEWORK FOR COMPLETE WORKFLOW 5 SYSTEM

This module provides the final validation framework for the complete Face Detection
Workflow 5 system, ensuring data integrity, processing accuracy, performance compliance,
and end-to-end functionality before production deployment.

Validation Categories:
1. Data Integrity Validation - Verify data consistency and accuracy
2. Processing Status Validation - Confirm correct workflow state management
3. Performance Metrics Validation - Validate against defined benchmarks
4. End-to-End Workflow Validation - Complete system operation verification
5. Production Readiness Assessment - Final deployment validation

Key Features:
- Comprehensive data validation algorithms
- Performance benchmark compliance testing
- Workflow state integrity verification
- Production deployment readiness assessment
- Detailed validation reporting and recommendations
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from workflow5_data_access import Workflow5DataAccess
from workflow5_error_recovery_system import (
    ErrorRecoverySystem,
    ErrorType,
    create_error_recovery_system,
)
from workflow5_face_data_retrieval_fixed import (
    StoredFaceDataRetriever,
    create_stored_face_data_retriever,
)
from workflow5_fallback_manager import (
    FallbackManager,
    FallbackMode,
    create_fallback_manager,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation test."""

    validation_name: str
    passed: bool
    score: float  # 0.0 to 100.0
    details: Dict[str, Any]
    recommendations: List[str]
    critical_issues: List[str]


@dataclass
class ProductionReadinessAssessment:
    """Final production readiness assessment."""

    overall_score: float
    deployment_ready: bool
    critical_blockers: List[str]
    recommendations: List[str]
    validation_summary: Dict[str, Any]


class Workflow5ValidationSuite:
    """
    Comprehensive validation suite for Face Detection Workflow 5.

    Provides final validation and production readiness assessment
    for the complete Workflow 5 system.
    """

    def __init__(self):
        self.data_access: Optional[Workflow5DataAccess] = None
        self.stored_retriever: Optional[StoredFaceDataRetriever] = None
        self.fallback_manager: Optional[FallbackManager] = None
        self.error_recovery: Optional[ErrorRecoverySystem] = None

        # Validation results
        self.validation_results: List[ValidationResult] = []

        # Production readiness criteria
        self.production_criteria = {
            "min_overall_score": 85.0,
            "max_critical_issues": 0,
            "required_validations": [
                "data_integrity",
                "performance_compliance",
                "error_recovery",
                "end_to_end_functionality",
            ],
        }

        # Performance benchmarks
        self.performance_benchmarks = {
            "max_retrieval_latency_ms": 50,
            "min_cache_hit_rate_percent": 80,
            "max_memory_usage_mb": 500,
            "min_fallback_success_rate_percent": 95,
            "max_error_recovery_time_ms": 1000,
        }

    async def setup(self):
        """Initialize validation environment."""
        logger.info("Setting up Workflow 5 validation environment...")

        # Initialize all components
        self.data_access = Workflow5DataAccess()
        self.stored_retriever = await create_stored_face_data_retriever()
        self.fallback_manager = await create_fallback_manager()
        self.error_recovery = await create_error_recovery_system()

        logger.info("Validation environment setup complete")

    async def run_complete_validation(self) -> ProductionReadinessAssessment:
        """Run complete validation suite and assess production readiness."""
        logger.info("🔍 Starting Complete Workflow 5 Validation Suite...")

        validation_start_time = time.time()

        # Run all validation categories
        validation_categories = [
            ("Data Integrity", self._validate_data_integrity),
            ("Processing Status", self._validate_processing_status),
            ("Performance Compliance", self._validate_performance_compliance),
            ("End-to-End Workflow", self._validate_end_to_end_workflow),
            ("Error Recovery", self._validate_error_recovery),
            ("System Resources", self._validate_system_resources),
        ]

        for category_name, validation_method in validation_categories:
            logger.info(f"\n📋 Validating {category_name}...")
            try:
                result = await validation_method()
                self.validation_results.append(result)

                status = "✅ PASSED" if result.passed else "❌ FAILED"
                logger.info(f"{status} - Score: {result.score:.1f}%")

                if result.critical_issues:
                    for issue in result.critical_issues:
                        logger.error(f"  🚨 CRITICAL: {issue}")

            except Exception as e:
                logger.error(f"❌ Validation {category_name} failed: {e}")
                self.validation_results.append(
                    ValidationResult(
                        validation_name=category_name.lower().replace(" ", "_"),
                        passed=False,
                        score=0.0,
                        details={"error": str(e)},
                        recommendations=[f"Fix validation error: {e}"],
                        critical_issues=[f"Validation failed with error: {e}"],
                    )
                )

        total_time = (time.time() - validation_start_time) * 1000

        # Generate production readiness assessment
        assessment = self._generate_production_readiness_assessment(total_time)

        return assessment

    async def _validate_data_integrity(self) -> ValidationResult:
        """Validate data integrity across the system."""
        validation_start = time.time()

        integrity_checks = []
        critical_issues = []
        recommendations = []

        try:
            # Check 1: Database consistency
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                # Check for orphaned face detections
                orphaned_faces = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM face_detections fd
                    LEFT JOIN media_records mr ON fd.media_id = mr.media_id
                    WHERE mr.media_id IS NULL
                """
                    )
                )
                orphaned_count = orphaned_faces.scalar()

                if orphaned_count > 0:
                    critical_issues.append(
                        f"Found {orphaned_count} orphaned face detections"
                    )
                    recommendations.append("Clean up orphaned face detections")

                integrity_checks.append(
                    {
                        "check": "orphaned_faces",
                        "passed": orphaned_count == 0,
                        "count": orphaned_count,
                    }
                )

                # Check for data format consistency
                invalid_bbox = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM face_detections
                    WHERE bbox_x1 < 0 OR bbox_y1 < 0
                    OR (bbox_x2 - bbox_x1) <= 0 OR (bbox_y2 - bbox_y1) <= 0
                """
                    )
                )
                invalid_count = invalid_bbox.scalar()

                if invalid_count > 0:
                    critical_issues.append(
                        f"Found {invalid_count} invalid bounding boxes"
                    )
                    recommendations.append("Validate and fix bounding box data")

                integrity_checks.append(
                    {
                        "check": "invalid_bounding_boxes",
                        "passed": invalid_count == 0,
                        "count": invalid_count,
                    }
                )

        except Exception as e:
            critical_issues.append(f"Database integrity check failed: {e}")
            integrity_checks.append(
                {"check": "database_access", "passed": False, "error": str(e)}
            )

        # Check 2: Cache data consistency
        try:
            if self.stored_retriever:
                cache_inconsistencies = 0

                # Test a few cached items for consistency
                for media_uuid, cached_data in list(
                    self.stored_retriever.cache.items()
                )[:5]:
                    try:
                        # Reload from database
                        fresh_data = await self.stored_retriever.load_complete_video(
                            media_uuid, force_reload=True
                        )

                        # Compare face counts
                        if cached_data.total_faces != fresh_data.total_faces:
                            cache_inconsistencies += 1

                    except Exception:
                        cache_inconsistencies += 1

                if cache_inconsistencies > 0:
                    recommendations.append(
                        f"Found {cache_inconsistencies} cache inconsistencies - "
                        "consider cache invalidation"
                    )

                integrity_checks.append(
                    {
                        "check": "cache_consistency",
                        "passed": cache_inconsistencies == 0,
                        "inconsistencies": cache_inconsistencies,
                    }
                )

        except Exception as e:
            recommendations.append(f"Cache consistency check failed: {e}")

        # Calculate overall score
        passed_checks = sum(
            1 for check in integrity_checks if check.get("passed", False)
        )
        total_checks = len(integrity_checks)
        score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        validation_time = (time.time() - validation_start) * 1000

        return ValidationResult(
            validation_name="data_integrity",
            passed=len(critical_issues) == 0 and score >= 90,
            score=score,
            details={
                "integrity_checks": integrity_checks,
                "validation_time_ms": validation_time,
                "total_checks": total_checks,
                "passed_checks": passed_checks,
            },
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    async def _validate_processing_status(self) -> ValidationResult:
        """Validate processing status accuracy."""
        validation_start = time.time()

        status_checks = []
        critical_issues = []
        recommendations = []

        try:
            # Check processing status accuracy
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                # Check for records marked as processed but no face detections
                unprocessed_with_status = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM media_records mr
                    WHERE mr.processing_status = 'completed'
                    AND NOT EXISTS (
                        SELECT 1 FROM face_detections fd 
                        WHERE fd.media_id = mr.media_id
                    )
                """
                    )
                )
                unprocessed_count = unprocessed_with_status.scalar()

                if unprocessed_count > 0:
                    critical_issues.append(
                        f"Found {unprocessed_count} records marked as processed "
                        "but no face detections found"
                    )
                    recommendations.append(
                        "Investigate and fix processing status inconsistencies"
                    )

                status_checks.append(
                    {
                        "check": "processing_status_accuracy",
                        "passed": unprocessed_count == 0,
                        "inconsistent_records": unprocessed_count,
                    }
                )

                # Check for incomplete processing
                incomplete_processing = await session.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM media_records
                    WHERE processing_status IN ('processing', 'pending')
                    AND created_at < NOW() - INTERVAL '1 hour'
                """
                    )
                )
                incomplete_count = incomplete_processing.scalar()

                if incomplete_count > 0:
                    recommendations.append(
                        f"Found {incomplete_count} records with stale processing status"
                    )

                status_checks.append(
                    {
                        "check": "stale_processing_status",
                        "passed": incomplete_count == 0,
                        "stale_records": incomplete_count,
                    }
                )

        except Exception as e:
            critical_issues.append(f"Processing status validation failed: {e}")
            status_checks.append(
                {"check": "status_validation", "passed": False, "error": str(e)}
            )

        # Calculate score
        passed_checks = sum(1 for check in status_checks if check.get("passed", False))
        total_checks = len(status_checks)
        score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        validation_time = (time.time() - validation_start) * 1000

        return ValidationResult(
            validation_name="processing_status",
            passed=len(critical_issues) == 0 and score >= 80,
            score=score,
            details={
                "status_checks": status_checks,
                "validation_time_ms": validation_time,
            },
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    async def _validate_performance_compliance(self) -> ValidationResult:
        """Validate performance against benchmarks."""
        validation_start = time.time()

        performance_tests = []
        critical_issues = []
        recommendations = []

        try:
            # Get test media for performance testing
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT media_id FROM media_records LIMIT 5")
                )
                test_media_uuids = [row[0] for row in result.fetchall()]

            if not test_media_uuids:
                critical_issues.append(
                    "No test media available for performance testing"
                )
                test_media_uuids = ["mock-uuid-1", "mock-uuid-2"]

            # Test 1: Retrieval latency
            latencies = []
            for media_uuid in test_media_uuids[:3]:
                try:
                    start_time = time.time()
                    await self.stored_retriever.get_frame_faces(media_uuid, 1)
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)
                except Exception:
                    latencies.append(999)  # High penalty for failures

            avg_latency = statistics.mean(latencies) if latencies else 999
            max_latency = max(latencies) if latencies else 999

            latency_passed = (
                avg_latency <= self.performance_benchmarks["max_retrieval_latency_ms"]
            )
            if not latency_passed:
                critical_issues.append(
                    f"Average retrieval latency {avg_latency:.1f}ms exceeds "
                    f"benchmark {self.performance_benchmarks['max_retrieval_latency_ms']}ms"
                )
                recommendations.append("Optimize data retrieval performance")

            performance_tests.append(
                {
                    "test": "retrieval_latency",
                    "passed": latency_passed,
                    "avg_latency_ms": round(avg_latency, 2),
                    "max_latency_ms": round(max_latency, 2),
                    "benchmark_ms": self.performance_benchmarks[
                        "max_retrieval_latency_ms"
                    ],
                }
            )

            # Test 2: Fallback performance
            fallback_start = time.time()
            faces, mode = await self.fallback_manager.get_faces_with_fallback(
                "non-existent-uuid", 1, FallbackMode.STORED_DATA
            )
            fallback_time = (time.time() - fallback_start) * 1000

            fallback_stats = self.fallback_manager.get_fallback_statistics()
            fallback_success_rate = fallback_stats["fallback_performance"][
                "success_rate_percent"
            ]

            fallback_passed = (
                fallback_success_rate
                >= self.performance_benchmarks["min_fallback_success_rate_percent"]
            )
            if not fallback_passed:
                recommendations.append("Improve fallback mechanism reliability")

            performance_tests.append(
                {
                    "test": "fallback_performance",
                    "passed": fallback_passed,
                    "success_rate_percent": fallback_success_rate,
                    "avg_recovery_time_ms": fallback_stats["fallback_performance"][
                        "avg_recovery_time_ms"
                    ],
                    "benchmark_success_rate": self.performance_benchmarks[
                        "min_fallback_success_rate_percent"
                    ],
                }
            )

            # Test 3: Memory usage
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)

            memory_passed = (
                memory_mb <= self.performance_benchmarks["max_memory_usage_mb"]
            )
            if not memory_passed:
                recommendations.append("Optimize memory usage")

            performance_tests.append(
                {
                    "test": "memory_usage",
                    "passed": memory_passed,
                    "current_memory_mb": round(memory_mb, 2),
                    "benchmark_mb": self.performance_benchmarks["max_memory_usage_mb"],
                }
            )

        except Exception as e:
            critical_issues.append(f"Performance validation failed: {e}")
            performance_tests.append(
                {"test": "performance_validation", "passed": False, "error": str(e)}
            )

        # Calculate score
        passed_tests = sum(1 for test in performance_tests if test.get("passed", False))
        total_tests = len(performance_tests)
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        validation_time = (time.time() - validation_start) * 1000

        return ValidationResult(
            validation_name="performance_compliance",
            passed=len(critical_issues) == 0 and score >= 80,
            score=score,
            details={
                "performance_tests": performance_tests,
                "validation_time_ms": validation_time,
                "benchmarks": self.performance_benchmarks,
            },
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    async def _validate_end_to_end_workflow(self) -> ValidationResult:
        """Validate complete end-to-end workflow functionality."""
        validation_start = time.time()

        workflow_tests = []
        critical_issues = []
        recommendations = []

        try:
            # Get test media
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT media_id FROM media_records LIMIT 3")
                )
                test_media_uuids = [row[0] for row in result.fetchall()]

            if not test_media_uuids:
                test_media_uuids = ["test-uuid-1", "test-uuid-2"]

            # Test 1: Complete video loading workflow
            successful_loads = 0
            total_attempts = len(test_media_uuids)

            for media_uuid in test_media_uuids:
                try:
                    video_data = await self.stored_retriever.load_complete_video(
                        media_uuid
                    )
                    if video_data:
                        successful_loads += 1
                except Exception:
                    pass

            load_success_rate = (
                (successful_loads / total_attempts * 100) if total_attempts > 0 else 0
            )
            load_passed = load_success_rate >= 80

            if not load_passed:
                recommendations.append("Improve video loading reliability")

            workflow_tests.append(
                {
                    "test": "video_loading_workflow",
                    "passed": load_passed,
                    "success_rate_percent": round(load_success_rate, 2),
                    "successful_loads": successful_loads,
                    "total_attempts": total_attempts,
                }
            )

            # Test 2: Fallback workflow
            fallback_modes_tested = 0
            successful_fallbacks = 0

            fallback_scenarios = [
                (FallbackMode.STORED_DATA, "test-nonexistent-1"),
                (FallbackMode.REALTIME_DETECTION, "test-nonexistent-2"),
                (FallbackMode.CACHED_SESSION, "test-nonexistent-3"),
            ]

            for mode, test_uuid in fallback_scenarios:
                try:
                    faces, result_mode = (
                        await self.fallback_manager.get_faces_with_fallback(
                            test_uuid, 1, mode
                        )
                    )
                    fallback_modes_tested += 1
                    if result_mode != FallbackMode.NO_DETECTION:
                        successful_fallbacks += 1
                except Exception:
                    fallback_modes_tested += 1

            fallback_success_rate = (
                (successful_fallbacks / fallback_modes_tested * 100)
                if fallback_modes_tested > 0
                else 0
            )
            fallback_passed = fallback_success_rate >= 70

            if not fallback_passed:
                recommendations.append("Improve fallback workflow reliability")

            workflow_tests.append(
                {
                    "test": "fallback_workflow",
                    "passed": fallback_passed,
                    "success_rate_percent": round(fallback_success_rate, 2),
                    "successful_fallbacks": successful_fallbacks,
                    "total_attempts": fallback_modes_tested,
                }
            )

            # Test 3: Error recovery workflow
            error_recovery_passed = True
            try:
                # Test error recovery
                test_error = ValueError("Test validation error")
                recovery_success = await self.error_recovery.handle_error(
                    test_error, "validation_test", {"test": True}
                )

                # Check if error was recorded
                error_stats = self.error_recovery.get_error_statistics()
                errors_recorded = error_stats["error_summary"]["total_errors"] > 0

                if not errors_recorded:
                    recommendations.append("Ensure error events are properly recorded")
                    error_recovery_passed = False

            except Exception as e:
                critical_issues.append(f"Error recovery test failed: {e}")
                error_recovery_passed = False

            workflow_tests.append(
                {
                    "test": "error_recovery_workflow",
                    "passed": error_recovery_passed,
                    "details": "Error recording and recovery mechanism",
                }
            )

        except Exception as e:
            critical_issues.append(f"End-to-end workflow validation failed: {e}")
            workflow_tests.append(
                {"test": "workflow_validation", "passed": False, "error": str(e)}
            )

        # Calculate score
        passed_tests = sum(1 for test in workflow_tests if test.get("passed", False))
        total_tests = len(workflow_tests)
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        validation_time = (time.time() - validation_start) * 1000

        return ValidationResult(
            validation_name="end_to_end_workflow",
            passed=len(critical_issues) == 0 and score >= 75,
            score=score,
            details={
                "workflow_tests": workflow_tests,
                "validation_time_ms": validation_time,
            },
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    async def _validate_error_recovery(self) -> ValidationResult:
        """Validate error recovery system."""
        validation_start = time.time()

        recovery_tests = []
        critical_issues = []
        recommendations = []

        try:
            # Test error recovery statistics
            error_stats = self.error_recovery.get_error_statistics()

            # Check if error recovery is working
            has_error_history = error_stats["error_summary"]["total_errors"] > 0
            if has_error_history:
                success_rate = error_stats["error_summary"][
                    "recovery_success_rate_percent"
                ]
                avg_recovery_time = error_stats["error_summary"]["avg_recovery_time_ms"]

                recovery_rate_passed = success_rate >= 80
                recovery_time_passed = (
                    avg_recovery_time
                    <= self.performance_benchmarks["max_error_recovery_time_ms"]
                )

                if not recovery_rate_passed:
                    critical_issues.append(
                        f"Error recovery success rate {success_rate:.1f}% below 80%"
                    )
                    recommendations.append("Improve error recovery strategies")

                if not recovery_time_passed:
                    recommendations.append("Optimize error recovery time")

                recovery_tests.append(
                    {
                        "test": "error_recovery_effectiveness",
                        "passed": recovery_rate_passed and recovery_time_passed,
                        "success_rate_percent": success_rate,
                        "avg_recovery_time_ms": avg_recovery_time,
                        "benchmark_time_ms": self.performance_benchmarks[
                            "max_error_recovery_time_ms"
                        ],
                    }
                )
            else:
                # No error history - test by generating an error
                test_error = ConnectionError("Validation test error")
                recovery_start = time.time()
                recovery_success = await self.error_recovery.handle_error(
                    test_error, "validation_component", {"test": True}
                )
                recovery_time = (time.time() - recovery_start) * 1000

                recovery_passed = recovery_success and recovery_time <= 1000
                if not recovery_passed:
                    recommendations.append("Improve error recovery performance")

                recovery_tests.append(
                    {
                        "test": "error_recovery_functionality",
                        "passed": recovery_passed,
                        "recovery_successful": recovery_success,
                        "recovery_time_ms": round(recovery_time, 2),
                    }
                )

            # Test circuit breaker functionality
            circuit_status = error_stats.get("circuit_breaker_status", {})
            circuit_breakers_healthy = all(
                status["state"] == "closed" for status in circuit_status.values()
            )

            recovery_tests.append(
                {
                    "test": "circuit_breaker_status",
                    "passed": circuit_breakers_healthy,
                    "circuit_breakers": circuit_status,
                }
            )

        except Exception as e:
            critical_issues.append(f"Error recovery validation failed: {e}")
            recovery_tests.append(
                {"test": "error_recovery_validation", "passed": False, "error": str(e)}
            )

        # Calculate score
        passed_tests = sum(1 for test in recovery_tests if test.get("passed", False))
        total_tests = len(recovery_tests)
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        validation_time = (time.time() - validation_start) * 1000

        return ValidationResult(
            validation_name="error_recovery",
            passed=len(critical_issues) == 0 and score >= 80,
            score=score,
            details={
                "recovery_tests": recovery_tests,
                "validation_time_ms": validation_time,
                "error_statistics": error_stats,
            },
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    async def _validate_system_resources(self) -> ValidationResult:
        """Validate system resource usage."""
        validation_start = time.time()

        resource_checks = []
        critical_issues = []
        recommendations = []

        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_passed = cpu_percent <= 80

            if not cpu_passed:
                recommendations.append("Monitor and optimize CPU usage")

            resource_checks.append(
                {
                    "check": "cpu_usage",
                    "passed": cpu_passed,
                    "cpu_percent": cpu_percent,
                    "threshold": 80,
                }
            )

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_passed = memory_percent <= 85

            if not memory_passed:
                recommendations.append("Monitor and optimize memory usage")

            resource_checks.append(
                {
                    "check": "memory_usage",
                    "passed": memory_passed,
                    "memory_percent": memory_percent,
                    "threshold": 85,
                }
            )

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_passed = disk_percent <= 90

            if not disk_passed:
                recommendations.append("Monitor disk space usage")

            resource_checks.append(
                {
                    "check": "disk_usage",
                    "passed": disk_passed,
                    "disk_percent": disk_percent,
                    "threshold": 90,
                }
            )

        except Exception as e:
            critical_issues.append(f"System resource validation failed: {e}")
            resource_checks.append(
                {"check": "resource_validation", "passed": False, "error": str(e)}
            )

        # Calculate score
        passed_checks = sum(
            1 for check in resource_checks if check.get("passed", False)
        )
        total_checks = len(resource_checks)
        score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        validation_time = (time.time() - validation_start) * 1000

        return ValidationResult(
            validation_name="system_resources",
            passed=len(critical_issues) == 0 and score >= 75,
            score=score,
            details={
                "resource_checks": resource_checks,
                "validation_time_ms": validation_time,
            },
            recommendations=recommendations,
            critical_issues=critical_issues,
        )

    def _generate_production_readiness_assessment(
        self, validation_time_ms: float
    ) -> ProductionReadinessAssessment:
        """Generate final production readiness assessment."""

        # Calculate overall score
        total_score = sum(result.score for result in self.validation_results)
        overall_score = (
            total_score / len(self.validation_results) if self.validation_results else 0
        )

        # Collect all critical issues
        all_critical_issues = []
        for result in self.validation_results:
            all_critical_issues.extend(result.critical_issues)

        # Collect all recommendations
        all_recommendations = []
        for result in self.validation_results:
            all_recommendations.extend(result.recommendations)

        # Check if required validations passed
        required_validations_passed = []
        for required in self.production_criteria["required_validations"]:
            validation_result = next(
                (r for r in self.validation_results if r.validation_name == required),
                None,
            )
            if validation_result:
                required_validations_passed.append(validation_result.passed)

        # Determine deployment readiness
        deployment_ready = (
            overall_score >= self.production_criteria["min_overall_score"]
            and len(all_critical_issues)
            <= self.production_criteria["max_critical_issues"]
            and all(required_validations_passed)
        )

        # Generate summary
        validation_summary = {
            "total_validations": len(self.validation_results),
            "passed_validations": sum(1 for r in self.validation_results if r.passed),
            "validation_time_ms": validation_time_ms,
            "validation_details": {
                result.validation_name: {
                    "passed": result.passed,
                    "score": result.score,
                    "critical_issues_count": len(result.critical_issues),
                }
                for result in self.validation_results
            },
        }

        return ProductionReadinessAssessment(
            overall_score=overall_score,
            deployment_ready=deployment_ready,
            critical_blockers=all_critical_issues,
            recommendations=list(set(all_recommendations)),  # Remove duplicates
            validation_summary=validation_summary,
        )


async def main():
    """Run the complete validation suite."""
    print("✅ Face Detection Workflow 5 - Final Validation Suite")
    print("=====================================================")

    # Create and setup validation suite
    validator = Workflow5ValidationSuite()

    try:
        # Setup validation environment
        await validator.setup()

        # Run complete validation
        assessment = await validator.run_complete_validation()

        # Display results
        print(f"\n🎯 Production Readiness Assessment:")
        print("=" * 45)

        print(f"Overall Score: {assessment.overall_score:.1f}%")
        print(
            f"Deployment Ready: {'✅ YES' if assessment.deployment_ready else '❌ NO'}"
        )

        # Validation summary
        summary = assessment.validation_summary
        print(f"\nValidation Summary:")
        print(f"  Total Validations: {summary['total_validations']}")
        print(f"  Passed Validations: {summary['passed_validations']}")
        print(
            f"  Success Rate: {(summary['passed_validations'] / summary['total_validations'] * 100):.1f}%"
        )
        print(f"  Total Time: {summary['validation_time_ms']:.1f}ms")

        # Individual validation results
        print(f"\n📋 Validation Results:")
        for validation_name, details in summary["validation_details"].items():
            status = "✅" if details["passed"] else "❌"
            score = details["score"]
            issues = details["critical_issues_count"]
            print(
                f"  {status} {validation_name.replace('_', ' ').title()}: {score:.1f}% (Critical Issues: {issues})"
            )

        # Critical blockers
        if assessment.critical_blockers:
            print(f"\n🚨 Critical Blockers:")
            for blocker in assessment.critical_blockers:
                print(f"  • {blocker}")

        # Recommendations
        if assessment.recommendations:
            print(f"\n💡 Recommendations:")
            for rec in assessment.recommendations[:10]:  # Show top 10
                print(f"  • {rec}")

        # Final decision
        if assessment.deployment_ready:
            print(f"\n🎉 VALIDATION PASSED - READY FOR PRODUCTION!")
            print(f"✅ Face Detection Workflow 5 meets all production requirements")
            print(f"🚀 System approved for deployment")
        else:
            print(f"\n⚠️  VALIDATION INCOMPLETE - NOT READY FOR PRODUCTION")
            print(f"🔧 Address critical blockers and recommendations before deployment")
            print(
                f"📈 Current score: {assessment.overall_score:.1f}% (Required: {validator.production_criteria['min_overall_score']}%)"
            )

        # Save detailed results
        results_data = {
            "assessment": {
                "overall_score": assessment.overall_score,
                "deployment_ready": assessment.deployment_ready,
                "critical_blockers": assessment.critical_blockers,
                "recommendations": assessment.recommendations,
            },
            "validation_summary": assessment.validation_summary,
            "detailed_results": [
                {
                    "validation_name": result.validation_name,
                    "passed": result.passed,
                    "score": result.score,
                    "details": result.details,
                    "recommendations": result.recommendations,
                    "critical_issues": result.critical_issues,
                }
                for result in validator.validation_results
            ],
            "timestamp": datetime.now().isoformat(),
        }

        with open("/tmp/workflow5_validation_results.json", "w") as f:
            json.dump(results_data, f, indent=2, default=str)

        print(
            f"\n📄 Detailed validation results saved to: /tmp/workflow5_validation_results.json"
        )

    except Exception as e:
        print(f"❌ Validation suite failed to execute: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
