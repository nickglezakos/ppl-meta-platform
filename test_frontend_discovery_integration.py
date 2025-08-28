#!/usr/bin/env python3
"""
Test script to validate the frontend service discovery integration
"""

import json
import sys

import requests


def test_discovery_service():
    """Test the discovery service directly"""
    try:
        print("🔍 Testing Discovery Service...")
        response = requests.get("http://localhost:8006/api/v1/services", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(
                f"✅ Discovery Service: {data['total_count']} services registered, {data['healthy_count']} healthy"
            )

            # Show registered services
            for service in data["services"]:
                status_icon = "✅" if service["status"] == "healthy" else "❌"
                print(
                    f"  {status_icon} {service['name']} ({service['service_type']}) - {service['host']}:{service['port']}"
                )

            return True
        else:
            print(f"❌ Discovery Service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Discovery Service error: {e}")
        return False


def test_service_endpoint(service_name, expected_port):
    """Test individual service endpoints"""
    try:
        print(f"🔍 Testing {service_name} service...")

        # Test direct endpoint
        if service_name == "node":
            url = f"http://localhost:{expected_port}/api/v1/health"
        else:
            url = f"http://localhost:{expected_port}/health"

        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {service_name} service healthy at port {expected_port}")
            return True
        else:
            print(f"❌ {service_name} service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name} service error: {e}")
        return False


def test_service_discovery_resolution():
    """Test service discovery resolution for each service"""
    try:
        print("🔍 Testing Service Discovery Resolution...")

        # Get services from discovery
        response = requests.get("http://localhost:8006/api/v1/services", timeout=5)
        if response.status_code != 200:
            print("❌ Cannot get services from discovery")
            return False

        services = response.json()["services"]

        # Test service discovery resolution
        service_mappings = {
            "ppl-meta-gateway": "gateway",
            "ppl-meta-media": "media",
            "ppl-meta-orchestrator": "orchestrator",
            "ppl-meta-vision": "vision",
            "ppl-meta-node": "node",
            "ppl-meta-cameras": "cameras",
        }

        discovered_services = {}
        for service in services:
            if service["status"] == "healthy":
                service_key = service_mappings.get(service["name"])
                if service_key:
                    discovered_services[service_key] = (
                        f"http://{service['host']}:{service['port']}"
                    )

        print(f"✅ Discovered {len(discovered_services)} healthy services:")
        for key, url in discovered_services.items():
            print(f"  • {key}: {url}")

        return len(discovered_services) > 0

    except Exception as e:
        print(f"❌ Service discovery resolution error: {e}")
        return False


def test_flutter_config_format():
    """Test that the Flutter configuration is properly formatted"""
    try:
        print("🔍 Testing Flutter Configuration...")

        # Check if env.development.json exists and is valid
        with open(
            "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/assets/config/env.development.json",
            "r",
        ) as f:
            config = json.load(f)

        required_keys = [
            "SERVICE_DISCOVERY_ENABLED",
            "DISCOVERY_SERVICE_URL",
            "API_BASE_URL",
            "CAMERA_SERVICE_URL",
        ]

        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            print(f"❌ Missing configuration keys: {missing_keys}")
            return False

        print("✅ Flutter configuration is valid")
        print(f"  • Service Discovery Enabled: {config['SERVICE_DISCOVERY_ENABLED']}")
        print(f"  • Discovery Service URL: {config['DISCOVERY_SERVICE_URL']}")
        return True

    except Exception as e:
        print(f"❌ Flutter configuration error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 PPL Meta Frontend Service Discovery Integration Test")
    print("=" * 60)

    tests = [
        ("Discovery Service", test_discovery_service),
        ("Gateway Service", lambda: test_service_endpoint("gateway", 8080)),
        ("Media Service", lambda: test_service_endpoint("media", 8000)),
        ("Orchestrator Service", lambda: test_service_endpoint("orchestrator", 8002)),
        ("Vision Service", lambda: test_service_endpoint("vision", 8003)),
        ("Node Service", lambda: test_service_endpoint("node", 8001)),
        ("Cameras Service", lambda: test_service_endpoint("cameras", 8005)),
        ("Service Resolution", test_service_discovery_resolution),
        ("Flutter Config", test_flutter_config_format),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'─' * 20} {test_name} {'─' * 20}")
        result = test_func()
        results.append((test_name, result))

    # Summary
    print(f"\n{'=' * 60}")
    print("📋 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Frontend service discovery integration is working!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
