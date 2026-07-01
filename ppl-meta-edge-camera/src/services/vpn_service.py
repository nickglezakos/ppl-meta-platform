"""VPN enrollment service for edge cameras.

Phase 4: Tailscale auto-enrollment.
On boot, the edge camera fetches a pre-auth key from the authority VPS
(if vpn.enabled) and enrolls in the Tailscale mesh. The Tailscale IP
becomes the camera's primary platform address.

Zero EyeNet credentials — the application_key from config is the sole
provisioning input. Tailscale ACL tags cryptographically bind the camera
to its Matrix group.
"""

import asyncio
import json
import logging
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

TAILSCALE_UP_TIMEOUT = 30


class EdgeCameraVPNService:
    """VPN enrollment for edge cameras.

    On startup:
    1. Fetch pre-auth key from authority
    2. Run tailscale up --authkey=...
    3. Cache the assigned Tailscale IP for streaming and registration
    """

    def __init__(self, config):
        self.config = config
        self.tailscale_ip: Optional[str] = None
        self.tailscale_binary: str = self._find_tailscale()

    def _find_tailscale(self) -> str:
        """Find the tailscale binary on PATH."""
        path = shutil.which("tailscale")
        if not path:
            raise RuntimeError(
                "tailscale not found. Install: curl -fsSL https://tailscale.com/install.sh | sh"
            )
        return path

    async def enroll(
        self,
        authority_url: str,
        application_key: str,
        hostname: str = "eyenet-edge-camera",
    ) -> bool:
        """Enroll this edge camera in the VPN mesh.

        Args:
            authority_url: Base URL of the authority service.
            application_key: The installation's application key.
            hostname: Hostname for this camera in the mesh.

        Returns:
            True if enrollment succeeded, False otherwise.
        """
        if not application_key:
            logger.warning("No application_key configured — skipping VPN enrollment")
            return False

        logger.info("Enrolling edge camera in VPN mesh: hostname=%s", hostname)

        # 1. Fetch pre-auth key from authority
        auth_key = await self._fetch_auth_key(authority_url, application_key)
        if not auth_key:
            logger.error("Failed to fetch pre-auth key from authority")
            return False

        # 2. Bring up tailscale
        success = await self._run_tailscale_up(auth_key, hostname)
        if not success:
            logger.error("Failed to bring up tailscale")
            return False

        # 3. Fetch assigned IP
        self.tailscale_ip = await self._get_tailscale_ip()
        if not self.tailscale_ip:
            logger.error("Failed to get Tailscale IP after enrollment")
            return False

        logger.info("Edge camera enrolled in VPN mesh: %s", self.tailscale_ip)
        return True

    async def _fetch_auth_key(
        self, authority_url: str, application_key: str
    ) -> Optional[str]:
        """Fetch a pre-authorized key from the authority VPN API."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{authority_url}/api/v1/vpn/enroll-installation",
                    json={
                        "installation_uuid": self.config.device.id or "edge-camera",
                        "application_key": application_key,
                    },
                )
            if response.status_code != 200:
                logger.error(
                    "Authority VPN enrollment failed: HTTP %s", response.status_code
                )
                return None
            data = response.json()
            auth_key = data.get("auth_key")
            if auth_key:
                logger.info("Received pre-auth key from authority")
            return auth_key
        except Exception as exc:
            logger.error("Failed to fetch auth key: %s", exc)
            return None

    async def _run_tailscale_up(self, auth_key: str, hostname: str) -> bool:
        """Run tailscale up with the provided auth key."""
        cmd = [
            self.tailscale_binary,
            "up",
            "--authkey", auth_key,
            "--hostname", hostname,
            "--accept-routes=false",
            "--accept-dns=false",
        ]
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
                    stderr.decode() if stderr else "",
                )
                return False
            logger.info("tailscale up succeeded")
            return True
        except asyncio.TimeoutError:
            logger.error("tailscale up timed out")
            return False
        except Exception as exc:
            logger.error("tailscale up failed: %s", exc)
            return False

    async def _get_tailscale_ip(self) -> Optional[str]:
        """Get the assigned Tailscale IP."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.tailscale_binary, "status", "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=5
            )
            if proc.returncode == 0:
                data = json.loads(stdout.decode())
                ips = data.get("Self", {}).get("TailscaleIPs", [])
                return ips[0] if ips else None
        except Exception as exc:
            logger.error("Failed to get tailscale IP: %s", exc)
        return None

    def get_tailscale_ip(self) -> Optional[str]:
        """Get cached Tailscale IP."""
        return self.tailscale_ip