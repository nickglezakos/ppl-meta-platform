"""VPN enrollment service for EyeNet Headscale mesh.

One-time bootstrap: calls the authority VPN enrollment endpoint,
gets a headscale pre-auth key, and runs `tailscale up`.

The pre-auth key is only needed for initial enrollment. After
`tailscale up` succeeds, the WireGuard keypair is stored locally
( /var/lib/tailscale/ ) and the device remains enrolled indefinitely.
No periodic re-enrollment is required.

Requirements:
  - tailscale CLI installed on the host/Docker image
  - EYENET_INSTALLATION_UUID and EYENET_APPLICATION_KEY env vars set
  - /var/lib/tailscale volume mounted (in Docker) for key persistence
"""

import os
import subprocess
import sys
import logging

import httpx

logger = logging.getLogger(__name__)

AUTHORITY_URL = os.environ.get(
    "AUTHORITY_BASE_URL", "https://authority.eyenet-vision.com"
)
INSTALLATION_UUID = os.environ.get("EYENET_INSTALLATION_UUID", "")
APPLICATION_KEY = os.environ.get("EYENET_APPLICATION_KEY", "")

# Node role/tag this service enrolls as. The platform compute module (this service,
# ppl-meta-node) owns its DB/registry/media and participates in the mesh as a
# ``tag:platform`` node (Phase 3 platform self-registration). Override with
# ``EYENET_VPN_NODE_TYPE=client`` (or ``node`` for the legacy tag) when the peer
# action differs.
VPN_NODE_TYPE = os.environ.get("EYENET_VPN_NODE_TYPE", "platform")

# Optional: set a custom hostname for MagicDNS.
# If not set, derived from INSTALLATION_UUID (sanitized).
VPN_HOSTNAME = os.environ.get("EYENET_VPN_HOSTNAME", "")


def _derive_hostname(install_uuid: str) -> str:
    """Derive a unique MagicDNS hostname from the installation UUID."""
    sanitized = install_uuid.replace("@", "-").replace(".", "-")
    # Strip anything not alphanumeric, dash, or underscore
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in "-_")
    return sanitized if sanitized else "eyenet-node"


def _is_tailscale_installed() -> bool:
    """Check if tailscale CLI is available."""
    try:
        subprocess.run(
            ["tailscale", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _is_already_enrolled() -> bool:
    """Check if tailscale is already enrolled and connected."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        import json
        status = json.loads(result.stdout)
        # If there's a valid tailscale IP, we're already enrolled
        return bool(status.get("Self", {}).get("TailscaleIPs"))
    except Exception:
        return False


def enroll_once() -> bool:
    """One-time VPN enrollment. Safe to call on every boot — will skip if already enrolled.

    Returns:
        True if enrollment succeeded or already enrolled, False on error.
    """
    if not INSTALLATION_UUID or not APPLICATION_KEY:
        logger.warning(
            "VPN: EYENET_INSTALLATION_UUID or EYENET_APPLICATION_KEY not set — "
            "VPN mesh enrollment skipped. Set these env vars to join the EyeNet VPN."
        )
        return False

    if not _is_tailscale_installed():
        logger.warning(
            "VPN: tailscale CLI not found — VPN mesh enrollment skipped. "
            "Install tailscale on this device to join the EyeNet VPN."
        )
        return False

    if _is_already_enrolled():
        logger.info("VPN: already enrolled — skipping enrollment")
        return True

    try:
        resp = httpx.post(
            f"{AUTHORITY_URL}/api/v1/vpn/enroll-installation",
            json={
                "installation_uuid": INSTALLATION_UUID,
                "application_key": APPLICATION_KEY,
                # Phase 3: this platform node self-registers as ``tag:platform``.
                # The Authority gates platform-node counts by ``max_platform_nodes``.

                "node_type": VPN_NODE_TYPE,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        auth_key = data["auth_key"]
        headscale_server = data["headscale_server"]
        matrix_group_id = data.get("matrix_group_id", "")

        result = subprocess.run(
            [
                "tailscale", "up",
                "--login-server", headscale_server,
                "--auth-key", auth_key,
                "--accept-routes",
                "--hostname", VPN_HOSTNAME or _derive_hostname(INSTALLATION_UUID),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(
                "VPN: enrollment succeeded — matrix_group=%s headscale_server=%s",
                matrix_group_id,
                headscale_server,
            )
            return True
        else:
            logger.error(
                "VPN: tailscale up failed (exit=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return False

    except httpx.HTTPError as e:
        logger.warning("VPN: authority enrollment request failed (non-fatal): %s", e)
        return False
    except subprocess.TimeoutExpired:
        logger.warning("VPN: tailscale up timed out (non-fatal)")
        return False
    except Exception as e:
        logger.warning("VPN: enrollment failed (non-fatal): %s", e)
        return False