#!/usr/bin/env python3
"""
Quick fix utility to update Discovery Service registrations with actual network IPs.
This addresses the issue where services register with "0.0.0.0" which isn't accessible from mobile devices.
"""

import asyncio
import json
import socket
import subprocess
from typing import Optional

import aiohttp


def get_local_ip() -> Optional[str]:
    """Get the local network IP address (not 127.0.0.1)."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use Google DNS to determine route
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception:
        try:
            # Fallback: use ifconfig
            result = subprocess.run(
                ["ifconfig"], capture_output=True, text=True, check=True
            )

            # Look for inet addresses that aren't 127.0.0.1
            lines = result.stdout.split("\n")
            for line in lines:
                if "inet " in line and "127.0.0.1" not in line:
                    parts = line.strip().split()
                    for part in parts:
                        if (
                            part.startswith("192.168.")
                            or part.startswith("10.")
                            or part.startswith("172.")
                        ):
                            return part
        except Exception:
            pass

    return None


async def update_service_registration(service_name: str, actual_host: str, port: int):
    """Update a service registration with the actual network IP."""

    discovery_url = "http://localhost:8006"

    async with aiohttp.ClientSession() as session:
        try:
            # Get current services
            async with session.get(f"{discovery_url}/api/v1/services") as response:
                if response.status == 200:
                    data = await response.json()
                    services = data.get("services", [])

                    # Find the service to update
                    target_service = None
                    for service in services:
                        if service["name"] == service_name:
                            target_service = service
                            break

                    if target_service:
                        print(
                            f"🔍 Found {service_name}: {target_service['host']}:{target_service['port']}"
                        )

                        if target_service["host"] == "0.0.0.0":
                            print(
                                f"🔧 Updating {service_name} host from 0.0.0.0 to {actual_host}"
                            )

                            # Update the registration
                            update_data = target_service.copy()
                            update_data["host"] = actual_host

                            # Re-register with correct host
                            async with session.post(
                                f"{discovery_url}/api/v1/services/register",
                                json=update_data,
                            ) as update_response:
                                if update_response.status == 200:
                                    print(
                                        f"✅ Successfully updated {service_name} registration"
                                    )
                                else:
                                    print(
                                        f"❌ Failed to update {service_name}: {update_response.status}"
                                    )
                        else:
                            print(
                                f"✅ {service_name} already has correct host: {target_service['host']}"
                            )
                    else:
                        print(f"⚠️ Service {service_name} not found in registry")

        except Exception as e:
            print(f"❌ Error updating {service_name}: {e}")


async def main():
    """Main function to fix service registrations."""
    print("🔧 PPL Meta Discovery Service - Network IP Fix")
    print("=" * 50)

    # Get actual network IP
    actual_ip = get_local_ip()
    if not actual_ip:
        print("❌ Could not determine local network IP")
        return

    print(f"🌐 Detected local network IP: {actual_ip}")
    print()

    # Known services that might need updating
    services_to_check = [
        ("ppl-meta-gateway", 8080),
        ("ppl-meta-node", 8001),
        ("ppl-meta-media", 8000),
        ("ppl-meta-orchestrator", 8002),
        ("ppl-meta-cameras", 8005),
        ("ppl-meta-vision", 8003),
    ]

    for service_name, port in services_to_check:
        await update_service_registration(service_name, actual_ip, port)
        print()

    print("🏁 Registration update complete!")

    # Verify by listing all services
    print("\n📋 Current registered services:")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8006/api/v1/services") as response:
                if response.status == 200:
                    data = await response.json()
                    services = data.get("services", [])

                    for service in services:
                        host = service["host"]
                        status_icon = "✅" if host != "0.0.0.0" else "⚠️"
                        print(
                            f"  {status_icon} {service['name']}: {host}:{service['port']} [{service['status']}]"
                        )
                else:
                    print("❌ Could not fetch services list")
    except Exception as e:
        print(f"❌ Error fetching services: {e}")


if __name__ == "__main__":
    asyncio.run(main())
