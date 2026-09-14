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
from src.services.vpn_service import _get_local_ip, _get_tailscale_ip

logger = logging.getLogger(__name__)

# Existing control-plane routes live under /node/vpn (frontend / ops).
router = APIRouter(prefix="/node/vpn", tags=["vpn"])

# Leaf-facing Variant A endpoint: GET /api/v1/vpn/local-ip
leaf_router = APIRouter(prefix="/api/v1/vpn", tags=["vpn"])


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
    # Role/type tag valve node enrolls as ``tag:<node_type>``. The platform
    # compute module (this node) self-registers as ``tag:platform`` (Phase 3).
    node_type: str = "platform"  # "platform" for the compute module, "client" for cameras/apps


@router.post("/enroll")
async def vpn_enroll(payload: EnrollRequest = EnrollRequest()):
    """Mint an EyeNet pre-auth key and enroll this platform as tag:platform.

    Never logs out an existing Tailscale.app / Tailscale.com session. If this
    daemon is already on another coordination server, the key is returned with
    a userspace second-daemon command instead of running `tailscale up`.
    """
    installation_uuid = (
        os.environ.get("EYENET_INSTALLATION_UUID")
        or os.environ.get("AUTHORITY_INSTALLATION_UUID")
        or os.environ.get("INSTALLATION_UUID")
        or settings.AUTHORITY_INSTALLATION_UUID
    )
    application_key = (
        os.environ.get("EYENET_APPLICATION_KEY")
        or os.environ.get("AUTHORITY_APPLICATION_KEY")
        or os.environ.get("APPLICATION_KEY")
        or settings.AUTHORITY_APPLICATION_KEY
    )
    authority_url = (
        os.environ.get("AUTHORITY_BASE_URL")
        or os.environ.get("AUTHORITY_SERVICE_URL")
        or os.environ.get("AUTHORITY_URL")
        or settings.AUTHORITY_SERVICE_URL
    )

    if not installation_uuid or not application_key:
        raise HTTPException(
            status_code=400,
            detail="Installation UUID and application key must be configured "
                    "(set EYENET_INSTALLATION_UUID and EYENET_APPLICATION_KEY env vars)",
        )

    node_type = (payload.node_type or "platform").lower()
    if node_type in ("node", ""):
        node_type = "platform"

    safe_to_auto_enroll, skip_reason = await mesh_vpn_service.can_safely_auto_enroll()

    # Fetch key from authority
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{authority_url.rstrip('/')}/api/v1/vpn/enroll-installation",
                json={
                    "installation_uuid": installation_uuid,
                    "application_key": application_key,
                    "node_type": node_type,
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

    # Derive hostname from installation identity for unique MagicDNS
    hostname = os.environ.get("EYENET_VPN_HOSTNAME", f"eyenet-{installation_uuid[:20]}")
    sanitized_hostname = "".join(c for c in hostname if c.isalnum() or c == "-").rstrip("-")[:63]
    magic_dns = f"{sanitized_hostname}.eyenet-vpn.local"
    discovery_url = f"http://{magic_dns}:8002"

    userspace_command = mesh_vpn_service.build_userspace_enroll_command(
        auth_key, headscale_server, sanitized_hostname
    )
    inplace_command = (
        f"tailscale up --login-server {headscale_server} "
        f"--auth-key {auth_key} --hostname {sanitized_hostname} "
        "--accept-routes=false --accept-dns=false"
    )

    enrolled = False
    assigned_ip = None
    auto_enroll_skipped = not safe_to_auto_enroll
    message = skip_reason or ""

    if safe_to_auto_enroll:
        mesh_vpn_service._headscale_server = headscale_server
        try:
            success = await mesh_vpn_service._run_tailscale_up(
                auth_key, sanitized_hostname
            )
            if success:
                post = await mesh_vpn_service.get_status()
                if post.get("enrolled") and post.get("tailscale_ip"):
                    assigned_ip = post["tailscale_ip"]
                    mesh_vpn_service.enrolled = True
                    mesh_vpn_service.tailscale_ip = assigned_ip
                    enrolled = True
                    logger.info("VPN enrollment succeeded: %s", assigned_ip)
                else:
                    auto_enroll_skipped = True
                    current = post.get("current_server")
                    message = (
                        f"tailscale up did not land on EyeNet (now on {current})"
                        if current
                        else "tailscale up did not assign an EyeNet IP"
                    )
        except Exception as exc:
            logger.warning("tailscale up failed: %s", exc)
            message = f"Automatic tailscale up failed: {exc}"
            auto_enroll_skipped = True
    else:
        logger.warning("Skipping in-place tailscale up: %s", skip_reason)

    tailscale_up_command = userspace_command if auto_enroll_skipped else inplace_command

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
        "auto_enroll_skipped": auto_enroll_skipped,
        "message": message,
        "node_type": node_type,
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



@leaf_router.get("/local-ip")
async def platform_local_ip():
    """Return this platform's current local LAN IP and mesh IP (Variant A).

    Leaf devices call this over the VPN mesh when their cached
    ``platform_local_ip`` is missing or unreachable, so they can refresh the
    LAN address without re-enrolling. No auth required — the mesh ACL already
    restricts who can reach the platform node.
    """
    local_ip = _get_local_ip()
    tailscale_ip = _get_tailscale_ip()
    if not local_ip and not tailscale_ip:
        raise HTTPException(
            status_code=503,
            detail="Could not detect platform local or mesh IP",
        )
    return {
        "platform_local_ip": local_ip or None,
        "platform_tailscale_ip": tailscale_ip or None,
    }
