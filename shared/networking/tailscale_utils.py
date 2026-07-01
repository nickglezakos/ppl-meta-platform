"""Shared Tailscale utilities for all EyeNet platform services.

Provides VPN IP detection and peer lookup via the local tailscale daemon.
All services use this module to detect their Tailscale IP and discover peers.
"""

import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

TAILSCALE_CGNAT = "100.64.0.0/10"


def _tailscale_cmd(args: list[str]) -> list[str]:
    """Build a tailscale command, respecting TS_SOCKET if set."""
    ts_socket = os.environ.get("TS_SOCKET", "")
    if ts_socket:
        return ["tailscale", "--socket", ts_socket] + args
    return ["tailscale"] + args


def get_tailscale_ip() -> Optional[str]:
    """Get the local machine's Tailscale IP by querying the tailscale daemon.

    Returns:
        The first Tailscale IP (100.64.x.x) if enrolled, None otherwise.
    """
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
        self_data = data.get("Self", {})
        ips = self_data.get("TailscaleIPs", [])
        if ips:
            return ips[0]

        logger.debug("No Tailscale IPs found in status output")
        return None

    except FileNotFoundError:
        logger.debug("tailscale binary not found on PATH")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("tailscale status timed out after 5 seconds")
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse tailscale status output: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error getting tailscale IP: %s", exc)
        return None


def is_tailscale_connected() -> bool:
    """Check if this machine is connected to a Tailscale network.

    Returns:
        True if tailscale is running and has an assigned IP.
    """
    return get_tailscale_ip() is not None


def get_tailscale_peer_ips(tag: Optional[str] = None) -> list[str]:
    """Get Tailscale IPs of all peers, optionally filtered by ACL tag.

    Args:
        tag: Optional ACL tag to filter peers by (e.g., "tag:matrix-<uuid>").

    Returns:
        List of Tailscale IP strings for matching peers.
    """
    try:
        result = subprocess.run(
            _tailscale_cmd(["status", "--json"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.debug("tailscale status returned non-zero: %s", result.returncode)
            return []

        data = json.loads(result.stdout)
        peers = data.get("Peer", {})
        ips = []

        for peer_id, peer_data in peers.items():
            if tag and tag not in peer_data.get("Tags", []):
                continue
            for ip in peer_data.get("TailscaleIPs", []):
                ips.append(ip)

        return ips

    except FileNotFoundError:
        logger.debug("tailscale binary not found on PATH")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("tailscale peer lookup timed out")
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse tailscale peer data: %s", exc)
        return []
    except Exception as exc:
        logger.warning("Unexpected error getting tailscale peers: %s", exc)
        return []


def get_peer_by_ip(ip_address: str) -> Optional[dict]:
    """Look up a specific peer by their Tailscale IP.

    Args:
        ip_address: The Tailscale IP to look up.

    Returns:
        Peer data dict with keys: TailscaleIPs, Tags, HostName, Online, etc.
        Returns None if no peer found with that IP.
    """
    try:
        result = subprocess.run(
            _tailscale_cmd(["status", "--json"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        peers = data.get("Peer", {})

        for peer_id, peer_data in peers.items():
            if ip_address in peer_data.get("TailscaleIPs", []):
                return peer_data

        return None

    except Exception as exc:
        logger.warning("Failed to look up peer by IP %s: %s", ip_address, exc)
        return None


def get_tailscale_tags() -> list[str]:
    """Get the local machine's Tailscale ACL tags.

    Returns:
        List of tag strings (e.g., ["tag:installation", "tag:matrix-abc123"]).
        Empty list if not enrolled or no tags assigned.
    """
    try:
        result = subprocess.run(
            _tailscale_cmd(["status", "--json"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        self_data = data.get("Self", {})
        return self_data.get("Tags", [])

    except Exception as exc:
        logger.warning("Failed to get tailscale tags: %s", exc)
        return []