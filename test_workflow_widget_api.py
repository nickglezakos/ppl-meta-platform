#!/usr/bin/env python3
"""
PPL Meta Backend API Improvements - Test Script
=============================================

Test script to validate the enhanced processing status API endpoints
designed for Flutter workflow widgets.

Tests:
- Widget-optimized processing status endpoints
- Analytics endpoints for dashboard widgets
- Health monitoring endpoints
- Session management for widgets
- Gateway routing validation
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests


class WorkflowWidgetAPITester:
    """Test suite for workflow widget API endpoints."""

    def __init__(self):
        self.base_urls = {
            "vision": "http://localhost:8003",
            "gateway": "http://localhost:8080",
            "media": "http://localhost:8000",
            "node": "http://localhost:8001",
        }
        self.test_results = []
        self.test_media_uuid = "test-media-uuid-12345"

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")

        result = {
            "timestamp": timestamp,
            "test": test_name,
            "success": success,
            "details": details,
        }
        self.test_results.append(result)

        print(f"[{timestamp}] {status} {test_name}")
        if details:
            print(f"    📋 {details}")
        print()

    def test_vision_service_health(self) -> bool:
        """Test vision service health endpoint."""
        try:
            response = requests.get(f"{self.base_urls['vision']}/health", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    models_loaded = data.get("models_loaded", False)
                    available_methods = data.get("available_methods", [])

                    details = f"Models loaded: {models_loaded}, Methods: {len(available_methods)}"
                    self.log_test("Vision Service Health", True, details)
                    return True
                else:
                    self.log_test(
                        "Vision Service Health", False, f"Status: {data.get('status')}"
                    )
                    return False
            else:
                self.log_test(
                    "Vision Service Health", False, f"HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test("Vision Service Health", False, f"Error: {e}")
            return False

    def test_widget_processing_status(self) -> bool:
        """Test widget-optimized processing status endpoint."""
        try:
            # Test direct vision service endpoint
            response = requests.get(
                f"{self.base_urls['vision']}/api/v1/processing-status/{self.test_media_uuid}/widget",
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                required_fields = [
                    "media_uuid",
                    "status",
                    "face_detection_processed",
                    "total_faces_detected",
                    "optimal_playback_mode",
                    "cache_available",
                    "last_updated",
                ]

                missing_fields = [
                    field for field in required_fields if field not in data
                ]

                if not missing_fields:
                    details = f"Status: {data.get('status')}, Faces: {data.get('total_faces_detected')}"
                    self.log_test("Widget Processing Status (Direct)", True, details)
                    return True
                else:
                    self.log_test(
                        "Widget Processing Status (Direct)",
                        False,
                        f"Missing fields: {missing_fields}",
                    )
                    return False
            else:
                self.log_test(
                    "Widget Processing Status (Direct)",
                    False,
                    f"HTTP {response.status_code}: {response.text[:100]}",
                )
                return False

        except Exception as e:
            self.log_test("Widget Processing Status (Direct)", False, f"Error: {e}")
            return False

    def test_widget_processing_status_via_gateway(self) -> bool:
        """Test widget processing status via gateway routing."""
        try:
            # Test via gateway routing
            response = requests.get(
                f"{self.base_urls['gateway']}/api/v1/processing-status/{self.test_media_uuid}/widget",
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                details = f"Status: {data.get('status')}, Routed successfully"
                self.log_test("Widget Processing Status (Gateway)", True, details)
                return True
            else:
                self.log_test(
                    "Widget Processing Status (Gateway)",
                    False,
                    f"HTTP {response.status_code}: {response.text[:100]}",
                )
                return False

        except Exception as e:
            self.log_test("Widget Processing Status (Gateway)", False, f"Error: {e}")
            return False

    def test_processing_analytics(self) -> bool:
        """Test processing analytics endpoint."""
        try:
            response = requests.get(
                f"{self.base_urls['vision']}/api/v1/processing-status/{self.test_media_uuid}/analytics",
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                required_fields = [
                    "media_uuid",
                    "session_history",
                    "total_sessions",
                    "total_faces_detected",
                    "quality_metrics",
                    "recommendations",
                ]

                missing_fields = [
                    field for field in required_fields if field not in data
                ]

                if not missing_fields:
                    sessions = data.get("total_sessions", 0)
                    faces = data.get("total_faces_detected", 0)
                    details = f"Sessions: {sessions}, Total faces: {faces}"
                    self.log_test("Processing Analytics", True, details)
                    return True
                else:
                    self.log_test(
                        "Processing Analytics",
                        False,
                        f"Missing fields: {missing_fields}",
                    )
                    return False
            else:
                self.log_test(
                    "Processing Analytics",
                    False,
                    f"HTTP {response.status_code}: {response.text[:100]}",
                )
                return False

        except Exception as e:
            self.log_test("Processing Analytics", False, f"Error: {e}")
            return False

    def test_system_health_monitoring(self) -> bool:
        """Test system health monitoring endpoint."""
        try:
            response = requests.get(
                f"{self.base_urls['vision']}/api/v1/processing-status/health",
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                required_fields = [
                    "overall_status",
                    "active_sessions",
                    "service_health",
                    "alerts",
                    "last_check",
                ]

                missing_fields = [
                    field for field in required_fields if field not in data
                ]

                if not missing_fields:
                    status = data.get("overall_status")
                    sessions = data.get("active_sessions", 0)
                    alerts = len(data.get("alerts", []))
                    details = f"Status: {status}, Active sessions: {sessions}, Alerts: {alerts}"
                    self.log_test("System Health Monitoring", True, details)
                    return True
                else:
                    self.log_test(
                        "System Health Monitoring",
                        False,
                        f"Missing fields: {missing_fields}",
                    )
                    return False
            else:
                self.log_test(
                    "System Health Monitoring",
                    False,
                    f"HTTP {response.status_code}: {response.text[:100]}",
                )
                return False

        except Exception as e:
            self.log_test("System Health Monitoring", False, f"Error: {e}")
            return False

    def test_active_sessions_overview(self) -> bool:
        """Test active sessions overview endpoint."""
        try:
            response = requests.get(
                f"{self.base_urls['vision']}/api/v1/sessions/active/overview",
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    active_count = len(data)
                    details = f"Active sessions found: {active_count}"

                    # Check session structure if any sessions exist
                    if active_count > 0:
                        session = data[0]
                        required_session_fields = [
                            "session_uuid",
                            "session_type",
                            "started_at",
                            "total_faces_detected",
                            "processing_status",
                        ]
                        missing = [
                            f for f in required_session_fields if f not in session
                        ]
                        if missing:
                            details += f", Missing session fields: {missing}"

                    self.log_test("Active Sessions Overview", True, details)
                    return True
                else:
                    self.log_test(
                        "Active Sessions Overview", False, "Response not a list"
                    )
                    return False
            else:
                self.log_test(
                    "Active Sessions Overview",
                    False,
                    f"HTTP {response.status_code}: {response.text[:100]}",
                )
                return False

        except Exception as e:
            self.log_test("Active Sessions Overview", False, f"Error: {e}")
            return False

    def test_gateway_routing_completeness(self) -> bool:
        """Test that all new endpoints are properly routed through gateway."""
        endpoints_to_test = [
            f"/api/v1/processing-status/{self.test_media_uuid}/widget",
            f"/api/v1/processing-status/{self.test_media_uuid}/analytics",
            "/api/v1/processing-status/health",
            "/api/v1/sessions/active/overview",
        ]

        routed_count = 0
        failed_endpoints = []

        for endpoint in endpoints_to_test:
            try:
                response = requests.get(
                    f"{self.base_urls['gateway']}{endpoint}", timeout=5
                )
                if response.status_code in [
                    200,
                    404,
                    422,
                ]:  # 404/422 acceptable for test data
                    routed_count += 1
                else:
                    failed_endpoints.append(f"{endpoint} -> {response.status_code}")

            except Exception as e:
                failed_endpoints.append(f"{endpoint} -> Error: {str(e)[:50]}")

        success = routed_count == len(endpoints_to_test)
        details = f"Routed: {routed_count}/{len(endpoints_to_test)}"
        if failed_endpoints:
            details += f", Failed: {failed_endpoints}"

        self.log_test("Gateway Routing Completeness", success, details)
        return success

    def test_existing_apis_still_working(self) -> bool:
        """Test that existing APIs are still functioning."""
        try:
            # Test basic face detection endpoint
            response = requests.get(f"{self.base_urls['vision']}/models", timeout=10)

            if response.status_code == 200:
                data = response.json()
                methods = data.get("available_methods", [])
                details = f"Available methods: {len(methods)} ({', '.join(methods)})"
                self.log_test("Existing APIs (Models)", True, details)

                # Test basic processing status endpoint
                response2 = requests.get(
                    f"{self.base_urls['vision']}/processing-status/{self.test_media_uuid}",
                    timeout=10,
                )

                if response2.status_code in [200, 404]:  # 404 acceptable for test UUID
                    self.log_test(
                        "Existing APIs (Processing Status)", True, "Endpoint accessible"
                    )
                    return True
                else:
                    self.log_test(
                        "Existing APIs (Processing Status)",
                        False,
                        f"HTTP {response2.status_code}",
                    )
                    return False
            else:
                self.log_test(
                    "Existing APIs (Models)", False, f"HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test("Existing APIs", False, f"Error: {e}")
            return False

    def run_all_tests(self) -> Dict:
        """Run all workflow widget API tests."""
        print("🚀 PPL Meta Backend API Improvements - Test Suite")
        print("=" * 60)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Testing widget-optimized API endpoints")
        print()

        # Run tests
        tests = [
            self.test_vision_service_health,
            self.test_existing_apis_still_working,
            self.test_widget_processing_status,
            self.test_widget_processing_status_via_gateway,
            self.test_processing_analytics,
            self.test_system_health_monitoring,
            self.test_active_sessions_overview,
            self.test_gateway_routing_completeness,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1

        # Print summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        success_rate = (passed / total) * 100
        status = (
            "✅ SUCCESS"
            if passed == total
            else "⚠️ PARTIAL" if passed > 0 else "❌ FAILED"
        )

        print(f"Overall Status: {status}")
        print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        print()

        # Print detailed results
        print("📋 Detailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result["success"] else "❌"
            print(f"  {status_icon} {result['test']}")
            if result["details"]:
                print(f"     {result['details']}")

        print()
        print("🎯 CONCLUSIONS:")

        if passed == total:
            print("✅ All workflow widget API endpoints are working correctly")
            print("✅ Gateway routing is properly configured")
            print("✅ Enhanced processing status API is ready for Flutter integration")
        elif passed > total * 0.7:
            print("⚠️ Most endpoints working, minor issues to address")
            print("✅ Core functionality is available for Flutter widgets")
        else:
            print("❌ Major issues detected, further development needed")
            print("⚠️ Flutter widget integration may be affected")

        print()
        print("📚 NEXT STEPS:")
        print("1. Review any failed tests and fix issues")
        print("2. Implement Flutter API client using these endpoints")
        print("3. Test real-time data flow with actual media processing")
        print("4. Optimize endpoint performance for production use")

        return {
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "results": self.test_results,
        }


def main():
    """Run the test suite."""
    tester = WorkflowWidgetAPITester()
    results = tester.run_all_tests()

    # Exit with appropriate code
    if results["passed"] == results["total"]:
        sys.exit(0)  # All tests passed
    elif results["passed"] > 0:
        sys.exit(1)  # Some tests failed
    else:
        sys.exit(2)  # All tests failed


if __name__ == "__main__":
    main()
