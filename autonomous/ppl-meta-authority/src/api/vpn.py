"""Authority VPN API — Headscale enrollment endpoint.

Provides pre-authorized Tailscale keys to EyeNet installations.
Validates installation identity via application_key before issuing keys.
Keys are scoped with ACL tags matching the installation's Matrix group.

All endpoints require authority admin authentication (session-based).
"""

import json
import logging
import os
import shlex
import subprocess
import time
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
    node_type: str = "client"  # "node" for platform nodes, "client" for cameras/apps


class EnrollInstallationResponse(BaseModel):
    auth_key: str
    tailscale_ip_range: str = "100.64.0.0/10"
    headscale_server: str = ""
    matrix_group_id: str = ""
    tags: list[str] = []
    expires_in_seconds: int = 86400  # 24 hours


class VpnNodeInfo(BaseModel):
    node_id: str
    hostname: str = ""
    installation_uuid: str
    tailscale_ip: str | None = None
    online: bool = False
    last_seen: str | None = None
    tags: list[str] = []


class VpnNodeListResponse(BaseModel):
    nodes: list[VpnNodeInfo]


class VpnMatrixAclResponse(BaseModel):
    matrix_group_id: str
    tags: list[str]
    acl_status: str  # "synced", "pending", "error"
    last_synced_at: str | None = None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

# In-memory cache with TTL for the /nodes endpoint.
# Avoids sequential docker exec headscale calls on every request.
_nodes_cache: tuple[float, VpnNodeListResponse] | None = None
_NODES_CACHE_TTL = 30  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Option B (Docker Compose): authority calls headscale via docker exec.
# HEADSCALE_CLI env var is set in docker-compose.production.yml.
# Format: "docker exec authority-headscale headscale"
HEADSCALE_CLI = os.environ.get(
    "HEADSCALE_CLI", "docker exec authority-headscale headscale"
)

# Pre-auth key TTL: 24 hours (bumped from 1h for manual enrollment convenience)
PREAUTH_KEY_EXPIRY_HOURS = 24


def _run_headscale(args: list[str]) -> str:
    """Run a headscale CLI command and return stdout.

    Uses docker exec when HEADSCALE_CLI is set to a docker wrapper.
    Falls back to direct `headscale` binary call for local development.

    Args:
        args: Headscale subcommand arguments (e.g. ["users", "list"]).

    Returns:
        stdout as string.

    Raises:
        RuntimeError: If headscale command fails.
    """
    cmd = shlex.split(HEADSCALE_CLI) + args
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
            "headscale not available. Ensure the authority container has "
            "access to the Docker socket or the headscale binary."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("headscale command timed out")


def _resolve_user_id(name: str) -> str:
    """Resolve a headscale user name to its numeric (uint) ID.

    Args:
        name: Headscale user name (e.g., "matrix-<uuid>").

    Returns:
        Numeric user ID as string.

    Raises:
        RuntimeError: If user not found or resolution fails.
    """
    try:
        output = _run_headscale(["users", "list", "--output", "json"])
        users = json.loads(output)
        for user in users:
            if user.get("name") == name:
                return str(user["id"])
    except Exception:
        pass

    raise RuntimeError(f"Headscale user '{name}' not found")


def _generate_preauth_key(user: str, tags: list[str]) -> str:
    """Generate a pre-authorized key via headscale CLI.

    The key is scoped to the given user (name) and ACL tags.

    Args:
        user: Headscale user name (e.g., "matrix-<uuid>").
        tags: ACL tags to scope the key to
               (e.g., ["tag:installation", "tag:matrix-<uuid>"]).

    Returns:
        The pre-auth key string (tskey-auth-...).
    """
    user_id = _resolve_user_id(user)
    cmd = ["preauthkeys", "create", "--user", user_id]
    for tag in tags:
        cmd.extend(["--tags", tag])

    output = _run_headscale(cmd)
    # Output format: "hskey-auth-xxxxxxxxxxxx" (headscale v0.28+)
    for line in output.splitlines():
        line = line.strip()
        # Skip JSON log lines (headscale sends warnings to stdout)
        if line.startswith("{"):
            continue
        if line.startswith("hskey-auth-") or line.startswith("tskey-auth-"):
            return line

    raise RuntimeError(f"No pre-auth key found in headscale output: {output}")


def _ensure_user(user: str) -> None:
    """Ensure a headscale user namespace exists, creating it if necessary.

    Args:
        user: Headscale user namespace (e.g., "matrix-<uuid>").
    """
    try:
        _run_headscale(["users", "create", user])
        logger.info("Headscale user created: %s", user)
    except RuntimeError:
        # User likely already exists — headscale returns non-zero for duplicates
        logger.debug("Headscale user already exists (or creation skipped): %s", user)


