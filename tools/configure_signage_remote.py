#!/usr/bin/env python3
"""
PPL Meta Signage - Remote Configuration Tool

Configure signage devices remotely without physical access.
This tool connects to the signage device's HTTP server (port 8009) and updates its configuration.
"""

import argparse
import json
import sys
import requests
from typing import Optional


class SignageRemoteConfigurator:
    """Remote configuration manager for PPL Meta Signage devices"""

    def __init__(self, device_ip: str, device_port: int = 8009):
        """
        Initialize the remote configurator
        
        Args:
            device_ip: IP address of the signage device (Raspberry Pi)
            device_port: HTTP server port on the device (default: 8009)
        """
        self.device_ip = device_ip
        self.device_port = device_port
        self.base_url = f"http://{device_ip}:{device_port}"

    def check_health(self) -> bool:
        """
        Check if the signage device is reachable
        
        Returns:
            True if device is healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Device is healthy")
                print(f"   Service: {data.get('service')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Device ID: {data.get('device_id')}")
                return True
            else:
                print(f"❌ Device returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot reach device: {e}")
            return False

    def get_current_config(self) -> Optional[dict]:
        """
        Retrieve current configuration from the device
        
        Returns:
            Configuration dictionary or None if failed
        """
        try:
            response = requests.get(f"{self.base_url}/api/v1/config", timeout=5)
            if response.status_code == 200:
                data = response.json()
                config = data.get('configuration', {})
                print(f"\n📋 Current Configuration:")
                print(f"   Backend IP: {config.get('backend_ip')}")
                print(f"   Discovery Port: {config.get('discovery_port')}")
                print(f"   Configured: {config.get('is_configured')}")
                print(f"   Discovery URL: {config.get('discovery_service_url')}")
                print(f"   Media URL: {config.get('media_service_url')}")
                print(f"   Gateway URL: {config.get('gateway_url')}")
                return config
            else:
                print(f"❌ Failed to get config: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def set_config(self, backend_ip: str, discovery_port: int = 8006) -> bool:
        """
        Update device configuration remotely
        
        Args:
            backend_ip: IP address of the backend platform
            discovery_port: Discovery service port (default: 8006)
            
        Returns:
            True if configuration was successful, False otherwise
        """
        try:
            payload = {
                "backend_ip": backend_ip,
                "discovery_port": discovery_port
            }
            
            print(f"\n🔧 Updating Configuration:")
            print(f"   Backend IP: {backend_ip}")
            print(f"   Discovery Port: {discovery_port}")
            
            response = requests.post(
                f"{self.base_url}/api/v1/config",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Configuration Updated Successfully!")
                
                if data.get('restart_required'):
                    print(f"⚠️  Restart Required: Please restart the signage application for changes to take effect.")
                
                config = data.get('configuration', {})
                print(f"\n📋 New Configuration:")
                print(f"   Backend IP: {config.get('backend_ip')}")
                print(f"   Discovery Port: {config.get('discovery_port')}")
                print(f"   Discovery URL: {config.get('discovery_service_url')}")
                print(f"   Media URL: {config.get('media_service_url')}")
                print(f"   Gateway URL: {config.get('gateway_url')}")
                
                return True
            else:
                print(f"❌ Configuration failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error')}")
                    print(f"   Message: {error_data.get('message')}")
                except:
                    print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Configure PPL Meta Signage devices remotely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check device health
  %(prog)s --device-ip 192.168.1.100 --check

  # Get current configuration
  %(prog)s --device-ip 192.168.1.100 --get

  # Set configuration
  %(prog)s --device-ip 192.168.1.100 --backend-ip 192.168.1.50

  # Set configuration with custom port
  %(prog)s --device-ip 192.168.1.100 --backend-ip 192.168.1.50 --discovery-port 8006
        """
    )
    
    parser.add_argument(
        '--device-ip',
        required=True,
        help='IP address of the signage device (Raspberry Pi)'
    )
    
    parser.add_argument(
        '--device-port',
        type=int,
        default=8009,
        help='HTTP server port on the device (default: 8009)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check device health status'
    )
    
    parser.add_argument(
        '--get',
        action='store_true',
        help='Get current configuration'
    )
    
    parser.add_argument(
        '--backend-ip',
        help='Backend platform IP address to configure'
    )
    
    parser.add_argument(
        '--discovery-port',
        type=int,
        default=8006,
        help='Discovery service port (default: 8006)'
    )

    args = parser.parse_args()

    # Create configurator
    configurator = SignageRemoteConfigurator(args.device_ip, args.device_port)

    print(f"🔌 Connecting to signage device at {args.device_ip}:{args.device_port}")
    print()

    # Execute requested action
    if args.check:
        success = configurator.check_health()
        sys.exit(0 if success else 1)
    
    if args.get:
        config = configurator.get_current_config()
        sys.exit(0 if config else 1)
    
    if args.backend_ip:
        success = configurator.set_config(args.backend_ip, args.discovery_port)
        sys.exit(0 if success else 1)
    
    # No action specified, show help
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
