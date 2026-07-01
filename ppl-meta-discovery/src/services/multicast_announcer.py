"""Multicast announcement service for PPL Meta Discovery Service."""

import asyncio
import json
import logging
import socket
import struct
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MulticastAnnouncer:
    """Handles multicast announcements for service discovery.

    Phase 2: VPN-aware — includes Tailscale IP in announcements so
    VPN-connected clients can discover the platform without multicast.
    """

    def __init__(
        self,
        multicast_group: str = "224.1.1.1",
        multicast_port: int = 12345,
        announcement_interval: int = 30,
        discovery_port: int = 8006,
    ):
        super().__init__()
        self.multicast_group = multicast_group
        self.multicast_port = multicast_port
        self.announcement_interval = announcement_interval
        self.discovery_port = discovery_port

        self._sock: Optional[socket.socket] = None
        self._announcement_task: Optional[asyncio.Task] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False

        # Local network interfaces cache
        self._local_ips: list[str] = []
        self._tailscale_ip: Optional[str] = None

    async def start(self):
        """Start multicast announcements and listener."""
        logger.info(
            f"Starting multicast announcer on {self.multicast_group}:{self.multicast_port}"
        )

        self._running = True
        self._tailscale_ip = self._get_tailscale_ip()
        self._update_local_ips()

        # Start announcement task
        self._announcement_task = asyncio.create_task(self._announcement_loop())

        # Start listener task for discovery requests
        self._listener_task = asyncio.create_task(self._listener_loop())

    async def stop(self):
        """Stop multicast announcements."""
        logger.info("Stopping multicast announcer")

        self._running = False

        if self._announcement_task:
            self._announcement_task.cancel()
            try:
                await self._announcement_task
            except asyncio.CancelledError:
                pass

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._sock:
            self._sock.close()
            self._sock = None

    def _get_tailscale_ip(self) -> Optional[str]:
        """Get the local Tailscale VPN IP, if connected."""
        try:
            import subprocess, json
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                ips = data.get("Self", {}).get("TailscaleIPs", [])
                if ips:
                    return ips[0]
        except Exception:
            pass
        return None

    def _update_local_ips(self):
        """Update list of local IP addresses."""
        try:
            # Get all network interfaces
            hostname = socket.gethostname()
            local_ips = []

            # Get primary IP (most reliable)
            try:
                # Connect to a remote address to determine best local IP
                temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                temp_sock.connect(("8.8.8.8", 80))
                primary_ip = temp_sock.getsockname()[0]
                temp_sock.close()
                local_ips.append(primary_ip)
            except Exception:
                pass

            # Get localhost
            local_ips.append("127.0.0.1")

            # Try to get all interface IPs
            try:
                import netifaces

                for interface in netifaces.interfaces():
                    try:
                        addrs = netifaces.ifaddresses(interface)
                        if netifaces.AF_INET in addrs:
                            for addr_info in addrs[netifaces.AF_INET]:
                                ip = addr_info.get("addr")
                                if ip and ip not in local_ips:
                                    local_ips.append(ip)
                    except Exception:
                        continue
            except ImportError:
                # netifaces not available, use fallback
                try:
                    hostname_ips = socket.gethostbyname_ex(hostname)[2]
                    for ip in hostname_ips:
                        if ip not in local_ips:
                            local_ips.append(ip)
                except Exception:
                    pass

            self._local_ips = local_ips
            logger.info(f"Detected local IPs: {self._local_ips}")

        except Exception as e:
            logger.warning(f"Failed to update local IPs: {e}")
            self._local_ips = ["127.0.0.1"]

    def _create_announcement_message(self) -> bytes:
        """Create announcement message."""
        message = {
            "type": "discovery_service_announcement",
            "service": "ppl-meta-discovery",
            "version": "2.14.0",
            "port": self.discovery_port,
            "endpoints": [
                "/health",
                "/api/v1/services",
                "/api/v1/devices",
                "/api/v1/platform/metadata",
                "/api/v1/platform/topology",
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "discovery_port": self.discovery_port,
            "local_ips": self._local_ips,
            # Phase 2: VPN-aware
            "tailscale_ip": self._tailscale_ip,
            "tailscale_network": "100.64.0.0/10",
        }
        return json.dumps(message).encode("utf-8")

    async def _announcement_loop(self):
        """Main announcement loop."""
        try:
            while self._running:
                try:
                    await self._send_announcement()
                    await asyncio.sleep(self.announcement_interval)
                except Exception as e:
                    logger.error(f"Error in announcement loop: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry
        except asyncio.CancelledError:
            logger.info("Announcement loop cancelled")

    async def _send_announcement(self):
        """Send multicast announcement."""
        try:
            # Create UDP socket for sending
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Set TTL for multicast
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

            # Create announcement message
            message = self._create_announcement_message()

            # Send to multicast group
            sock.sendto(message, (self.multicast_group, self.multicast_port))
            sock.close()

            logger.debug(
                f"Sent multicast announcement to {self.multicast_group}:{self.multicast_port}"
            )

        except Exception as e:
            logger.error(f"Failed to send multicast announcement: {e}")

    async def _listener_loop(self):
        """Listen for discovery requests."""
        try:
            # Create UDP socket for listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to multicast group
            sock.bind(("", self.multicast_port))

            # Join multicast group
            mreq = struct.pack(
                "4sl", socket.inet_aton(self.multicast_group), socket.INADDR_ANY
            )
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Set socket to non-blocking
            sock.setblocking(False)
            self._sock = sock

            logger.info(
                f"Listening for multicast requests on {self.multicast_group}:{self.multicast_port}"
            )

            while self._running:
                try:
                    # Use asyncio to make socket non-blocking
                    loop = asyncio.get_event_loop()
                    data, addr = await loop.sock_recvfrom(sock, 1024)

                    # Process received message
                    await self._process_discovery_request(data, addr)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Socket would block, continue
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Listener loop cancelled")
        except Exception as e:
            logger.error(f"Error in listener loop: {e}")
        finally:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass

    async def _process_discovery_request(self, data: bytes, addr: tuple):
        """Process incoming discovery request.

        Args:
            data: Received data
            addr: Sender address
        """
        try:
            message = json.loads(data.decode("utf-8"))

            if message.get("type") == "discovery_request":
                logger.info(f"Received discovery request from {addr[0]}:{addr[1]}")

                # Send response with discovery service information
                response = self._create_announcement_message()

                # Send direct response to requester
                response_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                response_sock.sendto(response, addr)
                response_sock.close()

                logger.debug(f"Sent discovery response to {addr[0]}:{addr[1]}")

        except Exception as e:
            logger.debug(f"Failed to process discovery request from {addr}: {e}")

    def send_discovery_request(self) -> None:
        """Send a discovery request to find other discovery services."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

            request = {
                "type": "discovery_request",
                "requester": "ppl-meta-discovery",
                "timestamp": datetime.utcnow().isoformat(),
            }

            message = json.dumps(request).encode("utf-8")
            sock.sendto(message, (self.multicast_group, self.multicast_port))
            sock.close()

            logger.info("Sent discovery request via multicast")

        except Exception as e:
            logger.error(f"Failed to send discovery request: {e}")
