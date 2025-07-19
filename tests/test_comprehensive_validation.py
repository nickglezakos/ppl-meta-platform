#!/usr/bin/env python3
"""
Comprehensive Input Validation Testing Suite
Tests ISSUE-016 resolution across all PPL Meta Platform services
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

try:
    from shared.validation import (
        FieldValidators,
        SecurityValidator,
        ValidationErrorDetail,
        ValidationErrorResponse,
        ValidationErrorType,
        validate_password_update_data,
        validate_user_create_data,
    )

    VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import shared validation: {e}")
    VALIDATION_AVAILABLE = False


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestResult:
    test_name: str
    status: TestStatus
    details: str
    service: str = "shared"


class ValidationTestSuite:
    """Comprehensive validation test suite."""

    def __init__(self):
        self.results: List[TestResult] = []

    def add_result(
        self, test_name: str, status: TestStatus, details: str, service: str = "shared"
    ):
        """Add a test result."""
        self.results.append(TestResult(test_name, status, details, service))

    def run_all_tests(self):
        """Run all validation tests."""
        print("🧪 Running Comprehensive Input Validation Tests")
        print("=" * 60)

        # Test shared validation module
        if VALIDATION_AVAILABLE:
            self.test_security_validators()
            self.test_field_validators()
            self.test_user_validation()
            self.test_error_handling()
        else:
            self.add_result(
                "Shared Validation Module",
                TestStatus.SKIP,
                "Shared validation module not available",
            )

        # Test service integrations
        self.test_service_integrations()

        # Display results
        self.display_results()

    def test_security_validators(self):
        """Test security validation functions."""
        print("\n🔒 Testing Security Validators")

        # Test SQL injection detection
        try:
            SecurityValidator.validate_sql_injection("normal text", "test_field")
            self.add_result(
                "SQL Injection - Safe Text",
                TestStatus.PASS,
                "Safe text passed validation",
            )
        except Exception as e:
            self.add_result("SQL Injection - Safe Text", TestStatus.FAIL, str(e))

        # Test SQL injection detection with malicious input
        try:
            SecurityValidator.validate_sql_injection(
                "'; DROP TABLE users; --", "test_field"
            )
            self.add_result(
                "SQL Injection - Malicious Input",
                TestStatus.FAIL,
                "Malicious SQL should have been detected",
            )
        except ValueError:
            self.add_result(
                "SQL Injection - Malicious Input",
                TestStatus.PASS,
                "Malicious SQL correctly detected",
            )
        except Exception as e:
            self.add_result("SQL Injection - Malicious Input", TestStatus.FAIL, str(e))

        # Test XSS detection
        try:
            SecurityValidator.validate_xss(
                "<script>alert('xss')</script>", "test_field"
            )
            self.add_result(
                "XSS - Malicious Script",
                TestStatus.FAIL,
                "Malicious script should have been detected",
            )
        except ValueError:
            self.add_result(
                "XSS - Malicious Script",
                TestStatus.PASS,
                "Malicious script correctly detected",
            )
        except Exception as e:
            self.add_result("XSS - Malicious Script", TestStatus.FAIL, str(e))

        # Test HTML escaping
        try:
            escaped = SecurityValidator.escape_html("<div>test</div>")
            if "&lt;div&gt;test&lt;/div&gt;" in escaped:
                self.add_result(
                    "HTML Escaping", TestStatus.PASS, "HTML correctly escaped"
                )
            else:
                self.add_result(
                    "HTML Escaping",
                    TestStatus.FAIL,
                    f"HTML not properly escaped: {escaped}",
                )
        except Exception as e:
            self.add_result("HTML Escaping", TestStatus.FAIL, str(e))

    def test_field_validators(self):
        """Test field validation functions."""
        print("\n📝 Testing Field Validators")

        # Test username validation
        try:
            valid_username = FieldValidators.validate_username("valid_user123")
            self.add_result(
                "Username - Valid",
                TestStatus.PASS,
                f"Valid username accepted: {valid_username}",
            )
        except Exception as e:
            self.add_result("Username - Valid", TestStatus.FAIL, str(e))

        # Test invalid username
        try:
            FieldValidators.validate_username("invalid user!")
            self.add_result(
                "Username - Invalid",
                TestStatus.FAIL,
                "Invalid username should have been rejected",
            )
        except ValueError:
            self.add_result(
                "Username - Invalid",
                TestStatus.PASS,
                "Invalid username correctly rejected",
            )
        except Exception as e:
            self.add_result("Username - Invalid", TestStatus.FAIL, str(e))

        # Test email validation
        try:
            valid_email = FieldValidators.validate_email("user@example.com")
            self.add_result(
                "Email - Valid", TestStatus.PASS, f"Valid email accepted: {valid_email}"
            )
        except Exception as e:
            self.add_result("Email - Valid", TestStatus.FAIL, str(e))

        # Test password validation
        try:
            valid_password = FieldValidators.validate_password("StrongPass123!")
            self.add_result(
                "Password - Strong", TestStatus.PASS, "Strong password accepted"
            )
        except Exception as e:
            self.add_result("Password - Strong", TestStatus.FAIL, str(e))

        # Test weak password
        try:
            FieldValidators.validate_password("weak")
            self.add_result(
                "Password - Weak",
                TestStatus.FAIL,
                "Weak password should have been rejected",
            )
        except ValueError:
            self.add_result(
                "Password - Weak", TestStatus.PASS, "Weak password correctly rejected"
            )
        except Exception as e:
            self.add_result("Password - Weak", TestStatus.FAIL, str(e))

    def test_user_validation(self):
        """Test user-specific validation functions."""
        print("\n👤 Testing User Validation")

        # Test valid user creation data
        try:
            valid_user_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "StrongPass123!",
                "first_name": "Test",
                "last_name": "User",
            }
            validated = validate_user_create_data(valid_user_data)
            self.add_result(
                "User Creation - Valid Data",
                TestStatus.PASS,
                f"Valid user data processed: {len(validated)} fields",
            )
        except Exception as e:
            self.add_result("User Creation - Valid Data", TestStatus.FAIL, str(e))

        # Test invalid user creation data
        try:
            invalid_user_data = {
                "username": "'; DROP TABLE users; --",
                "email": "invalid-email",
                "password": "weak",
                "first_name": "<script>alert('xss')</script>",
                "last_name": "",
            }
            validate_user_create_data(invalid_user_data)
            self.add_result(
                "User Creation - Invalid Data",
                TestStatus.FAIL,
                "Invalid user data should have been rejected",
            )
        except ValueError:
            self.add_result(
                "User Creation - Invalid Data",
                TestStatus.PASS,
                "Invalid user data correctly rejected",
            )
        except Exception as e:
            self.add_result("User Creation - Invalid Data", TestStatus.FAIL, str(e))

        # Test password update validation
        try:
            valid_password_data = {
                "current_password": "OldPass123!",
                "new_password": "NewPass456!",
                "confirm_password": "NewPass456!",
            }
            validated = validate_password_update_data(valid_password_data)
            self.add_result(
                "Password Update - Valid",
                TestStatus.PASS,
                "Valid password update data processed",
            )
        except Exception as e:
            self.add_result("Password Update - Valid", TestStatus.FAIL, str(e))

    def test_error_handling(self):
        """Test error handling and response structures."""
        print("\n🚨 Testing Error Handling")

        # Test validation error response structure
        try:
            error_detail = ValidationErrorDetail(
                field="test_field",
                error_type=ValidationErrorType.SECURITY_VIOLATION,
                message="Test security violation",
                value="malicious_value",
            )
            error_response = ValidationErrorResponse([error_detail])
            error_dict = error_response.dict()

            required_fields = ["error", "message", "details", "timestamp"]
            missing_fields = [
                field for field in required_fields if field not in error_dict
            ]

            if not missing_fields:
                self.add_result(
                    "Error Response Structure",
                    TestStatus.PASS,
                    "Error response has all required fields",
                )
            else:
                self.add_result(
                    "Error Response Structure",
                    TestStatus.FAIL,
                    f"Missing fields: {missing_fields}",
                )
        except Exception as e:
            self.add_result("Error Response Structure", TestStatus.FAIL, str(e))

    def test_service_integrations(self):
        """Test service integrations by importing validation from each service."""
        print("\n🔗 Testing Service Integrations")

        services = [
            ("ppl-meta-node", "ppl-meta-node/src/api/v1/users.py"),
            ("ppl-meta-media", "ppl-meta-media/src/api/v1/user.py"),
            ("ppl-meta-gateway", "ppl-meta-gateway/src/api/v1/router.py"),
            ("ppl-meta-orchestrator", "ppl-meta-orchestrator/src/main.py"),
        ]

        for service_name, service_file in services:
            try:
                # Check if service file exists and contains validation imports
                if os.path.exists(service_file):
                    with open(service_file, "r") as f:
                        content = f.read()

                    # Check for validation imports
                    if "shared.validation" in content:
                        self.add_result(
                            f"{service_name} - Validation Import",
                            TestStatus.PASS,
                            "Service imports shared validation",
                            service_name,
                        )
                    else:
                        self.add_result(
                            f"{service_name} - Validation Import",
                            TestStatus.FAIL,
                            "Service does not import shared validation",
                            service_name,
                        )

                    # Check for security validation calls
                    if "SecurityValidator" in content:
                        self.add_result(
                            f"{service_name} - Security Validation",
                            TestStatus.PASS,
                            "Service uses security validation",
                            service_name,
                        )
                    else:
                        self.add_result(
                            f"{service_name} - Security Validation",
                            TestStatus.FAIL,
                            "Service does not use security validation",
                            service_name,
                        )
                else:
                    self.add_result(
                        f"{service_name} - File Exists",
                        TestStatus.FAIL,
                        f"Service file not found: {service_file}",
                        service_name,
                    )
            except Exception as e:
                self.add_result(
                    f"{service_name} - Integration Test",
                    TestStatus.FAIL,
                    str(e),
                    service_name,
                )

    def display_results(self):
        """Display test results summary."""
        print("\n" + "=" * 60)
        print("🧪 INPUT VALIDATION TEST RESULTS")
        print("=" * 60)

        # Count results by status
        pass_count = sum(1 for r in self.results if r.status == TestStatus.PASS)
        fail_count = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        skip_count = sum(1 for r in self.results if r.status == TestStatus.SKIP)

        # Display summary
        print(f"✅ PASSED: {pass_count}")
        print(f"❌ FAILED: {fail_count}")
        print(f"⏭️  SKIPPED: {skip_count}")
        print(f"📊 TOTAL: {len(self.results)}")

        # Group results by service
        services = {}
        for result in self.results:
            if result.service not in services:
                services[result.service] = []
            services[result.service].append(result)

        # Display detailed results
        for service_name, service_results in services.items():
            print(f"\n📋 {service_name.upper()} SERVICE:")
            for result in service_results:
                status_icon = (
                    "✅"
                    if result.status == TestStatus.PASS
                    else "❌" if result.status == TestStatus.FAIL else "⏭️"
                )
                print(f"  {status_icon} {result.test_name}: {result.details}")

        # Overall assessment
        print(f"\n{'='*60}")
        if fail_count == 0:
            print("🎉 ALL TESTS PASSED - Input validation successfully implemented!")
        elif fail_count <= 3:
            print("⚠️  MOSTLY SUCCESSFUL - Some minor issues to address")
        else:
            print("🚨 SIGNIFICANT ISSUES - Input validation needs attention")

        print(f"{'='*60}")

        # Generate summary for ISSUE-016 resolution
        return {
            "total_tests": len(self.results),
            "passed": pass_count,
            "failed": fail_count,
            "skipped": skip_count,
            "success_rate": f"{(pass_count / len(self.results)) * 100:.1f}%",
        }


def main():
    """Run the comprehensive validation test suite."""
    suite = ValidationTestSuite()
    summary = suite.run_all_tests()

    # Save results to file
    with open("validation_test_results.json", "w") as f:
        json.dump(
            {
                "summary": summary,
                "detailed_results": [
                    {
                        "test_name": r.test_name,
                        "status": r.status.value,
                        "details": r.details,
                        "service": r.service,
                    }
                    for r in suite.results
                ],
            },
            f,
            indent=2,
        )

    print(f"\n📁 Detailed results saved to: validation_test_results.json")

    # Return exit code based on test results
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    exit(main())
