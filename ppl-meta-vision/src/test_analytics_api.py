#!/usr/bin/env python3
"""
PPL Meta Vision Service - Analytics API Testing Suite

This comprehensive testing suite validates all Phase 5 Advanced Analytics & Traceability Features
including cross-session analytics, device traceability, media timeline analysis, advanced querying,
and performance monitoring capabilities.

Test Coverage:
1. Cross-Session Analytics API (/analytics/cross-session)
2. Device Traceability API (/analytics/device/{uuid})
3. Media Timeline Analytics API (/analytics/media/{uuid}/timeline)
4. Advanced Querying System (/analytics/query)
5. Performance Monitoring System (/analytics/performance)
6. Analytics Dashboard Summary (/analytics/summary)

Dependencies:
- Vision service running on localhost:8003
- Test database with sample data
- Analytics service properly initialized
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest
import requests


class AnalyticsAPITestSuite:
    """Comprehensive test suite for analytics API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.test_data = {}

    def setup_test_data(self):
        """Setup test data for analytics testing."""
        print("🔧 Setting up test data for analytics testing...")

        # Generate test UUIDs
        self.test_data = {
            "media_uuid_1": str(uuid.uuid4()),
            "media_uuid_2": str(uuid.uuid4()),
            "camera_device_uuid_1": str(uuid.uuid4()),
            "camera_device_uuid_2": str(uuid.uuid4()),
            "session_uuid_1": str(uuid.uuid4()),
            "session_uuid_2": str(uuid.uuid4()),
            "session_uuid_3": str(uuid.uuid4()),
        }

        print(f"✅ Test data prepared with {len(self.test_data)} test UUIDs")
        return self.test_data

    def test_service_health(self) -> bool:
        """Test if Vision service is running and healthy."""
        print("🏥 Testing Vision service health...")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Vision service is healthy: {health_data.get('status')}")
                print(
                    f"📊 Available methods: {health_data.get('available_methods', [])}"
                )
                return True
            else:
                print(f"❌ Vision service health check failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Failed to connect to Vision service: {e}")
            return False

    def test_cross_session_analytics(self) -> Dict:
        """Test cross-session analytics endpoint."""
        print("\n📊 Testing Cross-Session Analytics API...")

        test_results = {"endpoint": "/analytics/cross-session", "tests": []}

        # Test 1: Basic cross-session analytics
        try:
            response = requests.get(f"{self.base_url}/analytics/cross-session")
            test_results["tests"].append(
                {
                    "name": "Basic cross-session analytics",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response_keys": (
                        list(response.json().keys())
                        if response.status_code == 200
                        else None
                    ),
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Basic analytics retrieved: {data.get('success')}")
                print(f"📈 Analytics keys: {list(data.get('analytics', {}).keys())}")
            else:
                print(f"❌ Basic analytics failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Basic cross-session analytics",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in basic analytics test: {e}")

        # Test 2: Date filtered analytics
        try:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

            params = {"start_date": start_date, "end_date": end_date}

            response = requests.get(
                f"{self.base_url}/analytics/cross-session", params=params
            )
            test_results["tests"].append(
                {
                    "name": "Date filtered cross-session analytics",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(
                    f"✅ Date filtered analytics retrieved for {start_date} to {end_date}"
                )
            else:
                print(f"❌ Date filtered analytics failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Date filtered cross-session analytics",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in date filtered analytics test: {e}")

        # Test 3: Camera device filtered analytics
        try:
            params = {"camera_device_uuid": self.test_data["camera_device_uuid_1"]}

            response = requests.get(
                f"{self.base_url}/analytics/cross-session", params=params
            )
            test_results["tests"].append(
                {
                    "name": "Camera device filtered analytics",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Camera filtered analytics retrieved")
            else:
                print(f"❌ Camera filtered analytics failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Camera device filtered analytics",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in camera filtered analytics test: {e}")

        return test_results

    def test_device_traceability_analytics(self) -> Dict:
        """Test device traceability analytics endpoint."""
        print("\n🎥 Testing Device Traceability Analytics API...")

        test_results = {
            "endpoint": "/analytics/device/{camera_device_uuid}",
            "tests": [],
        }

        camera_uuid = self.test_data["camera_device_uuid_1"]

        # Test 1: Basic device analytics
        try:
            response = requests.get(f"{self.base_url}/analytics/device/{camera_uuid}")
            test_results["tests"].append(
                {
                    "name": "Basic device traceability",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "camera_uuid": camera_uuid,
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Device analytics retrieved: {data.get('success')}")
                print(f"📊 Analytics keys: {list(data.get('analytics', {}).keys())}")
            else:
                print(f"❌ Device analytics failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Basic device traceability", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in device analytics test: {e}")

        # Test 2: Device analytics with custom parameters
        try:
            params = {"days": 14, "include_sessions": True}

            response = requests.get(
                f"{self.base_url}/analytics/device/{camera_uuid}", params=params
            )
            test_results["tests"].append(
                {
                    "name": "Device analytics with parameters",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Parameterized device analytics retrieved")
            else:
                print(
                    f"❌ Parameterized device analytics failed: {response.status_code}"
                )

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Device analytics with parameters",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in parameterized device analytics test: {e}")

        # Test 3: Invalid device UUID
        try:
            invalid_uuid = "invalid-uuid-format"
            response = requests.get(f"{self.base_url}/analytics/device/{invalid_uuid}")
            test_results["tests"].append(
                {
                    "name": "Invalid device UUID handling",
                    "status_code": response.status_code,
                    "success": response.status_code
                    == 400,  # Should return 400 for invalid UUID
                    "invalid_uuid": invalid_uuid,
                }
            )

            if response.status_code == 400:
                print(f"✅ Invalid UUID properly rejected: {response.status_code}")
            else:
                print(f"❌ Invalid UUID handling failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Invalid device UUID handling",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in invalid UUID test: {e}")

        return test_results

    def test_media_timeline_analytics(self) -> Dict:
        """Test media timeline analytics endpoint."""
        print("\n🎬 Testing Media Timeline Analytics API...")

        test_results = {
            "endpoint": "/analytics/media/{media_uuid}/timeline",
            "tests": [],
        }

        media_uuid = self.test_data["media_uuid_1"]

        # Test 1: Basic media timeline
        try:
            response = requests.get(
                f"{self.base_url}/analytics/media/{media_uuid}/timeline"
            )
            test_results["tests"].append(
                {
                    "name": "Basic media timeline",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "media_uuid": media_uuid,
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Media timeline retrieved: {data.get('success')}")
                print(f"📊 Analytics keys: {list(data.get('analytics', {}).keys())}")
            else:
                print(f"❌ Media timeline failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Basic media timeline", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in media timeline test: {e}")

        # Test 2: Media timeline with session details
        try:
            params = {"include_sessions": True, "include_frames": True}

            response = requests.get(
                f"{self.base_url}/analytics/media/{media_uuid}/timeline", params=params
            )
            test_results["tests"].append(
                {
                    "name": "Media timeline with details",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Detailed media timeline retrieved")
            else:
                print(f"❌ Detailed media timeline failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Media timeline with details",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in detailed media timeline test: {e}")

        # Test 3: Invalid media UUID
        try:
            invalid_uuid = "invalid-media-uuid"
            response = requests.get(
                f"{self.base_url}/analytics/media/{invalid_uuid}/timeline"
            )
            test_results["tests"].append(
                {
                    "name": "Invalid media UUID handling",
                    "status_code": response.status_code,
                    "success": response.status_code
                    == 400,  # Should return 400 for invalid UUID
                    "invalid_uuid": invalid_uuid,
                }
            )

            if response.status_code == 400:
                print(
                    f"✅ Invalid media UUID properly rejected: {response.status_code}"
                )
            else:
                print(f"❌ Invalid media UUID handling failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Invalid media UUID handling",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in invalid media UUID test: {e}")

        return test_results

    def test_advanced_querying_system(self) -> Dict:
        """Test advanced querying system endpoint."""
        print("\n🔍 Testing Advanced Querying System API...")

        test_results = {"endpoint": "/analytics/query", "tests": []}

        # Test 1: Sessions query
        try:
            params = {"query_type": "sessions", "limit": 10}

            response = requests.get(f"{self.base_url}/analytics/query", params=params)
            test_results["tests"].append(
                {
                    "name": "Sessions query",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Sessions query retrieved: {data.get('success')}")
                print(f"📊 Result keys: {list(data.get('result', {}).keys())}")
            else:
                print(f"❌ Sessions query failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Sessions query", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in sessions query test: {e}")

        # Test 2: Devices query
        try:
            params = {"query_type": "devices", "limit": 5}

            response = requests.get(f"{self.base_url}/analytics/query", params=params)
            test_results["tests"].append(
                {
                    "name": "Devices query",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Devices query retrieved")
            else:
                print(f"❌ Devices query failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Devices query", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in devices query test: {e}")

        # Test 3: Media query
        try:
            params = {"query_type": "media", "limit": 5}

            response = requests.get(f"{self.base_url}/analytics/query", params=params)
            test_results["tests"].append(
                {
                    "name": "Media query",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Media query retrieved")
            else:
                print(f"❌ Media query failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Media query", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in media query test: {e}")

        # Test 4: Performance query
        try:
            params = {"query_type": "performance", "limit": 10}

            response = requests.get(f"{self.base_url}/analytics/query", params=params)
            test_results["tests"].append(
                {
                    "name": "Performance query",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Performance query retrieved")
            else:
                print(f"❌ Performance query failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Performance query", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in performance query test: {e}")

        # Test 5: Invalid query type
        try:
            params = {"query_type": "invalid_type", "limit": 10}

            response = requests.get(f"{self.base_url}/analytics/query", params=params)
            test_results["tests"].append(
                {
                    "name": "Invalid query type handling",
                    "status_code": response.status_code,
                    "success": response.status_code
                    == 400,  # Should return 400 for invalid query type
                    "params": params,
                }
            )

            if response.status_code == 400:
                print(
                    f"✅ Invalid query type properly rejected: {response.status_code}"
                )
            else:
                print(f"❌ Invalid query type handling failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Invalid query type handling",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in invalid query type test: {e}")

        # Test 6: Complex filtered query
        try:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

            params = {
                "query_type": "sessions",
                "start_date": start_date,
                "end_date": end_date,
                "session_type": "batch",
                "limit": 20,
                "offset": 0,
            }

            response = requests.get(f"{self.base_url}/analytics/query", params=params)
            test_results["tests"].append(
                {
                    "name": "Complex filtered query",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Complex filtered query retrieved")
            else:
                print(f"❌ Complex filtered query failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Complex filtered query", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in complex filtered query test: {e}")

        return test_results

    def test_performance_monitoring_system(self) -> Dict:
        """Test performance monitoring system endpoint."""
        print("\n⚡ Testing Performance Monitoring System API...")

        test_results = {"endpoint": "/analytics/performance", "tests": []}

        # Test 1: Basic performance analytics
        try:
            response = requests.get(f"{self.base_url}/analytics/performance")
            test_results["tests"].append(
                {
                    "name": "Basic performance analytics",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Performance analytics retrieved: {data.get('success')}")
                print(f"📊 Analytics keys: {list(data.get('analytics', {}).keys())}")
            else:
                print(f"❌ Performance analytics failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Basic performance analytics",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in performance analytics test: {e}")

        # Test 2: Performance analytics with specific metric
        try:
            params = {
                "metric_type": "processing_time",
                "days": 14,
                "granularity": "day",
            }

            response = requests.get(
                f"{self.base_url}/analytics/performance", params=params
            )
            test_results["tests"].append(
                {
                    "name": "Specific metric performance analytics",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Specific metric performance analytics retrieved")
            else:
                print(
                    f"❌ Specific metric performance analytics failed: {response.status_code}"
                )

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Specific metric performance analytics",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in specific metric performance test: {e}")

        # Test 3: Performance analytics with hourly granularity
        try:
            params = {"days": 1, "granularity": "hour"}

            response = requests.get(
                f"{self.base_url}/analytics/performance", params=params
            )
            test_results["tests"].append(
                {
                    "name": "Hourly granularity performance analytics",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Hourly granularity performance analytics retrieved")
            else:
                print(
                    f"❌ Hourly granularity performance analytics failed: {response.status_code}"
                )

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Hourly granularity performance analytics",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in hourly granularity performance test: {e}")

        return test_results

    def test_analytics_dashboard_summary(self) -> Dict:
        """Test analytics dashboard summary endpoint."""
        print("\n📈 Testing Analytics Dashboard Summary API...")

        test_results = {"endpoint": "/analytics/summary", "tests": []}

        # Test 1: Basic dashboard summary
        try:
            response = requests.get(f"{self.base_url}/analytics/summary")
            test_results["tests"].append(
                {
                    "name": "Basic dashboard summary",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Dashboard summary retrieved: {data.get('success')}")
                print(f"📊 Summary keys: {list(data.get('summary', {}).keys())}")
            else:
                print(f"❌ Dashboard summary failed: {response.status_code}")

        except Exception as e:
            test_results["tests"].append(
                {"name": "Basic dashboard summary", "success": False, "error": str(e)}
            )
            print(f"❌ Exception in dashboard summary test: {e}")

        # Test 2: Dashboard summary with custom days
        try:
            params = {"days": 30}

            response = requests.get(f"{self.base_url}/analytics/summary", params=params)
            test_results["tests"].append(
                {
                    "name": "Custom period dashboard summary",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": params,
                }
            )

            if response.status_code == 200:
                print(f"✅ Custom period dashboard summary retrieved")
            else:
                print(
                    f"❌ Custom period dashboard summary failed: {response.status_code}"
                )

        except Exception as e:
            test_results["tests"].append(
                {
                    "name": "Custom period dashboard summary",
                    "success": False,
                    "error": str(e),
                }
            )
            print(f"❌ Exception in custom period dashboard summary test: {e}")

        return test_results

    def run_comprehensive_test_suite(self) -> Dict:
        """Run the complete analytics testing suite."""
        print("🚀 Starting Comprehensive Analytics API Testing Suite")
        print("=" * 60)

        # Setup test data
        self.setup_test_data()

        # Check service health first
        if not self.test_service_health():
            return {
                "success": False,
                "error": "Vision service is not available",
                "timestamp": datetime.now().isoformat(),
            }

        # Run all test suites
        all_results = {
            "test_suite": "PPL Meta Vision Analytics API Testing Suite",
            "timestamp": datetime.now().isoformat(),
            "service_url": self.base_url,
            "test_data": self.test_data,
            "results": {},
        }

        # Execute each test suite
        test_suites = [
            ("cross_session_analytics", self.test_cross_session_analytics),
            ("device_traceability_analytics", self.test_device_traceability_analytics),
            ("media_timeline_analytics", self.test_media_timeline_analytics),
            ("advanced_querying_system", self.test_advanced_querying_system),
            ("performance_monitoring_system", self.test_performance_monitoring_system),
            ("analytics_dashboard_summary", self.test_analytics_dashboard_summary),
        ]

        for suite_name, suite_function in test_suites:
            try:
                print(f"\n{'='*20} {suite_name.replace('_', ' ').title()} {'='*20}")
                suite_results = suite_function()
                all_results["results"][suite_name] = suite_results

                # Calculate success rate for this suite
                successful_tests = sum(
                    1 for test in suite_results["tests"] if test.get("success", False)
                )
                total_tests = len(suite_results["tests"])
                success_rate = (
                    (successful_tests / total_tests * 100) if total_tests > 0 else 0
                )

                print(
                    f"📊 {suite_name} Results: {successful_tests}/{total_tests} tests passed ({success_rate:.1f}%)"
                )

            except Exception as e:
                print(f"❌ Error in {suite_name}: {e}")
                all_results["results"][suite_name] = {"error": str(e), "tests": []}

        # Calculate overall results
        total_tests = 0
        successful_tests = 0

        for suite_results in all_results["results"].values():
            if "tests" in suite_results:
                suite_total = len(suite_results["tests"])
                suite_successful = sum(
                    1 for test in suite_results["tests"] if test.get("success", False)
                )
                total_tests += suite_total
                successful_tests += suite_successful

        overall_success_rate = (
            (successful_tests / total_tests * 100) if total_tests > 0 else 0
        )

        all_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": round(overall_success_rate, 2),
            "overall_success": overall_success_rate >= 80.0,  # 80% success threshold
        }

        print(f"\n{'='*60}")
        print(
            f"🏆 FINAL RESULTS: {successful_tests}/{total_tests} tests passed ({overall_success_rate:.1f}%)"
        )

        if all_results["summary"]["overall_success"]:
            print("✅ Analytics API Testing Suite PASSED!")
        else:
            print("❌ Analytics API Testing Suite FAILED!")

        return all_results

    def save_test_results(self, results: Dict, filename: str = None):
        """Save test results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analytics_api_test_results_{timestamp}.json"

        try:
            with open(filename, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"📄 Test results saved to: {filename}")
        except Exception as e:
            print(f"❌ Failed to save test results: {e}")


def main():
    """Main function to run analytics API testing."""
    print("🧪 PPL Meta Vision Analytics API Testing Suite")
    print("Phase 5: Advanced Analytics & Traceability Features")
    print("=" * 60)

    # Initialize test suite
    test_suite = AnalyticsAPITestSuite()

    # Run comprehensive tests
    results = test_suite.run_comprehensive_test_suite()

    # Save results
    test_suite.save_test_results(results)

    # Print final summary
    print(f"\n📊 Test Summary:")
    print(f"   Total Tests: {results['summary']['total_tests']}")
    print(f"   Successful: {results['summary']['successful_tests']}")
    print(f"   Failed: {results['summary']['failed_tests']}")
    print(f"   Success Rate: {results['summary']['success_rate']}%")

    # Exit with appropriate code
    exit_code = 0 if results["summary"]["overall_success"] else 1
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
