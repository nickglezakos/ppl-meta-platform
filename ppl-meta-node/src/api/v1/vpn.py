"""Node VPN status endpoint.

Exposes Tailscale enrollment state, peer list, and Matrix group
connectivity information consumed by the frontend and discovery service.
"""

import logging

from fastapi import APIRouter, HTTPException

from src.services.mesh_vpn_service import mesh_vpn_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/node/vpn", tags=["vpn"])


@router.get("/status")
async def vpn_status():
    """Get the node's VPN enrollment status and peer connectivity.

    Returns:
        Dict with enrollment state, Tailscale IP, peer count,
        matrix peer list, and server info.
    """
    try:
        status = await mesh_vpn_service.get_status()
    except Exception as exc:
        logger.error("Failed to get VPN status: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"VPN status unavailable: {exc}",
        )

    return status


@router.get("/peers")
async def vpn_peers():
    """Get all VPN peers visible to this node.

    Returns:
        List of peer info dicts with IP, hostname, online status, and tags.
    """
    try:
        peers = await mesh_vpn_service.get_peers()
    except Exception as exc:
        logger.error("Failed to get VPN peers: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"VPN peer list unavailable: {exc}",
        )

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
    """Get the local node's Tailscale ACL tags.

    Returns:
        List of tag strings (e.g., ["tag:installation", "tag:matrix-abc123"]).
    """
    try:
        tags = await mesh_vpn_service.get_tailscale_tags()
    except Exception as exc:
        logger.error("Failed to get VPN tags: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"VPN tag lookup failed: {exc}",
        )

    return {"tags": tags, "count": len(tags)}


@router.get("/matrix-peers/{matrix_group_id}")
async def vpn_matrix_peers(matrix_group_id: str):
    """Get all VPN peers in a specific Matrix group.

    Phase 6: Matrix-ready peer discovery endpoint.
    Returns member installations' Tailscale IPs and service URLs
    for consumption by the future ppl-meta-matrix service.

    Args:
        matrix_group_id: UUID of the Matrix group.

    Returns:
        Dict with peers list, service URLs, and group info.
    """
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
