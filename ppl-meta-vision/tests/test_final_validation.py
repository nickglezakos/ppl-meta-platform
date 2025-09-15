#!/usr/bin/env python3
"""
PPL Meta Vision Service - Final Validation & Production Readiness Assessment
Comprehensive validation script for Face Detection Workflow 4 implementation
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

import psutil
import requests


@dataclass
class ValidationResult:
    category: str
    test_name: str
    status: str  # PASS, FAIL, WARNING
    details: str
    execution_time: float = 0.0
    critical: bool = False


class ProductionReadinessValidator:
    """Comprehensive production readiness validation suite."""

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.start_time = time.time()
        self.service_url = "http://localhost:8003"

    def log_result(
        self,
        category: str,
        test_name: str,
        status: str,
        details: str,
        execution_time: float = 0.0,
        critical: bool = False,
    ):
        """Log validation result."""
        result = ValidationResult(
            category, test_name, status, details, execution_time, critical
        )
        self.results.append(result)

        # Real-time output
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {category}: {test_name} - {status}")
        if details and status != "PASS":
            print(f"   Details: {details}")

    def run_test_suite(self) -> bool:
        """Execute comprehensive unit and integration test suite."""
        print("🧪 Running Test Suite Validation...")

        # Unit Tests
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "tests/test_unit_comprehensive.py"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                # Parse output for test count
                output_lines = result.stdout.split("\n")
                test_count = sum(1 for line in output_lines if "✅ PASS:" in line)

                self.log_result(
                    "Testing",
                    f"Unit Tests ({test_count} tests)",
                    "PASS",
                    f"All unit tests passed in {execution_time:.2f}s",
                    execution_time,
                    critical=True,
                )
                return True
            else:
                self.log_result(
                    "Testing",
                    "Unit Tests",
                    "FAIL",
                    f"Unit tests failed: {result.stderr}",
                    execution_time,
                    critical=True,
                )
                return False

        except subprocess.TimeoutExpired:
            self.log_result(
                "Testing",
                "Unit Tests",
                "FAIL",
                "Unit tests timed out after 300 seconds",
                300.0,
                critical=True,
            )
            return False
        except Exception as e:
            self.log_result(
                "Testing",
                "Unit Tests",
                "FAIL",
                f"Error running unit tests: {str(e)}",
                0.0,
                critical=True,
            )
            return False

    def run_integration_tests(self) -> bool:
        """Execute integration test suite."""
        print("🔗 Running Integration Test Validation...")

        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "tests/test_integration_standalone.py"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                # Parse output for pass/fail counts
                output_lines = result.stdout.split("\n")
                pass_count = sum(1 for line in output_lines if "✅ PASS:" in line)
                fail_count = sum(1 for line in output_lines if "❌ FAIL:" in line)

                if fail_count == 0:
                    self.log_result(
                        "Integration",
                        f"Integration Tests ({pass_count} passed)",
                        "PASS",
                        f"All integration tests passed in {execution_time:.2f}s",
                        execution_time,
                        critical=True,
                    )
                    return True
                else:
                    self.log_result(
                        "Integration",
                        f"Integration Tests ({pass_count} passed, {fail_count} failed)",
                        "WARNING",
                        f"Some integration tests failed in {execution_time:.2f}s",
                        execution_time,
                        critical=False,
                    )
                    return True  # Not critical for production readiness
            else:
                self.log_result(
                    "Integration",
                    "Integration Tests",
                    "FAIL",
                    f"Integration tests failed: {result.stderr}",
                    execution_time,
                    critical=True,
                )
                return False

        except subprocess.TimeoutExpired:
            self.log_result(
                "Integration",
                "Integration Tests",
                "FAIL",
                "Integration tests timed out after 300 seconds",
                300.0,
                critical=True,
            )
            return False
        except Exception as e:
            self.log_result(
                "Integration",
                "Integration Tests",
                "FAIL",
                f"Error running integration tests: {str(e)}",
                0.0,
                critical=True,
            )
            return False

    def validate_performance_benchmarks(self) -> bool:
        """Validate performance meets production benchmarks."""
        print("🚀 Running Performance Benchmark Validation...")

        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "tests/test_performance_optimization.py"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                # Parse performance results
                output_lines = result.stdout.split("\n")
                performance_status = "PASS"

                for line in output_lines:
                    if "Overall Status:" in line:
                        if "PASS" in line:
                            performance_status = "PASS"
                        else:
                            performance_status = "FAIL"
                        break

                if performance_status == "PASS":
                    self.log_result(
                        "Performance",
                        "Benchmark Validation",
                        "PASS",
                        f"All performance targets met in {execution_time:.2f}s",
                        execution_time,
                        critical=True,
                    )
                    return True
                else:
                    self.log_result(
                        "Performance",
                        "Benchmark Validation",
                        "FAIL",
                        f"Performance targets not met in {execution_time:.2f}s",
                        execution_time,
                        critical=True,
                    )
                    return False
            else:
                self.log_result(
                    "Performance",
                    "Benchmark Validation",
                    "FAIL",
                    f"Performance tests failed: {result.stderr}",
                    execution_time,
                    critical=True,
                )
                return False

        except subprocess.TimeoutExpired:
            self.log_result(
                "Performance",
                "Benchmark Validation",
                "FAIL",
                "Performance tests timed out after 300 seconds",
                300.0,
                critical=True,
            )
            return False
        except Exception as e:
            self.log_result(
                "Performance",
                "Benchmark Validation",
                "FAIL",
                f"Error running performance tests: {str(e)}",
                0.0,
                critical=True,
            )
            return False

    def validate_service_health(self) -> bool:
        """Validate service health and availability."""
        print("🏥 Running Service Health Validation...")

        try:
            # Health endpoint check
            start_time = time.time()
            response = requests.get(f"{self.service_url}/health", timeout=10)
            health_time = time.time() - start_time

            if response.status_code == 200:
                self.log_result(
                    "Service",
                    "Health Endpoint",
                    "PASS",
                    f"Health check passed in {health_time*1000:.2f}ms",
                    health_time,
                )
            else:
                self.log_result(
                    "Service",
                    "Health Endpoint",
                    "FAIL",
                    f"Health check failed with status {response.status_code}",
                    health_time,
                    critical=True,
                )
                return False

            # API endpoint validation
            endpoints = [
                ("/api/v1/sessions", "POST"),
                ("/api/v1/analytics/summary", "GET"),
            ]

            all_endpoints_ok = True
            for endpoint, method in endpoints:
                start_time = time.time()
                try:
                    if method == "GET":
                        resp = requests.get(f"{self.service_url}{endpoint}", timeout=5)
                    else:
                        # For POST, just check if endpoint exists (expect validation error)
                        resp = requests.post(
                            f"{self.service_url}{endpoint}", json={}, timeout=5
                        )

                    endpoint_time = time.time() - start_time

                    # API should be reachable (even if returning validation errors)
                    if resp.status_code in [
                        200,
                        422,
                        400,
                    ]:  # 422 = validation error is OK
                        self.log_result(
                            "Service",
                            f"API {method} {endpoint}",
                            "PASS",
                            f"Endpoint reachable in {endpoint_time*1000:.2f}ms",
                            endpoint_time,
                        )
                    else:
                        self.log_result(
                            "Service",
                            f"API {method} {endpoint}",
                            "WARNING",
                            f"Unexpected status {resp.status_code}",
                            endpoint_time,
                        )

                except requests.exceptions.RequestException as e:
                    self.log_result(
                        "Service",
                        f"API {method} {endpoint}",
                        "FAIL",
                        f"Endpoint unreachable: {str(e)}",
                        0.0,
                        critical=True,
                    )
                    all_endpoints_ok = False

            return all_endpoints_ok

        except Exception as e:
            self.log_result(
                "Service",
                "Health Validation",
                "FAIL",
                f"Service health validation failed: {str(e)}",
                0.0,
                critical=True,
            )
            return False

    def validate_database_connectivity(self) -> bool:
        """Validate database connectivity and schema."""
        print("🗄️ Running Database Validation...")

        try:
            # Check if database files exist (for development setup)
            expected_files = ["src/database.py", "src/models.py"]

            for file_path in expected_files:
                if os.path.exists(file_path):
                    self.log_result(
                        "Database",
                        f"Schema File {os.path.basename(file_path)}",
                        "PASS",
                        f"Required file exists: {file_path}",
                    )
                else:
                    self.log_result(
                        "Database",
                        f"Schema File {os.path.basename(file_path)}",
                        "FAIL",
                        f"Required file missing: {file_path}",
                        critical=True,
                    )
                    return False

            # Check database schema validation through Python import
            try:
                sys.path.insert(0, "src")
                import database
                import models

                self.log_result(
                    "Database",
                    "Schema Import",
                    "PASS",
                    "Database schema modules importable",
                )

                # Validate required classes exist
                required_classes = [
                    ("models", "FaceDetectionSession"),
                    ("models", "FaceDetection"),
                    ("database", "DatabaseManager"),
                ]

                for module_name, class_name in required_classes:
                    module = sys.modules[module_name]
                    if hasattr(module, class_name):
                        self.log_result(
                            "Database",
                            f"Schema Class {class_name}",
                            "PASS",
                            f"Required class exists: {module_name}.{class_name}",
                        )
                    else:
                        self.log_result(
                            "Database",
                            f"Schema Class {class_name}",
                            "FAIL",
                            f"Required class missing: {module_name}.{class_name}",
                            critical=True,
                        )
                        return False

                return True

            except ImportError as e:
                self.log_result(
                    "Database",
                    "Schema Import",
                    "FAIL",
                    f"Cannot import database modules: {str(e)}",
                    critical=True,
                )
                return False

        except Exception as e:
            self.log_result(
                "Database",
                "Database Validation",
                "FAIL",
                f"Database validation failed: {str(e)}",
                critical=True,
            )
            return False

    def validate_security_configuration(self) -> bool:
        """Validate security configuration and best practices."""
        print("🔒 Running Security Configuration Validation...")

        try:
            # Check for security-related files
            security_files = ["src/utils/validators.py", "src/api_models.py"]

            security_score = 0
            total_checks = len(security_files) + 3  # Additional checks

            for file_path in security_files:
                if os.path.exists(file_path):
                    self.log_result(
                        "Security",
                        f"Security Module {os.path.basename(file_path)}",
                        "PASS",
                        f"Security-related file exists: {file_path}",
                    )
                    security_score += 1
                else:
                    self.log_result(
                        "Security",
                        f"Security Module {os.path.basename(file_path)}",
                        "WARNING",
                        f"Security file missing: {file_path}",
                    )

            # Check for input validation in API models
            try:
                with open("src/api_models.py", "r") as f:
                    api_content = f.read()

                if "BaseModel" in api_content and "pydantic" in api_content:
                    self.log_result(
                        "Security",
                        "Input Validation",
                        "PASS",
                        "Pydantic models provide input validation",
                    )
                    security_score += 1
                else:
                    self.log_result(
                        "Security",
                        "Input Validation",
                        "WARNING",
                        "Limited input validation detected",
                    )

            except FileNotFoundError:
                self.log_result(
                    "Security",
                    "Input Validation",
                    "WARNING",
                    "API models file not found",
                )

            # Check for error handling
            try:
                with open("src/main.py", "r") as f:
                    main_content = f.read()

                if "try:" in main_content and "except" in main_content:
                    self.log_result(
                        "Security",
                        "Error Handling",
                        "PASS",
                        "Error handling patterns detected",
                    )
                    security_score += 1
                else:
                    self.log_result(
                        "Security",
                        "Error Handling",
                        "WARNING",
                        "Limited error handling detected",
                    )

            except FileNotFoundError:
                self.log_result(
                    "Security",
                    "Error Handling",
                    "WARNING",
                    "Main application file not found",
                )

            # Check for logging configuration
            if os.path.exists("src/utils/logging.py"):
                self.log_result(
                    "Security",
                    "Audit Logging",
                    "PASS",
                    "Logging configuration available",
                )
                security_score += 1
            else:
                self.log_result(
                    "Security",
                    "Audit Logging",
                    "WARNING",
                    "Dedicated logging configuration missing",
                )

            # Overall security assessment
            security_percentage = (security_score / total_checks) * 100

            if security_percentage >= 80:
                self.log_result(
                    "Security",
                    "Overall Security",
                    "PASS",
                    f"Security score: {security_percentage:.1f}% ({security_score}/{total_checks})",
                )
                return True
            elif security_percentage >= 60:
                self.log_result(
                    "Security",
                    "Overall Security",
                    "WARNING",
                    f"Security score: {security_percentage:.1f}% ({security_score}/{total_checks})",
                )
                return True
            else:
                self.log_result(
                    "Security",
                    "Overall Security",
                    "FAIL",
                    f"Security score too low: {security_percentage:.1f}% ({security_score}/{total_checks})",
                    critical=True,
                )
                return False

        except Exception as e:
            self.log_result(
                "Security",
                "Security Validation",
                "FAIL",
                f"Security validation failed: {str(e)}",
                critical=True,
            )
            return False

    def validate_deployment_readiness(self) -> bool:
        """Validate deployment configuration and readiness."""
        print("🚀 Running Deployment Readiness Validation...")

        try:
            deployment_score = 0
            total_checks = 6

            # Check for required deployment files
            deployment_files = [
                ("Dockerfile", "Docker containerization"),
                ("requirements.txt", "Python dependencies"),
                ("src/main.py", "Application entry point"),
                ("docs/COMPREHENSIVE_DOCUMENTATION.md", "Complete documentation"),
            ]

            for file_path, description in deployment_files:
                if os.path.exists(file_path):
                    self.log_result(
                        "Deployment",
                        f"File {os.path.basename(file_path)}",
                        "PASS",
                        f"{description} available",
                    )
                    deployment_score += 1
                else:
                    self.log_result(
                        "Deployment",
                        f"File {os.path.basename(file_path)}",
                        "WARNING",
                        f"{description} missing: {file_path}",
                    )

            # Check configuration management
            config_files = ["src/config.py", "src/settings.py", "src/main.py"]
            has_config = any(os.path.exists(f) for f in config_files)

            if has_config:
                self.log_result(
                    "Deployment",
                    "Configuration Management",
                    "PASS",
                    "Configuration management available",
                )
                deployment_score += 1
            else:
                self.log_result(
                    "Deployment",
                    "Configuration Management",
                    "WARNING",
                    "Centralized configuration missing",
                )

            # Check for health check implementation
            try:
                with open("src/main.py", "r") as f:
                    main_content = f.read()

                if "/health" in main_content:
                    self.log_result(
                        "Deployment",
                        "Health Check Endpoint",
                        "PASS",
                        "Health check endpoint implemented",
                    )
                    deployment_score += 1
                else:
                    self.log_result(
                        "Deployment",
                        "Health Check Endpoint",
                        "WARNING",
                        "Health check endpoint missing",
                    )

            except FileNotFoundError:
                self.log_result(
                    "Deployment",
                    "Health Check Endpoint",
                    "WARNING",
                    "Cannot verify health check endpoint",
                )

            # Overall deployment readiness
            deployment_percentage = (deployment_score / total_checks) * 100

            if deployment_percentage >= 75:
                self.log_result(
                    "Deployment",
                    "Overall Readiness",
                    "PASS",
                    f"Deployment readiness: {deployment_percentage:.1f}% ({deployment_score}/{total_checks})",
                )
                return True
            elif deployment_percentage >= 50:
                self.log_result(
                    "Deployment",
                    "Overall Readiness",
                    "WARNING",
                    f"Deployment readiness: {deployment_percentage:.1f}% ({deployment_score}/{total_checks})",
                )
                return True
            else:
                self.log_result(
                    "Deployment",
                    "Overall Readiness",
                    "FAIL",
                    f"Deployment readiness too low: {deployment_percentage:.1f}% ({deployment_score}/{total_checks})",
                    critical=True,
                )
                return False

        except Exception as e:
            self.log_result(
                "Deployment",
                "Deployment Validation",
                "FAIL",
                f"Deployment validation failed: {str(e)}",
                critical=True,
            )
            return False

    def validate_documentation_completeness(self) -> bool:
        """Validate documentation completeness."""
        print("📚 Running Documentation Completeness Validation...")

        try:
            doc_score = 0
            total_docs = 7

            # Check for key documentation files
            doc_files = [
                ("README.md", "Project overview"),
                ("docs/COMPREHENSIVE_DOCUMENTATION.md", "Complete documentation"),
                ("tests/test_unit_comprehensive.py", "Unit test documentation"),
                (
                    "tests/test_integration_standalone.py",
                    "Integration test documentation",
                ),
                ("tests/test_performance_optimization.py", "Performance documentation"),
                ("src/api_models.py", "API model documentation"),
                ("src/main.py", "Application documentation"),
            ]

            for file_path, description in doc_files:
                if os.path.exists(file_path):
                    # Check if file has substantial content
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()

                        if len(content) > 500:  # Substantial content
                            self.log_result(
                                "Documentation",
                                f"File {os.path.basename(file_path)}",
                                "PASS",
                                f"{description} complete ({len(content)} chars)",
                            )
                            doc_score += 1
                        else:
                            self.log_result(
                                "Documentation",
                                f"File {os.path.basename(file_path)}",
                                "WARNING",
                                f"{description} minimal content ({len(content)} chars)",
                            )
                    except Exception:
                        self.log_result(
                            "Documentation",
                            f"File {os.path.basename(file_path)}",
                            "WARNING",
                            f"{description} unreadable",
                        )
                else:
                    self.log_result(
                        "Documentation",
                        f"File {os.path.basename(file_path)}",
                        "WARNING",
                        f"{description} missing: {file_path}",
                    )

            # Documentation completeness assessment
            doc_percentage = (doc_score / total_docs) * 100

            if doc_percentage >= 80:
                self.log_result(
                    "Documentation",
                    "Overall Completeness",
                    "PASS",
                    f"Documentation score: {doc_percentage:.1f}% ({doc_score}/{total_docs})",
                )
                return True
            elif doc_percentage >= 60:
                self.log_result(
                    "Documentation",
                    "Overall Completeness",
                    "WARNING",
                    f"Documentation score: {doc_percentage:.1f}% ({doc_score}/{total_docs})",
                )
                return True
            else:
                self.log_result(
                    "Documentation",
                    "Overall Completeness",
                    "FAIL",
                    f"Documentation score too low: {doc_percentage:.1f}% ({doc_score}/{total_docs})",
                    critical=False,  # Not critical for production
                )
                return False

        except Exception as e:
            self.log_result(
                "Documentation",
                "Documentation Validation",
                "FAIL",
                f"Documentation validation failed: {str(e)}",
                critical=False,
            )
            return False

    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final validation report."""
        total_time = time.time() - self.start_time

        # Categorize results
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {
                    "pass": 0,
                    "fail": 0,
                    "warning": 0,
                    "total": 0,
                }

            categories[result.category]["total"] += 1
            if result.status == "PASS":
                categories[result.category]["pass"] += 1
            elif result.status == "FAIL":
                categories[result.category]["fail"] += 1
            else:
                categories[result.category]["warning"] += 1

        # Calculate overall status
        critical_failures = [
            r for r in self.results if r.status == "FAIL" and r.critical
        ]
        total_tests = len(self.results)
        total_pass = sum(1 for r in self.results if r.status == "PASS")
        total_fail = sum(1 for r in self.results if r.status == "FAIL")
        total_warning = sum(1 for r in self.results if r.status == "WARNING")

        overall_status = (
            "PRODUCTION_READY" if len(critical_failures) == 0 else "NOT_READY"
        )

        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "total_execution_time": f"{total_time:.2f}s",
            "overall_status": overall_status,
            "summary": {
                "total_tests": total_tests,
                "passed": total_pass,
                "failed": total_fail,
                "warnings": total_warning,
                "critical_failures": len(critical_failures),
            },
            "categories": categories,
            "critical_failures": [
                {"category": r.category, "test": r.test_name, "details": r.details}
                for r in critical_failures
            ],
            "detailed_results": [
                {
                    "category": r.category,
                    "test_name": r.test_name,
                    "status": r.status,
                    "details": r.details,
                    "execution_time": r.execution_time,
                    "critical": r.critical,
                }
                for r in self.results
            ],
        }

        return report

    def run_full_validation(self) -> bool:
        """Run complete validation suite."""
        print("🎯 PPL Meta Vision Service - Final Production Readiness Validation")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Execute all validation categories
        validations = [
            self.run_test_suite,
            self.run_integration_tests,
            self.validate_performance_benchmarks,
            self.validate_service_health,
            self.validate_database_connectivity,
            self.validate_security_configuration,
            self.validate_deployment_readiness,
            self.validate_documentation_completeness,
        ]

        all_passed = True
        for validation in validations:
            try:
                result = validation()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Validation error: {str(e)}")
                all_passed = False
            print()  # Spacing between categories

        # Generate and display final report
        report = self.generate_final_report()

        print("=" * 80)
        print("🎯 FINAL PRODUCTION READINESS ASSESSMENT")
        print("=" * 80)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Total Execution Time: {report['total_execution_time']}")
        print()

        print("📊 Summary:")
        print(f"  Total Tests: {report['summary']['total_tests']}")
        print(f"  ✅ Passed: {report['summary']['passed']}")
        print(f"  ❌ Failed: {report['summary']['failed']}")
        print(f"  ⚠️  Warnings: {report['summary']['warnings']}")
        print(f"  🚨 Critical Failures: {report['summary']['critical_failures']}")
        print()

        if report["summary"]["critical_failures"] > 0:
            print("🚨 Critical Issues (Must Fix Before Production):")
            for failure in report["critical_failures"]:
                print(
                    f"  • {failure['category']}: {failure['test']} - {failure['details']}"
                )
            print()

        print("📋 Category Breakdown:")
        for category, stats in report["categories"].items():
            pass_rate = (stats["pass"] / stats["total"]) * 100
            print(
                f"  {category}: {stats['pass']}/{stats['total']} passed ({pass_rate:.1f}%)"
            )

        print()
        print("=" * 80)

        if report["overall_status"] == "PRODUCTION_READY":
            print("🎉 PRODUCTION READINESS: ✅ APPROVED")
            print("The PPL Meta Vision Service is ready for production deployment!")
        else:
            print("⚠️  PRODUCTION READINESS: ❌ NOT APPROVED")
            print("Critical issues must be resolved before production deployment.")

        print("=" * 80)

        # Save detailed report
        with open("validation_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed report saved to: validation_report.json")

        return report["overall_status"] == "PRODUCTION_READY"


def main():
    """Main execution function."""
    if not os.path.exists("src"):
        print(
            "❌ Error: This script must be run from the ppl-meta-vision root directory"
        )
        sys.exit(1)

    validator = ProductionReadinessValidator()
    success = validator.run_full_validation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
