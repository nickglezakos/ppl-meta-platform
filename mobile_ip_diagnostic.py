#!/usr/bin/env python3

import json
import socket
import subprocess
import urllib.error
import urllib.request


def get_machine_ip():
    """Get the machine's IP address using multiple methods"""
    print("🔍 Detecting Machine IP Address")
    print("=" * 40)

    methods = []

    # Method 1: Connect to external server
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip1 = s.getsockname()[0]
            methods.append(("Socket to 8.8.8.8", ip1))
    except Exception as e:
        methods.append(("Socket to 8.8.8.8", f"Failed: {e}"))

    # Method 2: ifconfig parsing
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True)
        lines = result.stdout.split("\n")
        for line in lines:
            if (
                "inet " in line
                and "127.0.0.1" not in line
                and "inet 169.254" not in line
            ):
                ip2 = line.split("inet ")[1].split(" ")[0]
                methods.append(("ifconfig parsing", ip2))
                break
    except Exception as e:
        methods.append(("ifconfig parsing", f"Failed: {e}"))

    # Method 3: hostname resolution
    try:
        hostname = socket.gethostname()
        ip3 = socket.gethostbyname(hostname)
        methods.append(("Hostname resolution", ip3))
    except Exception as e:
        methods.append(("Hostname resolution", f"Failed: {e}"))

    # Print all methods
    for method, result in methods:
        print(f"  {method}: {result}")

    # Return the most likely correct IP (first successful non-localhost)
    for method, result in methods:
        if not result.startswith("Failed") and not result.startswith("127."):
            return result

    return None


def test_url(url, description):
    """Test a URL and return the result"""
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return True, data
            else:
                return False, f"HTTP {response.status}"
    except Exception as e:
        return False, str(e)


def test_discovery_service(base_ip):
    """Test discovery service at the detected IP"""
    print(f"\n🧪 Testing Discovery Service at {base_ip}")
    print("=" * 50)

    # Test both direct and nginx proxy access
    endpoints = [
        (f"http://{base_ip}:8006/health", "Direct Discovery Service"),
        (f"http://{base_ip}/discovery/health", "Discovery via Nginx Proxy"),
        (f"http://localhost:8006/health", "Discovery localhost"),
    ]

    for url, description in endpoints:
        success, result = test_url(url, description)
        if success:
            print(f"  ✅ {description}: OK")
            print(f"     Status: {result.get('status', 'Unknown')}")
        else:
            print(f"  ❌ {description}: {result}")


def test_services_api(base_ip):
    """Test services API to see registered services"""
    print(f"\n📋 Testing Services API at {base_ip}")
    print("=" * 50)

    endpoints = [
        (f"http://{base_ip}:8006/api/v1/services", "Direct Services API"),
        (f"http://{base_ip}/discovery/api/v1/services", "Services via Nginx"),
        (f"http://localhost:8006/api/v1/services", "Services localhost"),
    ]

    for url, description in endpoints:
        success, result = test_url(url, description)
        if success:
            print(f"  ✅ {description}: Found {result['total_count']} services")

            # Show service IPs
            for service in result["services"][:3]:  # Show first 3 services
                print(f"     - {service['name']}: {service['host']}:{service['port']}")

            return True
        else:
            print(f"  ❌ {description}: {result}")

    return False


def generate_mobile_config(base_ip):
    """Generate configuration for mobile app"""
    print(f"\n📱 Mobile App Configuration")
    print("=" * 40)

    # Extract network prefix (first 3 octets)
    ip_parts = base_ip.split(".")
    network_prefix = ".".join(ip_parts[:3])

    print(f"Detected IP: {base_ip}")
    print(f"Network prefix: {network_prefix}")
    print(f"Discovery Service URL: http://{base_ip}:8006")
    print()
    print("Mobile app should use:")
    print(f"  - Auto-detected IP: {base_ip}")
    print(f"  - Network prefix: {network_prefix}")
    print(f"  - Discovery URL: http://{base_ip}:8006")
    print()
    print("If mobile app still uses 192.168.1.107, check for:")
    print("  1. Hardcoded IP values in mobile app code")
    print("  2. Cached network discovery results")
    print("  3. Network interface selection logic")


if __name__ == "__main__":
    print("🚀 PPL Meta Mobile Discovery Diagnostic Tool")
    print("=" * 60)

    # Get machine IP
    machine_ip = get_machine_ip()

    if not machine_ip:
        print("❌ Could not detect machine IP address")
        exit(1)

    print(f"\n🎯 Using detected IP: {machine_ip}")

    # Test discovery service
    test_discovery_service(machine_ip)

    # Test services API
    if test_services_api(machine_ip):
        print("\n✅ Discovery Service is working correctly")
    else:
        print("\n❌ Discovery Service has issues")

    # Generate mobile config
    generate_mobile_config(machine_ip)

    print(f"\n💡 Next Steps:")
    print(f"1. Update mobile app to use: {machine_ip}")
    print(f"2. Check mobile app's IP detection code")
    print(
        f"3. Verify mobile device is on same network ({'.'.join(machine_ip.split('.')[:3])}.x)"
    )
