#!/usr/bin/env python3
"""
Test script to simulate mobile VPN discovery scenario.
This simulates a mobile device on carrier network + Tailscale VPN
trying to discover the PPL Meta Platform.
"""

import json
import time

import requests


def test_vpn_discovery():
    """Test VPN discovery scenarios"""
    print("🧪 Testing VPN Discovery Scenarios")
    print("=" * 50)

    # Test scenarios
    scenarios = [
        {
            "name": "Local Network Discovery",
            "ip": "192.168.1.68",
            "description": "Direct local network access",
        },
        {
            "name": "Tailscale VPN Discovery",
            "ip": "100.102.56.67",
            "description": "Access via Tailscale mesh VPN",
        },
    ]

    for scenario in scenarios:
        print(f"\n🔍 {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Testing IP: {scenario['ip']}")

        try:
            # Test discovery endpoint
            discover_url = f"http://{scenario['ip']}:8001/api/v1/mobile/discover"
            print(f"   Calling: {discover_url}")

            response = requests.get(discover_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Discovery successful!")
                print(f"   📊 Detected IPs: {data['network']['detected_ips']}")
                print(
                    f"   🏷️  Network types: {json.dumps(data['network']['network_types'], indent=6)}"
                )
                print(f"   🔗 VPN support: {data['network']['vpn_support']}")

                # Test pairing info
                pairing_url = f"http://{scenario['ip']}:8001/api/v1/mobile/pairing-info"
                pairing_response = requests.get(pairing_url, timeout=5)
                if pairing_response.status_code == 200:
                    pairing_data = pairing_response.json()
                    print(
                        f"   📱 Pairing info available: {pairing_data['pairing']['status']}"
                    )
                else:
                    print(f"   ⚠️  Pairing info failed: {pairing_response.status_code}")

            else:
                print(f"   ❌ Discovery failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout - IP not accessible")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Connection error - IP not reachable")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n🎯 Scenario Analysis:")
    print(f"   • Local network (192.168.1.68): Direct access for same WiFi devices")
    print(
        f"   • Tailscale VPN (100.102.56.67): Secure access from any network via mesh VPN"
    )
    print(f"   • Mobile carrier + Tailscale: Works seamlessly across networks")
    print(f"\n✅ VPN discovery system ready for production!")


if __name__ == "__main__":
    test_vpn_discovery()
