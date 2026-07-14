"""Mesh VPN Service for PPL Meta Node.

Manages Tailscale client lifecycle on the node:
- Enrollment via authority-issued pre-auth keys
- VPN IP detection and caching
- Peer discovery (all peers, Matrix-group filtered)
- Status reporting
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TAILSCALE_UP_TIMEOUT = 30  # seconds for tailscale up to complete
TAILSCALE_STATUS_TIMEOUT = 5  # seconds for status queries


class MeshVPNService:
    """Manages Tailscale client lifecycle on the node.

    On startup, if a vpn_enabled licence feature is present, this service:
    1. Fetches a pre-auth key from the authority VPS
    2. Runs `tailscale up --authkey=<key>`
    3. Caches the assigned Tailscale IP
    4. Registers the VPN IP with the discovery service

    No Docker required — tailscale runs directly on the host.
    """

    def __init__(self):
        self.tailscale_binary: str = self._find_tailscale()
        self.tailscale_ip: Optional[str] = None
        self.enrolled: bool = False
        self._headscale_server: Optional[str] = None

    def _find_tailscale(self) -> str:
        """Find the tailscale binary on PATH.

        Returns:
            Absolute path to tailscale binary.

        Raises:
            RuntimeError: If tailscale is not installed.
        """
        path = shutil.which("tailscale")
        if not path:
            raise RuntimeError(
                "tailscale not found on PATH. Install with: brew install tailscale"
            )
        logger.info("Found tailscale at %s", path)
        return path

    def is_available(self) -> bool:
        """Check if tailscale binary is available."""
        return bool(self.tailscale_binary)

    async def enroll(
        self,
        authority_url: str,
        installation_uuid: str,
        application_key: str,
        hostname: str = "eyenet-node",
    ) -> bool:
        """Enroll this node in the VPN mesh.

        Fetches a pre-auth key from the authority VPS and brings up the
        Tailscale client with that key. The key is cryptographically scoped
        to this installation's Matrix group via ACL tags.

        Args:
            authority_url: Base URL of the authority service.
            installation_uuid: This installation's UUID.
            application_key: The installation's application key (lic_...).
            hostname: Hostname to register with in the Tailscale mesh.

        Returns:
            True if enrollment succeeded, False otherwise.
        """
        logger.info(
            "Enrolling node in VPN mesh: installation=%s hostname=%s",
            installation_uuid,
            hostname,
        )

        # 1. Fetch pre-auth key from authority
        auth_key = await self._fetch_auth_key(
            authority_url, installation_uuid, application_key
        )
        if not auth_key:
            logger.error("Failed to fetch pre-auth key from authority")
            return False

        # 2. Bring up tailscale
        success = await self._run_tailscale_up(auth_key, hostname)
        if not success:
            logger.error("Failed to bring up tailscale")
            return False

        # 3. Fetch assigned IP
        self.tailscale_ip = await self._get_tailscale_ip_async()
        if not self.tailscale_ip:
            logger.error("Failed to get Tailscale IP after enrollment")
            return False

        self.enrolled = True
        logger.info("Node enrolled in VPN mesh: %s", self.tailscale_ip)
        return True

    async def _fetch_auth_key(
        self,
        authority_url: str,
        installation_uuid: str,
        application_key: str,
    ) -> Optional[str]:
        """Fetch a pre-authorized key from the authority VPN API.

        Args:
            authority_url: Base URL of the authority service.
            installation_uuid: This installation's UUID.
            application_key: The installation's application key.

        Returns:
            The pre-auth key string, or None on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{authority_url}/api/v1/vpn/enroll-installation",
                    json={
                        "installation_uuid": installation_uuid,
                        "application_key": application_key,
                    },
                )

            if response.status_code != 200:
                logger.error(
                    "Authority VPN enrollment failed: HTTP %s - %s",
                    response.status_code,
                    response.text,
                )
                return None

            data = response.json()
            auth_key = data.get("auth_key")
            if not auth_key:
                logger.error("No auth_key in authority response: %s", data)
                return None

            self._headscale_server = data.get("headscale_server")
            tags = data.get("tags", [])
            logger.info(
                "Received pre-auth key from authority (tags=%s, server=%s)",
                tags,
                self._headscale_server,
            )
            return auth_key

        except httpx.HTTPError as exc:
            logger.error("HTTP error fetching auth key: %s", exc)
            return None
        except Exception as exc:
            logger.error("Unexpected error fetching auth key: %s", exc)
            return None

    async def _run_tailscale_up(self, auth_key: str, hostname: str) -> bool:
        """Run `tailscale up` with the provided auth key.

        Args:
            auth_key: Pre-auth key from authority.
            hostname: Hostname for this node in the mesh.

        Returns:
            True if tailscale up succeeded, False otherwise.
        """
        cmd = [
            self.tailscale_binary,
            "up",
            "--authkey", auth_key,
            "--hostname", hostname,
            "--accept-routes=false",
            "--accept-dns=false",
        ]

        # If headscale server URL is known, add it
        if self._headscale_server:
            cmd.extend(["--login-server", self._headscale_server])

        logger.info("Running: %s", " ".join(
            a if a != auth_key else "tskey-auth-***" for a in cmd
        ))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=TAILSCALE_UP_TIMEOUT
            )

            if proc.returncode != 0:
                logger.error(
                    "tailscale up failed (exit %s): %s",
                    proc.returncode,
                    stderr.decode() if stderr else "no stderr",
                )
                return False

            logger.info("tailscale up succeeded")
            return True

        except asyncio.TimeoutError:
            logger.error("tailscale up timed out after %ss", TAILSCALE_UP_TIMEOUT)
            return False
        except Exception as exc:
            logger.error("Failed to run tailscale up: %s", exc)
            return False

    async def _get_tailscale_ip_async(self) -> Optional[str]:
        """Get the local Tailscale IP asynchronously.

        Returns:
            The first Tailscale IP (100.64.x.x), or None.
        """
        try:
            result = await self._run_tailscale_json(["status", "--json"])
            if not result:
                return None

            self_data = result.get("Self", {})
            ips = self_data.get("TailscaleIPs", [])
            return ips[0] if ips else None

        except Exception as exc:
            logger.error("Failed to get tailscale IP: %s", exc)
            return None

    async def _run_tailscale_json(self, args: list[str]) -> Optional[dict]:
        """Run a tailscale command and parse JSON output.

        Args:
            args: Tailscale subcommand arguments (e.g., ["status", "--json"]).

        Returns:
            Parsed JSON dict, or None on failure.
        """
        cmd = [self.tailscale_binary] + args
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=TAILSCALE_STATUS_TIMEOUT
            )

            if proc.returncode != 0:
                logger.debug(
                    "tailscale %s failed (exit %s): %s",
                    " ".join(args),
                    proc.returncode,
                    stderr.decode() if stderr else "",
                )
                return None

            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            logger.debug("tailscale %s timed out", " ".join(args))
            return None
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse tailscale JSON output: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Failed to run tailscale %s: %s", " ".join(args), exc)
            return None

    async def get_peers(self, tag_filter: Optional[str] = None) -> list[dict]:
        """List all peers in the mesh, optionally filtered by ACL tag.

        Args:
            tag_filter: Optional ACL tag to filter peers by
                        (e.g., "tag:matrix-<uuid>").

        Returns:
            List of peer data dicts.
        """
        result = await self._run_tailscale_json(["status", "--json"])
        if not result:
            return []

        peers = result.get("Peer", {})
        if tag_filter:
            peers = {
                k: v for k, v in peers.items()
                if tag_filter in v.get("Tags", [])
            }
        return list(peers.values())

    async def get_matrix_peers(self, matrix_group_id: str) -> list[dict]:
        """Get all VPN peers in the same Matrix group.

        Args:
            matrix_group_id: UUID of the Matrix group.

        Returns:
            List of peer data dicts for peers in this Matrix group.
        """
        tag = f"tag:matrix-{matrix_group_id}"
        return await self.get_peers(tag_filter=tag)

    async def get_matrix_peer_service_urls(
        self, matrix_group_id: str, service_port: int
    ) -> list[str]:
        """Get service URLs for all peers in a Matrix group.

        For use by ppl-meta-matrix (future) to discover member installations'
        service endpoints via their VPN IPs.

        Args:
            matrix_group_id: UUID of the Matrix group.
            service_port: Port of the service to connect to.

        Returns:
            List of HTTP URLs (e.g., "http://100.64.1.3:8000").
        """
        peers = await self.get_matrix_peers(matrix_group_id)
        urls = []
        for peer in peers:
            ips = peer.get("TailscaleIPs", [])
            if ips:
                urls.append(f"http://{ips[0]}:{service_port}")
        return urls

    async def get_peer_by_ip(self, ip_address: str) -> Optional[dict]:
        """Look up a specific peer by their Tailscale IP.

        Args:
            ip_address: The Tailscale IP to look up.

        Returns:
            Peer data dict, or None if not found.
        """
        result = await self._run_tailscale_json(["status", "--json"])
        if not result:
            return None

        peers = result.get("Peer", {})
        for peer_id, peer_data in peers.items():
            if ip_address in peer_data.get("TailscaleIPs", []):
                return peer_data

        return None

    async def get_status(self) -> dict:
        """Get VPN connection status — dynamically checks tailscale on every call.

        Returns:
            Dict with enrollment state, IP, peer count, and connectivity info.
        """
        available = False
        has_tailscale_installed = bool(self.tailscale_binary)
        enrolled = False
        tailscale_ip = None
        vpn_ips = []
        peer_count = 0
        online_count = 0
        matrix_peers = []
        current_server = None
        headscale_server = self._headscale_server
        hostname = None

        if has_tailscale_installed:
            result = await self._run_tailscale_json(["status", "--json"])
            if result:
                available = True
                self_data = result.get("Self", {})
                current_server = self._resolve_server_from_status(self_data)
                tailscale_ip = (self_data.get("TailscaleIPs") or [None])[0]
                if tailscale_ip:
                    enrolled = True
                vpn_ips = list(self_data.get("TailscaleIPs") or [])
                # Read local hostname but prefer canonical from headscale via authority
                hostname = self_data.get("HostName", "")

                # Try to resolve canonical hostname from authority API
                if tailscale_ip:
                    try:
                        resolved = await self._resolve_hostname_from_authority(tailscale_ip)
                        if resolved:
                            hostname = resolved
                    except Exception:
                        pass

                peers = result.get("Peer") or {}
                all_peers = list(peers.values())
                peer_count = len(all_peers)
                online_count = sum(1 for p in all_peers if p.get("Online"))
                matrix_peers = all_peers

        if enrolled and not self.enrolled:
            self.enrolled = True
            self.tailscale_ip = tailscale_ip

        return {
            "enrolled": enrolled,
            "available": available,
            "has_tailscale_installed": has_tailscale_installed,
            "tailscale_ip": tailscale_ip,
            "vpn_ips": vpn_ips,
            "online": enrolled,
            "current_server": current_server,
            "expected_server": "https://vpn.eyenet-vision.com",
            "headscale_server": headscale_server or "https://vpn.eyenet-vision.com",
            "matrix_group_id": os.environ.get("EYENET_MATRIX_GROUP_ID", ""),
            "hostname": hostname,
            "peer_count": peer_count,
            "online_count": online_count,
            "peers_count": peer_count,
            "matrix_peers": [
                {
                    "ip": p.get("TailscaleIPs", [None])[0],
                    "hostname": p.get("HostName", ""),
                    "online": p.get("Online", False),
                    "tags": p.get("Tags", []),
                }
                for p in matrix_peers[:20]
            ],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _run_tailscale_command(self, args: list[str]) -> bool:
        """Run an arbitrary tailscale command (e.g., logout, up, down).

        Returns:
            True if command succeeded (exit 0), False otherwise.
        """
        try:
            cmd = [self.tailscale_binary] + args
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=TAILSCALE_STATUS_TIMEOUT)
            return proc.returncode == 0
        except Exception as exc:
            logger.warning("tailscale %s failed: %s", " ".join(args), exc)
            return False

    def _resolve_server_from_status(self, self_data: dict) -> Optional[str]:
        """Extract the coordination server URL from tailscale status data."""
        try:
            backend_state = self_data.get("BackendState", "")
            if "https://" in backend_state:
                return backend_state.split("https://")[1].split()[0].rstrip("/")
        except Exception:
            pass
        return None

    async def set_hostname(self, new_hostname: str) -> dict:
        """Change the node's Tailscale hostname (MagicDNS name).

        Runs `tailscale up --hostname=<new>` which preserves the existing
        IP address and WireGuard identity while updating the DNS name.

        Args:
            new_hostname: New hostname (alphanumeric, dashes, max 63 chars).

        Returns:
            Dict with success, old_hostname, new_hostname, and vpn_ip.
        """
        # Check if Tailscale is actually running and enrolled
        result = await self._run_tailscale_json(["status", "--json"])
        if not result:
            raise RuntimeError(
                "Tailscale is not running. Install and enroll the node first."
            )

        self_data = result.get("Self", {})
        tailscale_ips = self_data.get("TailscaleIPs", [])
        if not tailscale_ips:
            raise RuntimeError(
                "Node is not enrolled in the VPN mesh. Enroll first, then change hostname."
            )

        old_hostname = self_data.get("HostName", "unknown")

        # Validate hostname
        sanitized = "".join(c for c in new_hostname if c.isalnum() or c == "-")
        if not sanitized or len(sanitized) > 63:
            raise ValueError(
                "Hostname must be 1-63 alphanumeric characters or dashes"
            )

        # Run tailscale up with new hostname (preserve existing DNS/routes)
        cmd = [
            self.tailscale_binary, "up",
            "--hostname", sanitized,
            "--accept-routes=false",
            "--accept-dns=false",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=TAILSCALE_UP_TIMEOUT,
        )

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            raise RuntimeError(f"tailscale up failed (exit {proc.returncode}): {error_msg}")

        logger.info(
            "Hostname changed: %s → %s", old_hostname, sanitized,
        )

        return {
            "success": True,
            "old_hostname": old_hostname,
            "new_hostname": sanitized,
            "vpn_ip": self.tailscale_ip,
        }

    async def disconnect(self) -> dict:
        """Disconnect Tailscale without losing identity."""
        success = await self._run_tailscale_command(["down"])
        self.enrolled = False
        self.tailscale_ip = None
        if not success:
            raise RuntimeError("tailscale down failed")
        return {"status": "disconnected", "previous_ip": self.tailscale_ip}

    async def connect(self, hostname: str | None = None) -> dict:
        """Reconnect Tailscale with existing identity."""
        cmd = [self.tailscale_binary, "up"]
        if hostname:
            cmd.extend(["--hostname", hostname])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=TAILSCALE_UP_TIMEOUT,
        )
        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            raise RuntimeError(f"tailscale up failed: {error_msg}")
        self.tailscale_ip = await self._get_tailscale_ip_async()
        self.enrolled = bool(self.tailscale_ip)
        return {"status": "connected", "tailscale_ip": self.tailscale_ip}

    async def _resolve_hostname_from_authority(self, host_ip: str) -> Optional[str]:
        """Try to resolve canonical hostname from authority API.

        Looks up the node by IP in headscale's database via the authority.
        Returns the canonical hostname if found, None otherwise.
        """
        authority_url = os.environ.get(
            "AUTHORITY_BASE_URL",
            os.environ.get("AUTHORITY_SERVICE_URL", ""),
        )
        if not authority_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{authority_url.rstrip('/')}/api/v1/vpn/nodes",
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                for node in data.get("nodes", []):
                    if node.get("tailscale_ip") == host_ip:
                        return node.get("hostname", "")
        except Exception:
            pass
        return None

    async def get_tailscale_tags(self) -> list[str]:
        """Get the local node's Tailscale ACL tags.

        Returns:
            List of tag strings (e.g., ["tag:installation", "tag:matrix-abc123"]).
        """
        result = await self._run_tailscale_json(["status", "--json"])
        if not result:
            return []

        self_data = result.get("Self", {})
        return self_data.get("Tags", [])


# Global instance — initialized by node's main.py lifespan
mesh_vpn_service = MeshVPNService()