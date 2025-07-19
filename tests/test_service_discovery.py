#!/usr/bin/env python3
"""
Test script for service discovery implementation.
This script validates the service discovery functionality without requiring running services.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_service_discovery_import():
    """Test that the service discovery module can be imported."""
    try:
        from shared.service_discovery import ServiceDiscoveryClient

        print("✅ Service discovery module imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import service discovery module: {e}")
        return False


async def test_service_discovery_instantiation():
    """Test that the service discovery client can be instantiated."""
    try:
        from shared.service_discovery import ServiceDiscoveryClient

        client = ServiceDiscoveryClient(consul_host="consul", consul_port=8500)
        print("✅ Service discovery client instantiated successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to instantiate service discovery client: {e}")
        return False


async def test_service_configs():
    """Test that service configurations include Consul settings."""
    config_files = [
        "ppl-meta-node/src/microservice_config.py",
        "ppl-meta-media/src/microservice_config.py",
        "ppl-meta-gateway/src/config.py",
    ]

    success = True
    for config_file in config_files:
        file_path = project_root / config_file
        if file_path.exists():
            content = file_path.read_text()
            if "CONSUL" in content or "consul" in content:
                print(f"✅ {config_file} contains Consul configuration")
            else:
                print(f"❌ {config_file} missing Consul configuration")
                success = False
        else:
            print(f"❌ {config_file} not found")
            success = False

    return success


async def test_requirements_files():
    """Test that requirements files include service discovery dependencies."""
    requirements_files = [
        "shared/service_discovery/requirements.txt",
        "ppl-meta-gateway/requirements.txt",
        "ppl-meta-node/requirements.txt",
        "ppl-meta-media/requirements.txt",
        "ppl-meta-orchestrator/requirements.txt",
    ]

    success = True
    for req_file in requirements_files:
        file_path = project_root / req_file
        if file_path.exists():
            content = file_path.read_text()
            if "python-consul" in content or "service_discovery" in content:
                print(f"✅ {req_file} includes service discovery dependencies")
            else:
                print(f"❌ {req_file} missing service discovery dependencies")
                success = False
        else:
            print(f"❌ {req_file} not found")
            success = False

    return success


async def test_service_integrations():
    """Test that services have been updated to use service discovery."""
    service_files = [
        "ppl-meta-gateway/src/main.py",
        "ppl-meta-node/src/main.py",
        "ppl-meta-media/src/main.py",
        "ppl-meta-orchestrator/src/main.py",
    ]

    success = True
    for service_file in service_files:
        file_path = project_root / service_file
        if file_path.exists():
            content = file_path.read_text()
            if "service_discovery" in content or "ServiceDiscoveryClient" in content:
                print(f"✅ {service_file} integrated with service discovery")
            else:
                print(f"❌ {service_file} not integrated with service discovery")
                success = False
        else:
            print(f"❌ {service_file} not found")
            success = False

    return success


async def main():
    """Run all tests and report results."""
    print("🔍 Testing Service Discovery Implementation")
    print("=" * 50)

    tests = [
        ("Import Test", test_service_discovery_import),
        ("Instantiation Test", test_service_discovery_instantiation),
        ("Configuration Test", test_service_configs),
        ("Requirements Test", test_requirements_files),
        ("Integration Test", test_service_integrations),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Service discovery implementation is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