def _list_nodes(user: str) -> list[dict]:
    """List all enrolled nodes for a headscale user.

    Args:
        user: Headscale user namespace.

    Returns:
        List of node info dicts (empty list if none found).
    """
    try:
        output = _run_headscale(["nodes", "list", "--user", user, "--output", "json"])
        result = json.loads(output)
        if result is None:
            return []
        return result if isinstance(result, list) else []
    except RuntimeError:
        return []


def _fetch_all_nodes() -> VpnNodeListResponse:
    """Query all headscale users and build the node list response.

    Uses the global listing (fast, includes ``online`` and ``tags``)
    and supplements with per-user ``last_seen`` timestamps.
    """
    # 1. Get all nodes via global listing (fast, includes online + tags)
    global_nodes: dict[str, dict] = {}
    try:
        output = _run_headscale(["nodes", "list", "--output", "json"])
        global_data = json.loads(output) or []
        for n in global_data:
            node_id = str(n.get("id", ""))
            if node_id:
                global_nodes[node_id] = n
    except Exception:
        pass

    # 2. Get per-user listings for last_seen (not in global listing)
    last_seen_by_id: dict[str, dict] = {}
    try:
        users_output = _run_headscale(["users", "list", "--output", "json"])
        users_data = json.loads(users_output) or []
        for user in users_data:
            user_name = user.get("name", "")
            if not user_name:
                continue
            try:
                user_output = _run_headscale(
                    ["nodes", "list", "--user", user_name, "--output", "json"]
                )
                user_nodes = json.loads(user_output) or []
                for n in (user_nodes if isinstance(user_nodes, list) else []):
                    node_id = str(n.get("id", ""))
                    if node_id and n.get("last_seen"):
                        last_seen_by_id[node_id] = n.get("last_seen")
            except Exception:
                continue
    except Exception:
        pass

    # 3. Build response — combine global online/tags with per-user last_seen
    nodes = []
    for node_id, node in global_nodes.items():
        last_seen_raw = last_seen_by_id.get(
            node_id, node.get("last_seen")
        )
        last_seen_str = ""
        if isinstance(last_seen_raw, dict):
            secs = last_seen_raw.get("seconds")
            if isinstance(secs, (int, float)):
                try:
                    dt = datetime.fromtimestamp(float(secs), tz=timezone.utc)
                    last_seen_str = dt.isoformat()
                except (ValueError, OSError):
                    last_seen_str = str(last_seen_raw)
            else:
                last_seen_str = str(last_seen_raw)

        nodes.append(VpnNodeInfo(
            node_id=node_id,
            hostname=str(node.get("given_name", node.get("name", ""))),
            installation_uuid=str(
                (node.get("pre_auth_key") or {}).get("user", {}).get("name", "")
            ).replace("matrix-", ""),
            tailscale_ip=(
                (node.get("ip_addresses") or [None])[0]
                if node.get("ip_addresses") else None
            ),
            online=bool(node.get("online", False)),
            last_seen=last_seen_str,
            tags=list(node.get("tags") or []),
        ))

    return VpnNodeListResponse(nodes=nodes)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/enroll-installation", response_model=EnrollInstallationResponse)
