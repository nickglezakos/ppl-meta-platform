#!/usr/bin/env python3
"""
Fix Mobile Discovery Configuration Issue

This script addresses the "No discovery configuration found" error by:
1. Checking the current discovery service status
2. Providing a proper discovery configuration
3. Testing mobile camera registration workflow
"""

import json
import subprocess
from datetime import datetime

import requests


def check_discovery_service():
    """Check if discovery service is running and accessible"""
    try:
        response = requests.get("http://localhost:8006/health", timeout=5)
        if response.status_code == 200:
            print("✅ Discovery service is running")
            return True
        else:
            print(f"❌ Discovery service returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Discovery service not accessible: {e}")
        return False


def get_registered_services():
    """Get all registered services from discovery"""
    try:
        response = requests.get("http://localhost:8006/api/v1/services", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f'📡 Found {data["total_count"]} registered services:')
            for service in data["services"]:
                status_icon = "✅" if service["status"] == "healthy" else "❌"
                print(
                    f'  {status_icon} {service["name"]} - {service["host"]}:{service["port"]} ({service["status"]})'
                )
            return data["services"]
        else:
            print(f"❌ Failed to get services: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting services: {e}")
        return []


def create_discovery_config(services):
    """Create a discovery configuration for mobile app"""
    config = {
        "discovery_url": "http://192.168.185.107:8006",
        "services": {},
        "last_updated": datetime.now().isoformat(),
        "version": "1.0.0",
    }

    for service in services:
        if service["status"] == "healthy":
            config["services"][service["name"]] = {
                "name": service["name"],
                "host": service["host"],
                "port": service["port"],
                "url": f'http://{service["host"]}:{service["port"]}',
                "capabilities": service.get("capabilities", []),
                "health_endpoint": service.get("health_endpoint", "/health"),
            }

    return config


def test_cameras_service_access():
    """Test direct access to cameras service"""
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8005/health", timeout=5)
        if response.status_code == 200:
            print("✅ Cameras service health check passed")
        else:
            print(f"❌ Cameras service health check failed: {response.status_code}")
            return False

        # Test mobile cameras endpoint (requires auth)
        print("🔐 Testing mobile cameras endpoint (requires authentication)...")
        # Note: This would need a valid JWT token
        print("⚠️ Skipping authenticated test - requires valid JWT token")
        return True

    except Exception as e:
        print(f"❌ Error testing cameras service: {e}")
        return False


def cleanup_duplicate_cameras():
    """Remove duplicate mobile camera registrations"""
    print("🧹 Cleaning up duplicate camera registrations...")
    # This would require authentication and careful deletion
    print("⚠️ Manual cleanup required - use admin interface or direct database access")


def main():
    print("🔧 PPL Meta Mobile Discovery Configuration Fix")
    print("=" * 50)

    # Check discovery service
    if not check_discovery_service():
        print("❌ Discovery service must be running first")
        return

    # Get registered services
    services = get_registered_services()
    if not services:
        print("❌ No services found in discovery")
        return

    # Create discovery configuration
    config = create_discovery_config(services)

    # Save configuration file
    config_file = "/tmp/mobile_discovery_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"📝 Discovery configuration saved to: {config_file}")
    print("📋 Configuration summary:")
    print(f'  - Discovery URL: {config["discovery_url"]}')
    print(f'  - Services found: {len(config["services"])}')
    for name, service in config["services"].items():
        print(f'    • {name}: {service["url"]}')

    # Test cameras service
    print("\n🧪 Testing cameras service access...")
    test_cameras_service_access()

    # Provide instructions
    print("\n📖 Next Steps:")
    print("1. Copy the discovery configuration to your mobile app")
    print("2. Update the mobile app to use the correct discovery URL")
    print("3. Ensure proper network connectivity between mobile device and services")
    print("4. Clean up duplicate camera registrations manually")

    print("\n💡 Mobile App Configuration:")
    print("  - Discovery URL: http://192.168.185.107:8006")
    print("  - Cameras Service: http://192.168.185.107:8005")
    print("  - Gateway Service: http://192.168.185.107:8080")


if __name__ == "__main__":
    main()
