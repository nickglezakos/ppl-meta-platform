#!/usr/bin/env python3
"""
PPL Meta Signage - Console Setup Tool

This tool runs ON the signage device (Raspberry Pi) and provides a command-line
interface for configuring the backend connection settings.

Usage:
    # Interactive setup
    python3 setup_console.py
    
    # Non-interactive setup
    python3 setup_console.py --backend-ip 192.168.1.50 --discovery-port 8006
    
    # Check current configuration
    python3 setup_console.py --show
    
    # Test connection
    python3 setup_console.py --test
"""

import argparse
import json
import sys
import re
import requests
from pathlib import Path
from typing import Optional, Dict, Any


class SignageConsoleSetup:
    """Console-based setup tool for PPL Meta Signage devices"""
    
    # SharedPreferences storage location for Linux Flutter apps
    CONFIG_DIR = Path.home() / '.local' / 'share' / 'signage_simple_player'
    CONFIG_FILE = CONFIG_DIR / 'shared_preferences.json'
    
    # Configuration keys (match ConfigService in Flutter)
    KEY_BACKEND_IP = 'flutter.backend_ip'
    KEY_DISCOVERY_PORT = 'flutter.discovery_port'
    KEY_IS_CONFIGURED = 'flutter.is_configured'
    
    def __init__(self):
        """Initialize the console setup tool"""
        self.config_dir = self.CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load current configuration from SharedPreferences
        
        Returns:
            Configuration dictionary
        """
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not read config file: {e}")
            return {}
    
    def save_config(self, backend_ip: str, discovery_port: int) -> bool:
        """
        Save configuration to SharedPreferences
        
        Args:
            backend_ip: Backend platform IP address
            discovery_port: Discovery service port
            
        Returns:
            True if save was successful
        """
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Load existing config or create new
            config = self.load_config()
            
            # Update configuration
            config[self.KEY_BACKEND_IP] = backend_ip
            config[self.KEY_DISCOVERY_PORT] = discovery_port
            config[self.KEY_IS_CONFIGURED] = True
            
            # Write to file
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Configuration saved to: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """
        Get current backend configuration
        
        Returns:
            Configuration dict or None if not configured
        """
        config = self.load_config()
        
        if not config.get(self.KEY_IS_CONFIGURED):
            return None
        
        backend_ip = config.get(self.KEY_BACKEND_IP)
        discovery_port = config.get(self.KEY_DISCOVERY_PORT, 8006)
        
        if not backend_ip:
            return None
        
        return {
            'backend_ip': backend_ip,
            'discovery_port': discovery_port,
            'discovery_url': f'http://{backend_ip}:{discovery_port}',
            'media_url': f'http://{backend_ip}:8000',
            'gateway_url': f'http://{backend_ip}:8080',
        }
    
    def test_connection(self, backend_ip: str, discovery_port: int) -> bool:
        """
        Test connection to backend discovery service
        
        Args:
            backend_ip: Backend IP address
            discovery_port: Discovery service port
            
        Returns:
            True if connection successful
        """
        discovery_url = f'http://{backend_ip}:{discovery_port}'
        
        print(f"🔍 Testing connection to {discovery_url}...")
        
        try:
            # Try health endpoint
            response = requests.get(f'{discovery_url}/health', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                service = data.get('service', 'unknown')
                print(f"✅ Successfully connected to Discovery Service")
                print(f"   Service: {service}")
                return True
            else:
                print(f"❌ Discovery service returned status code: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ Connection timeout - service not responding")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - service not reachable")
            return False
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def validate_ip(self, ip: str) -> bool:
        """
        Validate IP address format
        
        Args:
            ip: IP address string
            
        Returns:
            True if valid IP format
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def validate_port(self, port: int) -> bool:
        """
        Validate port number
        
        Args:
            port: Port number
            
        Returns:
            True if valid port
        """
        return 1 <= port <= 65535
    
    def interactive_setup(self) -> bool:
        """
        Run interactive console setup
        
        Returns:
            True if setup completed successfully
        """
        print("=" * 60)
        print("PPL Meta Signage - Console Setup")
        print("=" * 60)
        print()
        
        # Check for existing configuration
        current_config = self.get_current_config()
        if current_config:
            print("📋 Current Configuration:")
            print(f"   Backend IP: {current_config['backend_ip']}")
            print(f"   Discovery Port: {current_config['discovery_port']}")
            print(f"   Discovery URL: {current_config['discovery_url']}")
            print()
            
            response = input("Configuration already exists. Reconfigure? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Setup cancelled.")
                return False
            print()
        
        # Get backend IP
        while True:
            default_ip = current_config['backend_ip'] if current_config else '192.168.1.50'
            backend_ip = input(f"Backend IP address [{default_ip}]: ").strip()
            
            if not backend_ip:
                backend_ip = default_ip
            
            if self.validate_ip(backend_ip):
                break
            else:
                print("❌ Invalid IP address format. Please use format: xxx.xxx.xxx.xxx")
                print()
        
        # Get discovery port
        while True:
            default_port = current_config['discovery_port'] if current_config else 8006
            port_input = input(f"Discovery Service Port [{default_port}]: ").strip()
            
            if not port_input:
                discovery_port = default_port
                break
            
            try:
                discovery_port = int(port_input)
                if self.validate_port(discovery_port):
                    break
                else:
                    print("❌ Invalid port number. Must be between 1-65535")
                    print()
            except ValueError:
                print("❌ Invalid port number. Please enter a number.")
                print()
        
        print()
        print("Configuration Summary:")
        print(f"  Backend IP: {backend_ip}")
        print(f"  Discovery Port: {discovery_port}")
        print(f"  Discovery URL: http://{backend_ip}:{discovery_port}")
        print(f"  Media URL: http://{backend_ip}:8000")
        print(f"  Gateway URL: http://{backend_ip}:8080")
        print()
        
        # Test connection
        response = input("Test connection before saving? (Y/n): ").strip().lower()
        if response not in ['n', 'no']:
            if not self.test_connection(backend_ip, discovery_port):
                print()
                response = input("Connection test failed. Save configuration anyway? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Setup cancelled.")
                    return False
        
        print()
        
        # Save configuration
        if self.save_config(backend_ip, discovery_port):
            print()
            print("✅ Configuration saved successfully!")
            print()
            print("Next Steps:")
            print("  1. Restart the signage application for changes to take effect")
            print("  2. The application will automatically connect to the backend")
            print("  3. Check logs for connection status")
            print()
            return True
        else:
            print()
            print("❌ Failed to save configuration")
            return False
    
    def show_config(self) -> bool:
        """
        Display current configuration
        
        Returns:
            True if configuration exists
        """
        config = self.get_current_config()
        
        if not config:
            print("❌ No configuration found")
            print()
            print("Run setup to configure:")
            print("  python3 setup_console.py")
            return False
        
        print("📋 Current Configuration:")
        print(f"  Backend IP: {config['backend_ip']}")
        print(f"  Discovery Port: {config['discovery_port']}")
        print(f"  Discovery URL: {config['discovery_url']}")
        print(f"  Media URL: {config['media_url']}")
        print(f"  Gateway URL: {config['gateway_url']}")
        print()
        print(f"Configuration file: {self.config_file}")
        
        return True
    
    def non_interactive_setup(self, backend_ip: str, discovery_port: int, skip_test: bool = False) -> bool:
        """
        Run non-interactive setup with provided parameters
        
        Args:
            backend_ip: Backend IP address
            discovery_port: Discovery port
            skip_test: Skip connection test
            
        Returns:
            True if setup successful
        """
        # Validate inputs
        if not self.validate_ip(backend_ip):
            print(f"❌ Invalid IP address: {backend_ip}")
            return False
        
        if not self.validate_port(discovery_port):
            print(f"❌ Invalid port: {discovery_port}")
            return False
        
        # Test connection unless skipped
        if not skip_test:
            if not self.test_connection(backend_ip, discovery_port):
                print("❌ Connection test failed. Use --force to save anyway.")
                return False
        
        # Save configuration
        if self.save_config(backend_ip, discovery_port):
            print("✅ Configuration saved successfully!")
            print()
            print("Configuration:")
            print(f"  Backend IP: {backend_ip}")
            print(f"  Discovery Port: {discovery_port}")
            print(f"  Discovery URL: http://{backend_ip}:{discovery_port}")
            print()
            print("⚠️  Restart the signage application for changes to take effect.")
            return True
        else:
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Configure PPL Meta Signage backend connection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive setup
  python3 setup_console.py
  
  # Non-interactive setup
  python3 setup_console.py --backend-ip 192.168.1.50 --discovery-port 8006
  
  # Show current configuration
  python3 setup_console.py --show
  
  # Test current configuration
  python3 setup_console.py --test
  
  # Setup without testing connection
  python3 setup_console.py --backend-ip 192.168.1.50 --force
        """
    )
    
    parser.add_argument(
        '--backend-ip',
        help='Backend platform IP address'
    )
    
    parser.add_argument(
        '--discovery-port',
        type=int,
        default=8006,
        help='Discovery service port (default: 8006)'
    )
    
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show current configuration'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test connection with current configuration'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip connection test (save configuration even if test fails)'
    )
    
    args = parser.parse_args()
    
    setup = SignageConsoleSetup()
    
    # Show configuration
    if args.show:
        success = setup.show_config()
        sys.exit(0 if success else 1)
    
    # Test connection
    if args.test:
        config = setup.get_current_config()
        if not config:
            print("❌ No configuration found. Run setup first.")
            sys.exit(1)
        
        success = setup.test_connection(config['backend_ip'], config['discovery_port'])
        sys.exit(0 if success else 1)
    
    # Non-interactive setup
    if args.backend_ip:
        success = setup.non_interactive_setup(
            args.backend_ip,
            args.discovery_port,
            skip_test=args.force
        )
        sys.exit(0 if success else 1)
    
    # Interactive setup
    success = setup.interactive_setup()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
