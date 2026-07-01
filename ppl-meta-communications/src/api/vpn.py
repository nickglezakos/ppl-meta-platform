"""VPN status endpoint for the Communications Service.

Phase 3: Exposes Tailscale connectivity state for monitoring.
"""

import json
import logging
import subprocess
from typing import Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vpn", tags=["vpn"])


def _get_tailscale_status() -> Optional[dict]:
    """Get the raw Tailscale status as a dict."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except FileNotFoundError:
        logger.debug("tailscale binary not found")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("tailscale status timed out")
        return None
    except Exception as exc:
        logger.warning("Failed to get tailscale status: %s", exc)
        return None


@router.get("/status")
async def vpn_status():
    """Get VPN connection status for the communications service.

    Returns:
        Dict with tailscale IP, peer count, DERP relay status,
        and overall mesh health.
    """
    data = _get_tailscale_status()

    if data is None:
        # Tailscale not running or not enrolled
        return {
            "tailscale_ip": None,
            "connected_peers": 0,
            "derp_relay": "disconnected",
            "mesh_online": False,
            "enrolled": False,
        }

    self_data = data.get("Self", {})
    peers = data.get("Peer", {})
    tailscale_ip = (
        self_data.get("TailscaleIPs", [None])[0]
        if self_data.get("TailscaleIPs") else None
    )

    # Check if any peer uses DERP relay
    derp_relay = "disconnected"
    for peer in peers.values():
        if peer.get("Relay") == "derp":
            derp_relay = "connected"
            break

    return {
        "tailscale_ip": tailscale_ip,
        "enrolled": bool(tailscale_ip),
        "connected_peers": len(peers),
        "derp_relay": derp_relay,
        "mesh_online": bool(tailscale_ip),
        "tags": self_data.get("Tags", []),
    }


@router.get("/health")
async def vpn_health():
    """Quick health check for VPN connectivity.

    Returns 200 if the service can query Tailscale, even if not enrolled.
    Returns 503 if tailscale binary is not found or status query fails.
    """
    data = _get_tailscale_status()
    if data is not None:
        return {"vpn_healthy": True, "enrolled": bool(
            data.get("Self", {}).get("TailscaleIPs")
        )}

    raise HTTPException(
        status_code=503,
        detail="VPN status unavailable — tailscale not running or not installed",
    )