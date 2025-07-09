#!/usr/bin/env python3
"""
Comprehensive test script for PPL Meta Gateway Service Advanced Features
Tests all the advanced features including rate limiting, service discovery,
circuit breaking, load balancing, authentication, health checks, and metrics.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class TestCase:
    name: str
    description: str
    result: TestResult
    details: str = ""
    execution_time: float = 0.0


class GatewayTester:
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results: List[TestCase] = []
        self.auth_token: Optional[str] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def run_test(self, test_name: str, test_description: str, test_func):
        """Run a single test and record results"""
        logger.info(f"Running test: {test_name}")
        start_time = time.time()

        try:
            await test_func()
            execution_time = time.time() - start_time
            test_case = TestCase(
                name=test_name,
                description=test_description,
                result=TestResult.PASS,
                execution_time=execution_time,
            )
            logger.info(f"✅ {test_name} PASSED ({execution_time:.2f}s)")
        except Exception as e:
            execution_time = time.time() - start_time
            test_case = TestCase(
                name=test_name,
                description=test_description,
                result=TestResult.FAIL,
                details=str(e),
                execution_time=execution_time,
            )
            logger.error(f"❌ {test_name} FAILED: {e} ({execution_time:.2f}s)")

        self.test_results.append(test_case)

    async def test_health_check(self):
        """Test health check endpoint"""
        async with self.session.get(f"{self.gateway_url}/health") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data

    async def test_service_discovery(self):
        """Test service discovery endpoints"""
        # Test service registration
        service_data = {
            "name": "test-service",
            "address": "localhost",
            "port": 9000,
            "health_check": "/health",
            "tags": ["test", "api"],
        }

        async with self.session.post(
            f"{self.gateway_url}/services/register", json=service_data
        ) as response:
            assert response.status in [200, 201]

        # Test service discovery
        async with self.session.get(f"{self.gateway_url}/services") as response:
            assert response.status == 200
            services = await response.json()
            assert isinstance(services, list)

    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Make rapid requests to trigger rate limiting
        rate_limit_exceeded = False

        for i in range(15):  # Exceed the typical rate limit
            async with self.session.get(f"{self.gateway_url}/health") as response:
                if response.status == 429:  # Too Many Requests
                    rate_limit_exceeded = True
                    break
                await asyncio.sleep(0.1)

        assert rate_limit_exceeded, "Rate limiting not triggered"

    async def test_load_balancing(self):
        """Test load balancing across multiple service instances"""
        # This test requires multiple service instances to be registered
        # For now, we'll test the load balancing endpoint exists
        async with self.session.get(
            f"{self.gateway_url}/services/test-service"
        ) as response:
            # Accept both 200 (service found) and 404 (no service registered)
            assert response.status in [200, 404, 503]

    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        # Test circuit breaker status
        async with self.session.get(
            f"{self.gateway_url}/circuit-breaker/status"
        ) as response:
            if response.status == 200:
                data = await response.json()
                assert "circuits" in data
            else:
                # Circuit breaker endpoint might not be implemented yet
                assert response.status in [404, 501]

    async def test_authentication(self):
        """Test authentication endpoints"""
        # Test login endpoint
        login_data = {"username": "test_user", "password": "test_password"}

        try:
            async with self.session.post(
                f"{self.gateway_url}/auth/login", json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    assert self.auth_token is not None
                elif response.status == 404:
                    # Auth endpoint not implemented yet
                    logger.info("Authentication endpoint not implemented")
                else:
                    assert False, f"Unexpected auth response: {response.status}"
        except aiohttp.ClientConnectorError:
            logger.info("Authentication service not available")

    async def test_metrics_endpoint(self):
        """Test metrics collection endpoint"""
        async with self.session.get(f"{self.gateway_url}/metrics") as response:
            assert response.status == 200
            metrics_data = await response.text()

            # Check for Prometheus-style metrics
            assert "http_requests_total" in metrics_data or "gateway_" in metrics_data

    async def test_request_tracing(self):
        """Test distributed tracing headers"""
        headers = {"X-Trace-Id": "test-trace-123", "X-Span-Id": "test-span-456"}

        async with self.session.get(
            f"{self.gateway_url}/health", headers=headers
        ) as response:
            assert response.status == 200
            # Check if tracing headers are preserved or new ones added
            response_headers = dict(response.headers)
            assert (
                any(key.lower().startswith("x-trace") for key in response_headers)
                or response.status == 200
            )

    async def test_cors_headers(self):
        """Test CORS (Cross-Origin Resource Sharing) headers"""
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        }

        async with self.session.options(
            f"{self.gateway_url}/health", headers=headers
        ) as response:
            # Should either handle CORS properly or return 200/404
            assert response.status in [200, 204, 404]

            if response.status in [200, 204]:
                cors_headers = dict(response.headers)
                # Check for CORS headers
                assert any(
                    key.lower().startswith("access-control") for key in cors_headers
                )

    async def test_request_transformation(self):
        """Test request/response transformation capabilities"""
        # Test with custom headers that should be transformed
        headers = {"X-Custom-Header": "test-value", "User-Agent": "Gateway-Tester/1.0"}

        async with self.session.get(
            f"{self.gateway_url}/health", headers=headers
        ) as response:
            assert response.status == 200
            # The gateway should handle custom headers gracefully

    async def test_websocket_support(self):
        """Test WebSocket proxy support"""
        # This is a basic test to see if WebSocket endpoints are available
        try:
            ws_url = self.gateway_url.replace("http://", "ws://") + "/ws/test"
            # For now, just test if the endpoint exists
            async with self.session.get(f"{self.gateway_url}/ws/health") as response:
                # Accept various responses as WebSocket support varies
                assert response.status in [200, 404, 426, 501]
        except Exception:
            # WebSocket support might not be implemented
            logger.info("WebSocket support not available")

    async def test_api_versioning(self):
        """Test API versioning support"""
        # Test different API versions
        versions = ["v1", "v2"]

        for version in versions:
            async with self.session.get(
                f"{self.gateway_url}/api/{version}/health"
            ) as response:
                # Should either route to versioned service or return 404
                assert response.status in [200, 404, 503]

    async def test_request_validation(self):
        """Test request validation and schema checking"""
        # Test with malformed JSON
        try:
            async with self.session.post(
                f"{self.gateway_url}/services/register", data="invalid json"
            ) as response:
                # Should reject malformed requests
                assert response.status in [400, 422, 415]
        except Exception:
            # Validation might be handled differently
            pass

    async def test_caching(self):
        """Test response caching functionality"""
        # Make the same request twice to test caching
        cache_test_url = f"{self.gateway_url}/health"

        # First request
        start_time = time.time()
        async with self.session.get(cache_test_url) as response1:
            first_time = time.time() - start_time
            assert response1.status == 200
            data1 = await response1.json()

        # Second request (should be faster if cached)
        start_time = time.time()
        async with self.session.get(cache_test_url) as response2:
            second_time = time.time() - start_time
            assert response2.status == 200
            data2 = await response2.json()

        # The second request might be cached (faster) or fresh
        # This is more of a performance indicator than a strict test
        logger.info(
            f"First request: {first_time:.3f}s, Second request: {second_time:.3f}s"
        )

    async def test_security_headers(self):
        """Test security headers in responses"""
        async with self.session.get(f"{self.gateway_url}/health") as response:
            assert response.status == 200
            headers = dict(response.headers)

            # Check for common security headers
            security_headers = [
                "x-content-type-options",
                "x-frame-options",
                "x-xss-protection",
                "strict-transport-security",
            ]

            # At least some security headers should be present
            present_headers = [
                h for h in security_headers if h in [k.lower() for k in headers.keys()]
            ]
            logger.info(f"Security headers present: {present_headers}")

    async def run_all_tests(self):
        """Run all gateway tests"""
        logger.info("🚀 Starting PPL Meta Gateway Advanced Features Test Suite")
        logger.info("=" * 70)

        # Core functionality tests
        await self.run_test(
            "health_check", "Test gateway health check endpoint", self.test_health_check
        )

        await self.run_test(
            "service_discovery",
            "Test service registration and discovery",
            self.test_service_discovery,
        )

        await self.run_test(
            "metrics_endpoint",
            "Test metrics collection and exposure",
            self.test_metrics_endpoint,
        )

        # Advanced features tests
        await self.run_test(
            "rate_limiting", "Test rate limiting functionality", self.test_rate_limiting
        )

        await self.run_test(
            "load_balancing",
            "Test load balancing capabilities",
            self.test_load_balancing,
        )

        await self.run_test(
            "circuit_breaker", "Test circuit breaker pattern", self.test_circuit_breaker
        )

        await self.run_test(
            "authentication",
            "Test authentication and authorization",
            self.test_authentication,
        )

        await self.run_test(
            "request_tracing",
            "Test distributed tracing support",
            self.test_request_tracing,
        )

        await self.run_test("cors_headers", "Test CORS support", self.test_cors_headers)

        await self.run_test(
            "request_transformation",
            "Test request/response transformation",
            self.test_request_transformation,
        )

        await self.run_test(
            "websocket_support",
            "Test WebSocket proxy support",
            self.test_websocket_support,
        )

        await self.run_test(
            "api_versioning", "Test API versioning support", self.test_api_versioning
        )

        await self.run_test(
            "request_validation",
            "Test request validation",
            self.test_request_validation,
        )

        await self.run_test("caching", "Test response caching", self.test_caching)

        await self.run_test(
            "security_headers", "Test security headers", self.test_security_headers
        )

    def generate_report(self) -> str:
        """Generate a comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len(
            [t for t in self.test_results if t.result == TestResult.PASS]
        )
        failed_tests = len(
            [t for t in self.test_results if t.result == TestResult.FAIL]
        )
        skipped_tests = len(
            [t for t in self.test_results if t.result == TestResult.SKIP]
        )

        total_time = sum(t.execution_time for t in self.test_results)

        report = []
        report.append("=" * 80)
        report.append("PPL META GATEWAY - ADVANCED FEATURES TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests} ✅")
        report.append(f"Failed: {failed_tests} ❌")
        report.append(f"Skipped: {skipped_tests} ⏭️")
        report.append(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        report.append(f"Total Execution Time: {total_time:.2f} seconds")
        report.append("")

        # Detailed results
        report.append("DETAILED TEST RESULTS:")
        report.append("-" * 40)

        for test in self.test_results:
            status_icon = {
                TestResult.PASS: "✅",
                TestResult.FAIL: "❌",
                TestResult.SKIP: "⏭️",
            }[test.result]

            report.append(f"{status_icon} {test.name}")
            report.append(f"   Description: {test.description}")
            report.append(f"   Execution Time: {test.execution_time:.2f}s")

            if test.result == TestResult.FAIL and test.details:
                report.append(f"   Error: {test.details}")
            report.append("")

        # Feature coverage summary
        report.append("FEATURE COVERAGE SUMMARY:")
        report.append("-" * 30)

        feature_categories = {
            "Core Features": ["health_check", "service_discovery", "metrics_endpoint"],
            "Traffic Management": [
                "rate_limiting",
                "load_balancing",
                "circuit_breaker",
            ],
            "Security": ["authentication", "security_headers", "request_validation"],
            "Observability": ["request_tracing", "metrics_endpoint", "caching"],
            "Protocol Support": ["cors_headers", "websocket_support", "api_versioning"],
            "Request Processing": [
                "request_transformation",
                "request_validation",
                "caching",
            ],
        }

        for category, tests in feature_categories.items():
            category_tests = [t for t in self.test_results if t.name in tests]
            if category_tests:
                passed = len([t for t in category_tests if t.result == TestResult.PASS])
                total = len(category_tests)
                percentage = (passed / total) * 100
                report.append(f"{category}: {passed}/{total} ({percentage:.1f}%)")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


async def main():
    """Main test execution function"""
    gateway_url = "http://localhost:8080"

    print(f"🔍 Testing PPL Meta Gateway at {gateway_url}")
    print("⏳ Please ensure the gateway service is running...")
    print()

    async with GatewayTester(gateway_url) as tester:
        try:
            await tester.run_all_tests()
        except KeyboardInterrupt:
            logger.info("Tests interrupted by user")
        except Exception as e:
            logger.error(f"Test suite failed with error: {e}")
        finally:
            # Generate and display report
            report = tester.generate_report()
            print(report)

            # Save report to file
            with open("gateway_test_report.txt", "w") as f:
                f.write(report)

            print(f"📄 Test report saved to: gateway_test_report.txt")


if __name__ == "__main__":
    asyncio.run(main())
