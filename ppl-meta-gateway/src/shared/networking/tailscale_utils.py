"""Gateway service Tailscale utilities.

Minimal copy used by the gateway (which ships a local ``src/shared`` package)
to detect this host's Tailscale mesh IP during service discovery registration,
so remote VPN clients can resolve the gateway to a reachable address.
"""

import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _tailscale_cmd(args: list[str]) -> list[str]:
    ts_socket = os.environ.get("TS_SOCKET", "")
    if ts_socket:
        return ["tailscale", "--socket", ts_socket] + args
    return ["tailscale"] + args


def get_tailscale_ip() -> Optional[str]:
    """Return this host's first Tailscale (100.64.x.x) IP, if enrolled."""
    try:
        result = subprocess.run(
            _tailscale_cmd(["status", "--json"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.debug("tailscale status returned non-zero: %s", result.returncode)
            return None

        data = json.loads(result.stdout)
        ips = (data.get("Self", {}) or {}).get("TailscaleIPs", [])
        return ips[0] if ips else None

    except Exception as exc:
        logger.warning("Unexpected error getting tailscale IP: %s", exc)
        return None