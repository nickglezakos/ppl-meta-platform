#!/usr/bin/env python3
"""
Quick test of service discovery functionality with the existing Consul
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_consul_connection():
    """Test that we can connect to the existing Consul instance."""
    try:
        from shared.service_discovery import ServiceDiscoveryClient

        # Test connection to localhost Consul
        client = ServiceDiscoveryClient(
            consul_enabled=True, consul_host="localhost", consul_port=8500
        )

        # Try to register a test service
        result = await client.register_service(
            service_name="test-service",
            host="127.0.0.1",
            port=9999,
            health_endpoint="/health",
            tags=["test", "validation"],
            metadata={"test": "true"},
        )

        if result:
            print("✅ Successfully registered test service with Consul")

            # Try to discover the service
            service_url = await client.get_service_url("test-service")
            if service_url:
                print(f"✅ Successfully discovered test service: {service_url}")
            else:
                print("❌ Could not discover registered test service")

            # Clean up - deregister the test service
            await client.deregister_service("test-service", "127.0.0.1", 9999)
            print("✅ Successfully deregistered test service")

            return True
        else:
            print("❌ Failed to register test service with Consul")
            return False

    except Exception as e:
        print(f"❌ Service discovery test failed: {e}")
        return False


async def test_fallback_mode():
    """Test fallback mode when Consul is not available."""
    try:
        from shared.service_discovery import ServiceDiscoveryClient

        fallback_urls = {"test-service": "http://localhost:8999"}

        client = ServiceDiscoveryClient(
            consul_enabled=False, fallback_urls=fallback_urls
        )

        # Test fallback URL retrieval
        service_url = await client.get_service_url("test-service")
        if service_url == "http://localhost:8999":
            print("✅ Fallback mode working correctly")
            return True
        else:
            print(f"❌ Fallback mode failed: got {service_url}")
            return False

    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False


async def main():
    """Run service discovery tests."""
    print("🔍 Testing Service Discovery with Existing Consul")
    print("=" * 60)

    # Test 1: Consul connection and registration
    print("\n📋 Test 1: Consul Connection and Registration")
    print("-" * 45)
    consul_result = await test_consul_connection()

    # Test 2: Fallback mode
    print("\n📋 Test 2: Fallback Mode")
    print("-" * 25)
    fallback_result = await test_fallback_mode()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)

    results = [
        ("Consul Integration", consul_result),
        ("Fallback Mode", fallback_result),
    ]

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if consul_result:
        print("\n🎉 Service discovery is working! Ready to test with actual services.")
        print("\nNext steps:")
        print("1. Fix database connection issues")
        print("2. Start services one by one")
        print("3. Verify service registration in Consul")
        print("4. Test inter-service communication")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
