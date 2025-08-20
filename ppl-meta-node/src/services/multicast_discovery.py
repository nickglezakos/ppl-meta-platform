#!/usr/bin/env python3
"""
PPL Meta Platform - Multicast Service Discovery Broadcaster

This service broadcasts the Node service information via multicast UDP packets,
allowing Flutter mobile apps to automatically discover the platform on any
network (WiFi, VPN, hotspot, etc.) without IP scanning or hardcoded addresses.

The broadcaster sends periodic announcements containing:
- Service type and version
- Current IP address and port
- Platform capabilities
- Network timestamp

Flutter apps listen for these announcements and can immediately connect
to the discovered service endpoint.
"""

import json
import logging
import socket
import struct
import threading
import time
from typing import Any, Dict, Optional

import netifaces


class MulticastServiceDiscoveryBroadcaster:
    """Multicast broadcaster for PPL Meta Node service discovery"""

    # Multicast configuration
    MULTICAST_GROUP = "224.1.1.1"  # PPL Meta specific multicast address
    MULTICAST_PORT = 12345
    BROADCAST_INTERVAL = 5.0  # Send announcement every 5 seconds
    TTL = 2  # Time-to-live (local network only)

    def __init__(self, service_port: int = 8001, service_name: str = "ppl-meta-node"):
        """
        Initialize the multicast broadcaster

        Args:
            service_port: Port where the Node service is running
            service_name: Name of the service being broadcast
        """
        # Set up logging first
        self.logger = logging.getLogger(__name__)

        self.service_port = service_port
        self.service_name = service_name
        self.socket: Optional[socket.socket] = None
        self.broadcast_thread: Optional[threading.Thread] = None
        self.running = False

        # Get IP after logger is set up
        self.service_ip = self._get_local_ip()

    def _get_local_ip(self) -> str:
        """
        Get the most appropriate local IP address for the service

        Prioritizes:
        1. VPN interfaces (Tailscale, etc.)
        2. WiFi interfaces
        3. Ethernet interfaces
        4. Fallback to localhost
        """
        try:
            # Get all network interfaces
            interfaces = netifaces.interfaces()

            # Priority order for interface types
            preferred_prefixes = [
                "tailscale",  # Tailscale VPN
                "utun",  # macOS VPN tunnels
                "tun",  # Generic VPN tunnels
                "en0",  # Primary WiFi on macOS
                "wlan",  # WiFi on Linux
                "eth",  # Ethernet
                "en1",  # Secondary network on macOS
            ]

            # Try each preferred interface type
            for prefix in preferred_prefixes:
                for interface in interfaces:
                    if interface.startswith(prefix):
                        addrs = netifaces.ifaddresses(interface)
                        if netifaces.AF_INET in addrs:
                            for addr_info in addrs[netifaces.AF_INET]:
                                ip = addr_info.get("addr")
                                if ip and not ip.startswith("127."):
                                    self.logger.info(
                                        "Selected IP %s from interface %s",
                                        ip,
                                        interface,
                                    )
                                    return ip

            # Fallback: use any non-localhost address
            for interface in interfaces:
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info.get("addr")
                        if ip and not ip.startswith("127."):
                            self.logger.info(
                                "Fallback IP %s from interface %s", ip, interface
                            )
                            return ip

        except OSError as e:
            self.logger.warning("Error detecting IP address: %s", e)

        # Final fallback
        self.logger.warning("Using localhost as fallback IP")
        return "127.0.0.1"

    def _create_service_announcement(self) -> Dict[str, Any]:
        """Create the service announcement message"""
        return {
            "service": self.service_name,
            "version": "2.13.1",
            "ip": self.service_ip,
            "port": self.service_port,
            "protocol": "http",
            "endpoints": {
                "health": f"http://{self.service_ip}:{self.service_port}/api/v1/health",
                "login": f"http://{self.service_ip}:{self.service_port}/api/v1/users/login",
                "services": f"http://{self.service_ip}:{self.service_port}/api/v1/users/platform/services",
            },
            "capabilities": [
                "authentication",
                "service_discovery",
                "mobile_camera_registration",
            ],
            "timestamp": int(time.time()),
            "discovery_method": "multicast_udp",
        }

    def start(self) -> bool:
        """Start the multicast broadcaster"""
        if self.running:
            self.logger.warning("Broadcaster already running")
            return True

        try:
            # Create multicast socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Set multicast TTL
            ttl = struct.pack("b", self.TTL)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

            # Set multicast interface (use service IP)
            mreq = socket.inet_aton(self.service_ip)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, mreq)

            self.running = True

            # Start broadcast thread
            self.broadcast_thread = threading.Thread(
                target=self._broadcast_loop, daemon=True
            )
            self.broadcast_thread.start()

            self.logger.info("🎯 Multicast discovery broadcaster started")
            self.logger.info("   Service: %s", self.service_name)
            self.logger.info("   IP: %s:%s", self.service_ip, self.service_port)
            self.logger.info(
                "   Multicast: %s:%s", self.MULTICAST_GROUP, self.MULTICAST_PORT
            )
            self.logger.info("   Interval: %ss", self.BROADCAST_INTERVAL)

            return True

        except OSError as e:
            self.logger.error("Failed to start multicast broadcaster: %s", e)
            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False

    def stop(self):
        """Stop the multicast broadcaster"""
        if not self.running:
            return

        self.logger.info("🛑 Stopping multicast discovery broadcaster...")
        self.running = False

        if self.socket:
            self.socket.close()
            self.socket = None

        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join(timeout=2.0)

        self.logger.info("✅ Multicast broadcaster stopped")

    def _broadcast_loop(self):
        """Main broadcast loop - runs in separate thread"""
        self.logger.info("📡 Starting multicast broadcast loop...")

        while self.running:
            try:
                # Create service announcement
                announcement = self._create_service_announcement()
                message = json.dumps(announcement).encode("utf-8")

                # Send multicast packet
                self.socket.sendto(message, (self.MULTICAST_GROUP, self.MULTICAST_PORT))

                self.logger.debug(
                    "📡 Broadcast sent: %s bytes to %s:%s",
                    len(message),
                    self.MULTICAST_GROUP,
                    self.MULTICAST_PORT,
                )

                # Wait for next broadcast
                for _ in range(int(self.BROADCAST_INTERVAL * 10)):
                    if not self.running:
                        break
                    time.sleep(0.1)

            except OSError as e:
                if self.running:  # Only log errors if we're supposed to be running
                    self.logger.error("Broadcast error: %s", e)
                    time.sleep(1.0)  # Brief pause before retry

        self.logger.info("📡 Multicast broadcast loop stopped")

    def update_service_ip(self, new_ip: str):
        """Update the service IP address (useful for network changes)"""
        if new_ip != self.service_ip:
            old_ip = self.service_ip
            self.service_ip = new_ip
            self.logger.info("🔄 Service IP updated: %s → %s", old_ip, new_ip)


# Example usage for testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and start broadcaster
    broadcaster = MulticastServiceDiscoveryBroadcaster(service_port=8001)

    try:
        if broadcaster.start():
            print("Broadcaster started successfully. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        else:
            print("Failed to start broadcaster")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        broadcaster.stop()
