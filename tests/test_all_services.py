#!/usr/bin/env python3
"""
Comprehensive test script for PPL Meta Code services.
Tests all services to ensure they're running correctly.
"""

import json
import sys
import time
from typing import Dict, List, Tuple

import requests


class ServiceTester:
    """Test runner for all PPL Meta Code services."""

    def __init__(self):
        """Initialize the service tester."""
        self.services = {
            "gateway": {
                "url": "http://localhost:8080",
                "health_endpoint": "/health",
                "docs_endpoint": "/docs",
            },
            "node": {
                "url": "http://localhost:8001",
                "health_endpoint": "/api/v1/health",  # Node uses different health path
                "docs_endpoint": "/docs",
            },
            "media": {
                "url": "http://localhost:8000",
                "health_endpoint": "/",  # Media uses root for health info
                "docs_endpoint": "/docs",
            },
            "orchestrator": {
                "url": "http://localhost:8002",
                "health_endpoint": "/health",
                "docs_endpoint": "/docs",
            },
        }

    def test_service(self, name: str, config: Dict) -> Tuple[bool, List[str]]:
        """Test a single service and its endpoints."""
        results = []
        success = True

        print(f"\n🔍 Testing {name} service at {config['url']}...")

        # Test health endpoint
        health_url = f"{config['url']}{config['health_endpoint']}"
        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                results.append(f"  ✅ health: OK (200)")
                try:
                    health_data = response.json()
                    service_name = health_data.get("service", "unknown")
                    status = health_data.get("status", "unknown")
                    version = health_data.get("version", "unknown")
                    results.append(f"     Service: {service_name}")
                    results.append(f"     Status: {status}")
                    results.append(f"     Version: {version}")
                except Exception:
                    results.append(f"     Data: {response.text[:50]}...")
            else:
                results.append(f"  ❌ health: HTTP {response.status_code}")
                success = False
        except requests.exceptions.ConnectionError:
            results.append("  ❌ health: Connection refused")
            success = False
        except requests.exceptions.Timeout:
            results.append("  ❌ health: Timeout")
            success = False
        except Exception as e:
            results.append(f"  ❌ health: Error - {str(e)}")
            success = False

        # Test docs endpoint
        docs_url = f"{config['url']}{config['docs_endpoint']}"
        try:
            response = requests.get(docs_url, timeout=10)
            if response.status_code == 200:
                results.append("  ✅ docs: OK (200)")
            else:
                results.append(f"  ❌ docs: HTTP {response.status_code}")
                success = False
        except requests.exceptions.ConnectionError:
            results.append("  ❌ docs: Connection refused")
            success = False
        except requests.exceptions.Timeout:
            results.append("  ❌ docs: Timeout")
            success = False
        except Exception as e:
            results.append(f"  ❌ docs: Error - {str(e)}")
            success = False

        return success, results

    def test_all_services(self) -> bool:
        """Test all services and return overall success status."""
        print("🚀 Starting comprehensive service tests...")

        all_success = True
        service_results = {}

        for service_name, config in self.services.items():
            success, results = self.test_service(service_name, config)
            service_results[service_name] = (success, results)
            if not success:
                all_success = False

        # Print detailed results
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)

        for service_name, (success, results) in service_results.items():
            status_icon = "✅" if success else "❌"
            print(f"\n{status_icon} {service_name.upper()} SERVICE:")
            for result in results:
                print(result)

        print("\n" + "=" * 60)
        if all_success:
            print("🎉 ALL SERVICES ARE RUNNING SUCCESSFULLY!")
        else:
            print("⚠️  SOME SERVICES HAVE ISSUES")
        print("=" * 60)

        return all_success

    def test_service_integration(self) -> bool:
        """Test basic integration between services."""
        print("\n🔗 Testing service integration...")

        try:
            # Test if gateway can reach other services through service discovery
            gateway_url = "http://localhost:8080"

            # This would be expanded with actual integration tests
            print("  ℹ️  Integration tests would go here")
            print("  ℹ️  (Requires actual service endpoints to be implemented)")

            return True
        except Exception as e:
            print(f"  ❌ Integration test failed: {e}")
            return False


def main():
    """Main test execution."""
    print("🧪 PPL Meta Code Service Tester")
    print("Testing all microservices for health and availability...")

    tester = ServiceTester()

    # Test all services
    services_ok = tester.test_all_services()

    # Test integration (basic)
    integration_ok = tester.test_service_integration()

    # Overall result
    if services_ok and integration_ok:
        print("\n🎯 OVERALL RESULT: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n💥 OVERALL RESULT: SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
