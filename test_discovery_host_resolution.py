#!/usr/bin/env python3

import json

import requests


def test_discovery_service():
    """Test Discovery Service with host resolution"""

    print("🔍 Testing Discovery Service host resolution...")

    # Test via nginx proxy
    urls = [
        "http://localhost/discovery/api/v1/services",
        "http://localhost:8006/api/v1/services",
    ]

    for url in urls:
        try:
            print(f"\n🌐 Testing: {url}")
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS ({response.status_code})")
                print(f"   📋 Found {data['total_count']} services")

                for service in data["services"]:
                    print(
                        f"   - {service['name']} ({service['service_type']}) at {service['host']}:{service['port']}"
                    )

                    # Test if the host is resolvable
                    if service["host"] != "0.0.0.0":
                        print(f"   ✅ Host {service['host']} is external-accessible")
                    else:
                        print(
                            f"   ❌ Host {service['host']} is NOT external-accessible"
                        )
            else:
                print(f"❌ FAILED ({response.status_code})")

        except Exception as e:
            print(f"❌ ERROR: {e}")


def simulate_mobile_discovery():
    """Simulate mobile app discovery process"""

    print("\n📱 Simulating mobile app discovery...")

    # Machine IP that mobile app would discover
    machine_ip = "192.168.1.229"

    test_urls = [
        f"http://{machine_ip}/discovery/api/v1/services",
        f"http://{machine_ip}:8006/api/v1/services",
    ]

    for url in test_urls:
        try:
            print(f"\n🌐 Mobile testing: {url}")
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS ({response.status_code})")
                print(f"   📋 Found {data['total_count']} services")

                for service in data["services"]:
                    print(
                        f"   - {service['name']} at {service['host']}:{service['port']}"
                    )

                    # Test connectivity to resolved service
                    service_url = f"http://{service['host']}:{service['port']}/health"
                    try:
                        svc_response = requests.get(service_url, timeout=3)
                        if svc_response.status_code == 200:
                            print(f"     ✅ Service reachable at {service_url}")
                        else:
                            print(
                                f"     ❌ Service not reachable at {service_url} ({svc_response.status_code})"
                            )
                    except Exception as svc_e:
                        print(f"     ❌ Service connectivity failed: {svc_e}")
            else:
                print(f"❌ FAILED ({response.status_code})")

        except Exception as e:
            print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    test_discovery_service()
    simulate_mobile_discovery()
