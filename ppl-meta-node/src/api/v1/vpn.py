"""Node VPN status endpoint.

Exposes Tailscale enrollment state, peer list, and Matrix group
connectivity information consumed by the frontend and discovery service.
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException

from src.config import settings
from src.services.mesh_vpn_service import mesh_vpn_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/node/vpn", tags=["vpn"])


@router.get("/status")
async def vpn_status():
    """Get the node's VPN enrollment status and peer connectivity."""
    try:
        status = await mesh_vpn_service.get_status()
    except Exception as exc:
        logger.error("Failed to get VPN status: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"VPN status unavailable: {exc}",
        )
    return status


from pydantic import BaseModel, Field


class HostnameRequest(BaseModel):
    hostname: str = Field(
        ..., min_length=1, max_length=63,
        pattern=r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$',
        description="New MagicDNS hostname (alphanumeric, dashes, max 63 chars)",
    )


@router.post("/disconnect")
async def vpn_disconnect():
    """Disconnect Tailscale without losing identity. Can reconnect later."""
    try:
        result = await mesh_vpn_service.disconnect()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to disconnect: %s", exc)
        raise HTTPException(status_code=503, detail=f"Disconnect failed: {exc}")
    return result


@router.post("/connect")
async def vpn_connect():
    """Reconnect Tailscale with existing identity."""
    try:
        result = await mesh_vpn_service.connect()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to connect: %s", exc)
        raise HTTPException(status_code=503, detail=f"Connect failed: {exc}")
    return result


@router.patch("/hostname")
async def vpn_hostname(request: HostnameRequest):
    """Change the node's Tailscale hostname (MagicDNS name).

    Preserves the existing VPN IP and WireGuard identity.
    """
    try:
        result = await mesh_vpn_service.set_hostname(request.hostname)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to set hostname: %s", exc)
        raise HTTPException(status_code=503, detail=f"Hostname update failed: {exc}")

    return result


@router.get("/peers")
async def vpn_peers():
    """Get all VPN peers visible to this node."""
    try:
        peers = await mesh_vpn_service.get_peers()
    except Exception as exc:
        logger.error("Failed to get VPN peers: %s", exc)
        raise HTTPException(status_code=503, detail=f"VPN peer list unavailable: {exc}")

    return {
        "peers": [
            {
                "ip": p.get("TailscaleIPs", [None])[0],
                "hostname": p.get("HostName", ""),
                "online": p.get("Online", False),
                "tags": p.get("Tags", []),
            }
            for p in peers
        ],
        "count": len(peers),
    }


@router.get("/tags")
async def vpn_tags():
    """Get the local node's Tailscale ACL tags."""
    try:
        tags = await mesh_vpn_service.get_tailscale_tags()
    except Exception as exc:
        logger.error("Failed to get VPN tags: %s", exc)
        raise HTTPException(status_code=503, detail=f"VPN tag lookup failed: {exc}")
    return {"tags": tags, "count": len(tags)}


class EnrollRequest(BaseModel):
    node_type: str = "client"  # "node" for self-enrollment, "client" for cameras/apps


@router.post("/enroll")
async def vpn_enroll(payload: EnrollRequest = EnrollRequest()):
    """Full VPN enrollment — logout from other networks, fetch key, run tailscale up.

    Returns enrollment success status, assigned IP, and matrix group ID.
    If automatic enrollment fails, returns the manual tailscale up command.
    """
    installation_uuid = os.environ.get(
        "EYENET_INSTALLATION_UUID",
        settings.AUTHORITY_INSTALLATION_UUID,
    )
    application_key = os.environ.get(
        "EYENET_APPLICATION_KEY",
        settings.AUTHORITY_APPLICATION_KEY,
    )
    authority_url = os.environ.get(
        "AUTHORITY_BASE_URL",
        settings.AUTHORITY_SERVICE_URL,
    )

    if not installation_uuid or not application_key:
        raise HTTPException(
            status_code=400,
            detail="Installation UUID and application key must be configured "
                    "(set EYENET_INSTALLATION_UUID and EYENET_APPLICATION_KEY env vars)",
        )

    # Check if connected to a different server — logout first
    try:
        status = await mesh_vpn_service.get_status()
        if status.get("connected_to_other_server") or (
            status.get("has_tailscale_installed") and not status.get("enrolled")
        ):
            await mesh_vpn_service._run_tailscale_command(["logout"])
            logger.info("Logged out from previous tailscale network")
    except Exception as exc:
        logger.warning("Could not logout from previous tailscale: %s", exc)

    # Fetch key from authority
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{authority_url.rstrip('/')}/api/v1/vpn/enroll-installation",
                json={
                    "installation_uuid": installation_uuid,
                    "application_key": application_key,
                    "node_type": payload.node_type,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Authority enrollment failed: HTTP {resp.status_code} - {resp.text}",
                )
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Authority unreachable: {e}")

    auth_key = data["auth_key"]
    headscale_server = data["headscale_server"]
    matrix_group_id = data.get("matrix_group_id")
    tailscale_up_command = f'tailscale up --login-server {headscale_server} --auth-key {auth_key} --accept-routes'

    # Derive hostname from installation identity for unique MagicDNS
    hostname = os.environ.get("EYENET_VPN_HOSTNAME", f"eyenet-{installation_uuid[:20]}")
    sanitized_hostname = "".join(c for c in hostname if c.isalnum() or c == "-").rstrip("-")[:63]
    magic_dns = f"{sanitized_hostname}.eyenet-vpn.local"
    discovery_url = f"http://{magic_dns}:8002"

    # Attempt to run tailscale up
    enrolled = False
    assigned_ip = None
    try:
        success = await mesh_vpn_service._run_tailscale_up(auth_key, sanitized_hostname)
        if success:
            assigned_ip = await mesh_vpn_service._get_tailscale_ip_async()
            if assigned_ip:
                mesh_vpn_service.enrolled = True
                mesh_vpn_service.tailscale_ip = assigned_ip
                enrolled = True
                logger.info("VPN enrollment succeeded: %s", assigned_ip)
    except Exception as exc:
        logger.warning("tailscale up failed: %s", exc)

    # Tailscale Android deep link — bypasses the hidden "custom server" menu
    deep_link = f"tailscale://login?server={headscale_server}&key={auth_key}"

    return {
        "enrolled": enrolled,
        "tailscale_ip": assigned_ip,
        "auth_key": auth_key,
        "headscale_server": headscale_server,
        "matrix_group_id": matrix_group_id,
        "tags": data.get("tags", []),
        "tailscale_up_command": tailscale_up_command,
        "deep_link": deep_link,
        "hostname": sanitized_hostname,
        "magic_dns": magic_dns,
        "discovery_url": discovery_url,
    }


@router.get("/matrix-peers/{matrix_group_id}")
async def vpn_matrix_peers(matrix_group_id: str):
    """Get all VPN peers in a specific Matrix group."""
    try:
        peers = await mesh_vpn_service.get_matrix_peers(matrix_group_id)
        node_service_urls = await mesh_vpn_service.get_matrix_peer_service_urls(
            matrix_group_id, 8000
        )
    except Exception as exc:
        logger.error("Failed to get Matrix peers: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Matrix peer discovery failed: {exc}",
        )

    return {
        "matrix_group_id": matrix_group_id,
        "peers": [
            {
                "ip": p.get("TailscaleIPs", [None])[0],
                "hostname": p.get("HostName", ""),
                "online": p.get("Online", False),
                "tags": p.get("Tags", []),
            }
            for p in peers
        ],
        "node_service_urls": node_service_urls,
        "count": len(peers),
    }