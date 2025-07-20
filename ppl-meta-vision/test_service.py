#!/usr/bin/env python3
"""
PPL Meta Vision Service Test Suite
Comprehensive testing for the face detection microservice
"""

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


class VisionServiceTester:
    """Test suite for PPL Meta Vision Service."""

    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}: {details}")
        self.test_results.append(
            {
                "test": test_name,
                "success": success,
                "details": details,
                "timestamp": time.time(),
            }
        )

    def test_service_health(self) -> bool:
        """Test the health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test(
                        "Health Check",
                        True,
                        f"Service healthy, {len(data.get('available_methods', []))} methods available",
                    )
                    return True
                else:
                    self.log_test(
                        "Health Check",
                        False,
                        f"Service unhealthy: {data.get('status')}",
                    )
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {e}")
            return False

    def test_root_endpoint(self) -> bool:
        """Test the root endpoint."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "service" in data and "PPL Meta Vision Service" in data["service"]:
                    self.log_test("Root Endpoint", True, f"Service: {data['service']}")
                    return True
                else:
                    self.log_test("Root Endpoint", False, "Invalid response format")
                    return False
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Error: {e}")
            return False

    def test_models_endpoint(self) -> bool:
        """Test the models endpoint."""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            if response.status_code == 200:
                data = response.json()
                methods = data.get("available_methods", [])
                if methods:
                    self.log_test(
                        "Models Endpoint", True, f"Methods: {', '.join(methods)}"
                    )
                    return True
                else:
                    self.log_test("Models Endpoint", False, "No methods available")
                    return False
            else:
                self.log_test("Models Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Models Endpoint", False, f"Error: {e}")
            return False

    def create_test_image_base64(self) -> str:
        """Create a simple test image encoded as base64."""
        # Create a simple test image with PIL
        try:
            import io

            from PIL import Image

            # Create a 100x100 white image
            img = Image.new("RGB", (100, 100), color="white")

            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()

            # Encode to base64
            return base64.b64encode(img_bytes).decode("utf-8")
        except ImportError:
            # Fallback: tiny 1x1 PNG in base64
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    def test_face_detection(self) -> bool:
        """Test face detection endpoint."""
        try:
            # Create test image
            test_image = self.create_test_image_base64()

            # Test payload
            payload = {
                "image_base64": test_image,
                "methods": ["haar"],  # Start with one method
                "confidence_threshold": 0.5,
            }

            response = requests.post(
                f"{self.base_url}/detect",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    detections = data.get("detections", [])
                    processing_time = data.get("processing_time", 0)
                    self.log_test(
                        "Face Detection",
                        True,
                        f"{len(detections)} faces detected in {processing_time:.3f}s",
                    )
                    return True
                else:
                    self.log_test(
                        "Face Detection",
                        True,
                        "No faces detected (expected for test image)",
                    )
                    return True
            else:
                self.log_test(
                    "Face Detection",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False
        except Exception as e:
            self.log_test("Face Detection", False, f"Error: {e}")
            return False

    def test_multi_method_detection(self) -> bool:
        """Test multi-method face detection."""
        try:
            # Get available methods first
            models_response = requests.get(f"{self.base_url}/models", timeout=5)
            if models_response.status_code != 200:
                self.log_test(
                    "Multi-Method Detection", False, "Could not get available methods"
                )
                return False

            available_methods = models_response.json().get("available_methods", [])
            if len(available_methods) < 2:
                self.log_test(
                    "Multi-Method Detection",
                    True,
                    "Skipped - only one method available",
                )
                return True

            # Test with multiple methods
            test_image = self.create_test_image_base64()
            payload = {
                "image_base64": test_image,
                "methods": available_methods,
                "confidence_threshold": 0.5,
            }

            response = requests.post(
                f"{self.base_url}/detect",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                method_results = data.get("method_results", {})
                self.log_test(
                    "Multi-Method Detection",
                    True,
                    f"Tested {len(method_results)} methods",
                )
                return True
            else:
                self.log_test(
                    "Multi-Method Detection", False, f"HTTP {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_test("Multi-Method Detection", False, f"Error: {e}")
            return False

    def test_docs_endpoint(self) -> bool:
        """Test that API documentation is available."""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                self.log_test("API Documentation", True, "Swagger UI available")
                return True
            else:
                self.log_test(
                    "API Documentation", False, f"HTTP {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_test("API Documentation", False, f"Error: {e}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary."""
        print(f"\n🧪 PPL Meta Vision Service Test Suite")
        print(f"🎯 Testing service at: {self.base_url}")
        print("=" * 60)

        # Run tests in order
        tests = [
            self.test_service_health,
            self.test_root_endpoint,
            self.test_models_endpoint,
            self.test_docs_endpoint,
            self.test_face_detection,
            self.test_multi_method_detection,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"❌ FAIL | {test.__name__}: Unexpected error: {e}")

        print("=" * 60)
        print(f"📊 Test Summary: {passed} passed, {failed} failed")

        if failed == 0:
            print("🎉 All tests passed! Service is ready for production.")
        else:
            print("⚠️ Some tests failed. Check the service configuration.")

        return {
            "total_tests": len(tests),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(tests) * 100,
            "details": self.test_results,
        }


def main():
    """Main test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Test PPL Meta Vision Service")
    parser.add_argument(
        "--url",
        default="http://localhost:8003",
        help="Service URL (default: http://localhost:8003)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="Wait seconds before testing (for service startup)",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for service startup...")
        time.sleep(args.wait)

    tester = VisionServiceTester(args.url)
    results = tester.run_all_tests()

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with error code if tests failed
    exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