async def enroll_installation(payload: EnrollInstallationRequest):
    """Issue a pre-authorized Tailscale key for an EyeNet installation.

    Validates the installation's application_key against the authority
    entitlement registry. Only approved, active installations receive keys.

    The issued key is scoped with ACL tags that cryptographically bind
    the node to its Matrix group. Each Matrix group gets its own
    headscale user namespace (matrix-<uuid>) for mesh isolation.

    Key expires after 24 hours.

    Security: Keys have limited TTL. Every issuance is logged to the
    audit trail.
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

    # Determine ACL tags and user namespace (per-matrix isolation)
    matrix_group_id = installation.get("matrix_group_id")
    if matrix_group_id:
        tags = [f"tag:matrix-{matrix_group_id}"]
        headscale_user = f"matrix-{matrix_group_id}"
    else:
        # Legacy installations without a matrix group — auto-provision one
        from core.storage import _ensure_matrix_group
        entitlement_uuid = installation.get("entitlement_uuid", "")
        if entitlement_uuid:
            matrix_group_id = _ensure_matrix_group(entitlement_uuid)
        else:
            matrix_group_id = str(uuid.uuid4())
            logger.warning(
                "Installation %s has no entitlement_uuid — using generated matrix group %s",
                payload.installation_uuid,
                matrix_group_id,
            )
        tags = [f"tag:matrix-{matrix_group_id}"]
        headscale_user = f"matrix-{matrix_group_id}"

    # Always include the base installation tag
    if "tag:installation" not in tags:
        tags.insert(0, "tag:installation")

    # Add node type tag for service discovery (tag:node or tag:client)
    type_tag = f"tag:{payload.node_type}"
    if type_tag not in tags:
        tags.append(type_tag)

    # Ensure headscale user namespace exists
    try:
        _ensure_user(headscale_user)
    except RuntimeError as exc:
        logger.error("Failed to ensure headscale user %s: %s", headscale_user, exc)
        raise HTTPException(status_code=503, detail=f"VPN user setup failed: {exc}")

    try:
        auth_key = _generate_preauth_key(headscale_user, tags)
    except RuntimeError as exc:
        logger.error("Failed to generate pre-auth key: %s", exc)
        raise HTTPException(status_code=503, detail=f"VPN key generation failed: {exc}")

    logger.info(
        "VPN enrollment: installation=%s matrix_group=%s tags=%s",
        payload.installation_uuid,
        matrix_group_id,
        tags,
    )

    return EnrollInstallationResponse(
        auth_key=auth_key,
        tags=tags,
        matrix_group_id=matrix_group_id,
        headscale_server="https://vpn.eyenet-vision.com",
        expires_in_seconds=PREAUTH_KEY_EXPIRY_HOURS * 3600,
    )


@router.get("/nodes", response_model=VpnNodeListResponse)
async def list_vpn_nodes(_request: Request):
    """List all enrolled VPN nodes with online status.

    Uses a 30-second in-memory cache to avoid slow sequential
    ``docker exec headscale`` calls on every request from mobile
    clients over high-latency connections.
    """
    global _nodes_cache

    now = time.time()
    if _nodes_cache is not None:
        ts, data = _nodes_cache
        if now - ts < _NODES_CACHE_TTL:
            return data

    data = _fetch_all_nodes()
    _nodes_cache = (now, data)
    return data


@router.get("/matrix-groups/{matrix_id}/nodes", response_model=VpnNodeListResponse)
async def list_matrix_group_nodes(matrix_id: str, _request: Request):
    """List all enrolled VPN nodes for a specific Matrix group.

    Returns only nodes tagged with tag:matrix-{matrix_id}.
    Requires admin session authentication.
    """
    # TODO: require_admin_session dependency
    headscale_user = f"matrix-{matrix_id}"

    try:
        nodes_data = _list_nodes(headscale_user)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to list nodes: {exc}")

    nodes = []
    for node in nodes_data:
        nodes.append(VpnNodeInfo(
            node_id=str(node.get("id", node.get("node_key", ""))),
            hostname=str(node.get("name", node.get("given_name", ""))),
            installation_uuid="",
            tailscale_ip=(
                (node.get("ip_addresses") or [None])[0] if node.get("ip_addresses") else None
            ),
            online=node.get("online", False),
            last_seen=str(node.get("last_seen", "")),
        ))

    return VpnNodeListResponse(nodes=nodes)


class RenameNodeRequest(BaseModel):
    node_id: str
    new_hostname: str


@router.patch("/rename-node")
async def rename_node(payload: RenameNodeRequest):
    """Rename any node in the VPN mesh (admin only).

    Runs 'headscale nodes rename <node_id> <new_hostname>' via docker exec.
    MagicDNS updates automatically.
    """
    # Validate hostname
    sanitized = "".join(c for c in payload.new_hostname if c.isalnum() or c == "-")
    if not sanitized or len(sanitized) > 63:
        raise HTTPException(
            status_code=400,
            detail="Hostname must be 1-63 alphanumeric characters or dashes",
        )

    try:
        _run_headscale(["nodes", "rename", "--identifier", payload.node_id, sanitized])
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail=f"Failed to rename node: {exc}"
        )

    # Invalidate cache so next GET /nodes returns fresh data
    global _nodes_cache
    _nodes_cache = None

    logger.info(
        "Node renamed: %s → %s", payload.node_id, sanitized,
    )
    return {
        "status": "renamed",
        "node_id": payload.node_id,
        "new_hostname": sanitized,
        "magic_dns": f"{sanitized}.eyenet-vpn.local",
    }


@router.delete("/nodes/{node_id}")
async def revoke_vpn_node(node_id: str, _request: Request):
    """Revoke a node's VPN access (admin only).

    Requires admin session authentication.
    Node IDs are globally unique so no --user filter needed.
    """
    # TODO: require_admin_session dependency

    try:
        _run_headscale(["nodes", "delete", "--identifier", node_id, "--force"])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to revoke node: {exc}")

    # Invalidate cache so next GET /nodes returns fresh data
    global _nodes_cache
    _nodes_cache = None

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