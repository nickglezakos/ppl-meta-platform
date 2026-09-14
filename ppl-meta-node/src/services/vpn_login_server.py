"""EyeNet vs foreign Tailscale coordination-server helpers.

A 100.64.x.x address is not enough: the operator Mac often has Tailscale.app
logged into Tailscale.com (lab / Windows mesh) while EyeNet uses Headscale at
https://vpn.eyenet-vision.com. In-place `tailscale logout` / `tailscale up`
would drop that operator mesh.
"""

from __future__ import annotations

import os
from typing import Any, Optional

EYENET_HEADSCALE_DEFAULT = "https://vpn.eyenet-vision.com"


def expected_headscale_url() -> str:
    return (
        os.environ.get("EYENET_HEADSCALE_URL") or EYENET_HEADSCALE_DEFAULT
    ).strip().rstrip("/")


def normalize_login_server(url: str) -> str:
    return url.strip().rstrip("/").lower()


def is_eyenet_login_server(url: Optional[str]) -> bool:
    if not url:
        return False
    actual = normalize_login_server(url)
    expected = normalize_login_server(expected_headscale_url())
    return actual == expected or "vpn.eyenet-vision.com" in actual


def extract_control_url(
    prefs: Optional[dict[str, Any]] = None,
    status: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Best-effort ControlURL from `tailscale debug prefs` and/or status JSON."""
    if prefs:
        url = prefs.get("ControlURL") or prefs.get("controlURL")
        if url:
            return str(url).strip().rstrip("/")

    if not status:
        return None

    url = status.get("ControlURL")
    if url:
        return str(url).strip().rstrip("/")

    tailnet = status.get("CurrentTailnet") or {}
    if isinstance(tailnet, dict):
        magic = str(tailnet.get("MagicDNSSuffix") or "")
        name = str(tailnet.get("Name") or "")
        combined = f"{magic} {name}".lower()
        if "eyenet" in combined:
            return expected_headscale_url()
        if "tailscale.com" in combined or ".ts.net" in magic.lower() or magic.lower().endswith("ts.net"):
            return "https://controlplane.tailscale.com"

    self_data = status.get("Self") or {}
    dns = str(self_data.get("DNSName") or "")
    hostname = str(self_data.get("HostName") or "")
    if "eyenet" in dns.lower() or "eyenet" in hostname.lower():
        return expected_headscale_url()

    return None


def userspace_enroll_command(
    auth_key: str,
    headscale_server: str,
    hostname: str,
) -> str:
    """Command block that joins EyeNet without logging out Tailscale.app."""
    server = (headscale_server or expected_headscale_url()).rstrip("/")
    safe_host = "".join(c for c in hostname if c.isalnum() or c == "-").rstrip("-")[:63] or "eyenet-node"
    return (
        "# Keep Tailscale.app on its current mesh (lab / Windows access).\n"
        "# Do not run tailscale logout.\n"
        'mkdir -p "$HOME/.eyenet-tailscale"\n'
        "tailscaled --tun=userspace-networking \\\n"
        '  --socket="$HOME/.eyenet-tailscale/tailscaled.sock" \\\n'
        '  --statedir="$HOME/.eyenet-tailscale" &\n'
        f'TS_SOCKET="$HOME/.eyenet-tailscale/tailscaled.sock" tailscale up \\\n'
        f"  --login-server {server} \\\n"
        f"  --auth-key {auth_key} \\\n"
        f"  --hostname {safe_host} \\\n"
        "  --accept-routes=false --accept-dns=false\n"
        "# Point this Node at that daemon and restart:\n"
        'export EYENET_TS_SOCKET="$HOME/.eyenet-tailscale/tailscaled.sock"'
    )
