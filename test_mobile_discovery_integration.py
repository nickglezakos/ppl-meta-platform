#!/usr/bin/env python3

import json

import requests


def test_complete_discovery_flow():
    """Test the complete Discovery Service flow that mobile app uses"""

    print("🧪 Testing Complete PPL Meta Discovery Integration")
    print("=" * 60)

    # Current machine IP (same as what mobile app should discover)
    machine_ip = "192.168.1.68"

    print(f"📱 Testing from mobile perspective (IP: {machine_ip})")

    # Test 1: Discovery Service Health
    print("\n1️⃣ Testing Discovery Service Health...")
    try:
        response = requests.get(f"http://{machine_ip}/discovery/health", timeout=5)
        if response.status_code == 200:
            print("✅ Discovery Service accessible via nginx")
            print(f'   Status: {response.json()["status"]}')
        else:
            print(f"❌ Discovery Service health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Discovery Service not reachable: {e}")
        return False

    # Test 2: Service Registry
    print("\n2️⃣ Testing Service Registry...")
    try:
        response = requests.get(
            f"http://{machine_ip}/discovery/api/v1/services", timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service registry accessible")
            print(f'   Total services: {data["total_count"]}')
            print(f'   Healthy services: {data["healthy_count"]}')

            if data["total_count"] == 0:
                print("⚠️  No services registered!")
                return False

            # Check each service
            for service in data["services"]:
                print(
                    f'   📋 {service["name"]} at {service["host"]}:{service["port"]} ({service["status"]})'
                )

                # Test service connectivity
                service_url = f'http://{service["host"]}:{service["port"]}/health'
                try:
                    svc_response = requests.get(service_url, timeout=3)
                    if svc_response.status_code == 200:
                        print(f"     ✅ Service reachable")
                    else:
                        print(
                            f"     ❌ Service not reachable ({svc_response.status_code})"
                        )
                except Exception as svc_e:
                    print(f"     ❌ Service connectivity failed: {svc_e}")
        else:
            print(f"❌ Service registry failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Service registry not reachable: {e}")
        return False

    # Test 3: Authentication Flow (simulation)
    print("\n3️⃣ Testing Authentication Flow...")
    gateway_service = None
    for service in data["services"]:
        if service["name"] == "ppl-meta-gateway":
            gateway_service = service
            break

    if not gateway_service:
        print("❌ Gateway service not found in registry")
        return False

    # Test gateway endpoints that mobile app would use
    gateway_base = f'http://{gateway_service["host"]}:{gateway_service["port"]}'

    # Test auth endpoint
    try:
        # Test login endpoint exists (even without credentials)
        response = requests.post(
            f"{gateway_base}/api/v1/auth/login",
            json={"username": "test", "password": "test"},
            timeout=5,
        )
        if response.status_code in [
            200,
            400,
            401,
            422,
        ]:  # Any response means endpoint exists
            print("✅ Gateway auth endpoint accessible")
        else:
            print(f"❌ Gateway auth endpoint not accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Gateway auth test failed: {e}")

    print("\n🎉 Discovery Service integration test complete!")
    print("\n📱 Mobile app should now be able to:")
    print("   1. Find Discovery Service at http://{}/discovery".format(machine_ip))
    print("   2. Get service registry with resolved host IPs")
    print("   3. Connect to gateway for authentication")
    print("   4. Proceed with camera functionality")

    return True


if __name__ == "__main__":
    test_complete_discovery_flow()
