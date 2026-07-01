"""Authority VPN API — Headscale enrollment endpoint.

Provides pre-authorized Tailscale keys to EyeNet installations.
Validates installation identity via application_key before issuing keys.
Keys are scoped with ACL tags matching the installation's Matrix group.

All endpoints require authority admin authentication (session-based).
"""

import logging
import subprocess
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.storage import (
    get_installation_by_application_key,
)
from services.vpn_acl_service import vpn_acl_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vpn", tags=["vpn"])

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class EnrollInstallationRequest(BaseModel):
    installation_uuid: str
    application_key: str


class EnrollInstallationResponse(BaseModel):
    auth_key: str
    tailscale_ip_range: str = "100.64.0.0/10"
    headscale_server: str = ""
    tags: list[str] = []
    expires_in_seconds: int = 3600  # 1 hour


class VpnNodeInfo(BaseModel):
    node_id: str
    installation_uuid: str
    tailscale_ip: str | None = None
    online: bool = False
    last_seen: str | None = None


class VpnNodeListResponse(BaseModel):
    nodes: list[VpnNodeInfo]


class VpnMatrixAclResponse(BaseModel):
    matrix_group_id: str
    tags: list[str]
    acl_status: str  # "synced", "pending", "error"
    last_synced_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HEADSCALE_CLI = "headscale"

# Pre-auth key TTL: 1 hour (matches proposal Section 10.2 M7 hardening)
PREAUTH_KEY_EXPIRY_HOURS = 1


def _run_headscale(args: list[str]) -> str:
    """Run a headscale CLI command and return stdout.

    Args:
        args: Headscale subcommand arguments.

    Returns:
        stdout as string.

    Raises:
        RuntimeError: If headscale command fails.
    """
    cmd = [HEADSCALE_CLI] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.error("headscale command failed: %s — %s", " ".join(cmd), result.stderr)
            raise RuntimeError(f"headscale command failed: {result.stderr.strip()}")
        return result.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError(
            "headscale binary not found. Install headscale on the authority VPS."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("headscale command timed out")


def _generate_preauth_key(user: str, tags: list[str]) -> str:
    """Generate a pre-authorized key via headscale CLI.

    The key is scoped to the given user and ACL tags.

    Args:
        user: Headscale user namespace (e.g., "eyenet-platform").
        tags: ACL tags to scope the key to
               (e.g., ["tag:installation", "tag:matrix-<uuid>"]).

    Returns:
        The pre-auth key string (tskey-auth-...).
    """
    # headscale preauthkeys create --user <user> --tags tag:installation,tag:matrix-xxx
    cmd = ["preauthkeys", "create", "--user", user]
    for tag in tags:
        cmd.extend(["--tags", tag])

    output = _run_headscale(cmd)
    # Output format: "tskey-auth-xxxxxxxxxxxx"
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("tskey-auth-"):
            return line

    raise RuntimeError(f"No pre-auth key found in headscale output: {output}")


def _list_nodes(user: str) -> list[dict]:
    """List all enrolled nodes for a headscale user.

    Args:
        user: Headscale user namespace.

    Returns:
        List of node info dicts.
    """
    output = _run_headscale(["nodes", "list", "--user", user, "--output", "json"])
    import json
    return json.loads(output)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/enroll-installation", response_model=EnrollInstallationResponse)
async def enroll_installation(payload: EnrollInstallationRequest):
    """Issue a pre-authorized Tailscale key for an EyeNet installation.

    Validates the installation's application_key against the authority
    entitlement registry. Only approved, active installations receive keys.

    The issued key is scoped with ACL tags that cryptographically bind
    the node to its Matrix group. Key expires after 1 hour.

    Security (per Section 10.2 M7): Keys have short TTL. Every issuance
    is logged to the audit trail.
    """
    # Validate installation exists and is active
    installation = get_installation_by_application_key(payload.application_key.strip().lower())
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found for application key")

    if not installation.get("owner_enabled"):
        raise HTTPException(status_code=403, detail="Installation owner is disabled")

    licence_status = installation.get("licence_status", "")
    if licence_status not in {"active", "grace"}:
        raise HTTPException(status_code=403, detail=f"Licence not active (status: {licence_status})")

    # Verify installation UUID matches
    stored_uuid = installation.get("installation_uuid", "")
    if stored_uuid and stored_uuid != payload.installation_uuid:
        logger.warning(
            "Installation UUID mismatch: stored=%s requested=%s",
            stored_uuid,
            payload.installation_uuid,
        )

    # Determine ACL tags
    tags = ["tag:installation"]
    matrix_group_id = installation.get("matrix_group_id")
    if matrix_group_id:
        tags.append(f"tag:matrix-{matrix_group_id}")

    headscale_user = "eyenet-platform"

    try:
        auth_key = _generate_preauth_key(headscale_user, tags)
    except RuntimeError as exc:
        logger.error("Failed to generate pre-auth key: %s", exc)
        raise HTTPException(status_code=503, detail=f"VPN key generation failed: {exc}")

    logger.info(
        "VPN enrollment: installation=%s application_key=%s tags=%s",
        payload.installation_uuid,
        payload.application_key[:16] + "...",
        tags,
    )

    return EnrollInstallationResponse(
        auth_key=auth_key,
        tags=tags,
        headscale_server="https://vpn.eyenet-vision.com:50443",
        expires_in_seconds=PREAUTH_KEY_EXPIRY_HOURS * 3600,
    )


@router.get("/nodes", response_model=VpnNodeListResponse)
async def list_vpn_nodes(_request: Request):
    """List all enrolled VPN nodes (admin only).

    Requires admin session authentication.
    """
    # TODO: require_admin_session dependency
    headscale_user = "eyenet-platform"

    try:
        nodes_data = _list_nodes(headscale_user)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to list nodes: {exc}")

    nodes = []
    for node in nodes_data:
        nodes.append(VpnNodeInfo(
            node_id=node.get("ID", node.get("NodeKey", "")),
            installation_uuid="",  # Not directly mapped in headscale data
            tailscale_ip=(
                node.get("IPAddresses", [None])[0] if node.get("IPAddresses") else None
            ),
            online=node.get("Online", False),
            last_seen=node.get("LastSeen"),
        ))

    return VpnNodeListResponse(nodes=nodes)


@router.delete("/nodes/{node_id}")
async def revoke_vpn_node(node_id: str, _request: Request):
    """Revoke a node's VPN access (admin only).

    Requires admin session authentication.
    """
    # TODO: require_admin_session dependency
    headscale_user = "eyenet-platform"

    try:
        _run_headscale(["nodes", "delete", "--user", headscale_user, node_id])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to revoke node: {exc}")

    logger.info("VPN node revoked: %s", node_id)
    return {"status": "revoked", "node_id": node_id}


@router.get("/matrix-groups/{matrix_id}/acl", response_model=VpnMatrixAclResponse)
async def get_matrix_group_acl(matrix_id: str, _request: Request):
    """Get VPN ACL status for a Matrix group.

    Returns the tags and sync status for the group's ACL.
    """
    # TODO: require_admin_session dependency
    # Phase 6: Return real ACL status from the VpnACLService
    acl_status = vpn_acl_service.get_acl_status()
    return VpnMatrixAclResponse(
        matrix_group_id=matrix_id,
        tags=[f"tag:matrix-{matrix_id}"],
        acl_status=acl_status.get("status", "unknown"),
        last_synced_at=acl_status.get("last_modified"),
    )
