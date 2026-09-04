"""Authority VPN API — Headscale enrollment endpoint.

Provides pre-authorized Tailscale keys to EyeNet installations.
Validates installation identity via application_key before issuing keys.
Keys are scoped with ACL tags matching the installation's Matrix group.

All endpoints require authority admin authentication (session-based).
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import require_platform_admin
from core.storage import (
    clear_installation_platform,
    consume_enrollment_token,
    create_enrollment_token,
    get_enrollment_token,
    get_installation_by_application_key,
    get_installation_by_uuid,
    get_max_platform_nodes,
    list_enrollment_tokens,
    revoke_enrollment_token,
    set_installation_matrix_group,
    set_installation_platform,
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
    # Role / type tag of the enrolling node. Tags are derived as ``tag:<node_type>``.
    #   - platform  → tag:platform  (own DB/registry compute module)   [new]
    #   - client    → tag:client    (leaf device/app)                  [existing]
    #   - analytics → tag:analytics (read-only aggregator, follow-up)  [new]
    #   - camera    → tag:camera    (edge camera)                      [existing]
    #   - signage   → tag:signage   (signage player)                   [new]
    #   - node      → tag:node (legacy, deprecated — use platform)
    node_type: str = "client"


class EnrollInstallationResponse(BaseModel):
    auth_key: str
    tailscale_ip_range: str = "100.64.0.0/10"
    headscale_server: str = ""
    matrix_group_id: str = ""
    # The installation's real UUID. Distinct from matrix_group_id — the platform
    # HMAC token below is derived from THIS value, so edge clients must persist it
    # (not the matrix group) to authenticate against ppl-meta-discovery (Issue #8).
    installation_uuid: str = ""
    primary_node_ip: str | None = None
    tags: list[str] = []
    expires_in_seconds: int = 86400  # 24 hours
    api_token: str = ""  # HMAC installation token for discovery auth (Issue #8)
    # The client's *assigned* platform (the mesh IP it should dial after
    # enrollment), or null when the installation has no platform assigned yet.
    platform_tailscale_ip: str | None = None
    platform_hostname: str | None = None


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


class InstallationPlatformAssignRequest(BaseModel):
    """Body for assigning an installation to a platform node.

    Supply either the Headscale node id or the mesh (``100.64.x.x``) IP of the
    platform. The Authority resolves the other from the VPN mesh.
    """

    platform_node_id: str | None = None
    platform_tailscale_ip: str | None = None


class InstallationPlatformResponse(BaseModel):
    """Resolved client↔platform assignment for an installation."""

    installation_uuid: str
    platform_node_id: str | None = None
    platform_tailscale_ip: str | None = None
    platform_hostname: str | None = None
    platform_assigned_at: str | None = None


class EnrollmentTokenCreateRequest(BaseModel):
    """Body for an admin to mint a one-time, short-lived enrollment token.

    Binds the token to a single installation (and hence its matrix group) +
    ``node_type``, so the receiving device can enroll into exactly the right mesh.
    ``expires_in_seconds`` must be 60..86400 (default 300 = 5 minutes).
    """

    installation_uuid: str
    node_type: str = Field(default="client")
    expires_in_seconds: int = Field(default=300, ge=60, le=86400)


class EnrollmentTokenCreateResponse(BaseModel):
    """One-time enrollment token issued by an operator for onboarding a device."""

    token: str
    installation_uuid: str
    matrix_group_id: str
    node_type: str
    headscale_server: str
    expires_in_seconds: int
    expires_at: str


class EnrollmentTokenRedeemRequest(BaseModel):
    """Body for a device to redeem a one-time enrollment token (scenario b)."""

    token: str
    node_type: str = Field(default="client")


class EnrollmentTokenInfo(BaseModel):
    token: str
    installation_uuid: str
    matrix_group_id: str
    node_type: str
    expires_at: str
    used: bool
    used_at: str | None = None
    revoked: bool
    revoked_at: str | None = None


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

# Shared secret for HMAC installation tokens (Issue #8). Must match
# ppl-meta-discovery's INSTALLATION_AUTH_SECRET.
INSTALLATION_AUTH_SECRET = os.getenv(
    "INSTALLATION_AUTH_SECRET", "ppl-meta-installation-auth-secret-dev"
)

# Authorised role/type tags for enrollment (Phase 1 tag taxonomy).
# All are derived as ``tag:<node_type>``. ``node`` is the legacy platform role,
# kept for backward compatibility but superseded by ``platform``.
SUPPORTED_NODE_TYPES = {
    "platform",
    "client",
    "analytics",
    "camera",
    "signage",
    "node",
}


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

    # Reusable pre-auth key: multiple devices (and the same device across
    # re-enrolls / re-boots) can join with this one key until it expires. This is
    # essential for field device replacement — a freshly-minted key scoped to the
    # installation's tags lets a replacement hardware join the same identity
    # without minting another key. Security is preserved because each node still
    # carries its own `tag:install-<hex>` (deduped per installation).
    cmd.append("--reusable")

    # Keys last ~24h (PREAUTH_KEY_EXPIRY_HOURS); keep them long-lived within the
    # install's lifetime so an install that resets/reboots can re-join without a
    # fresh token. Headscale rejects a 0 (never) expiry, so use a large fixed TTL.
    cmd.append("--expiration")
    cmd.append("8760h")  # 365 days — effectively "each device lives a year"

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


def _node_tags(node: dict) -> list[str]:
    """Return ACL tags for a headscale node dict, deriving node/client by hostname."""
    raw_tags = list(node.get("tags") or [])
    if not any("tag:node" in t or "tag:client" in t for t in raw_tags):
        hostname = str(node.get("given_name", node.get("name", "")))
        derived = (
            "tag:node"
            if hostname.startswith("eyenet-node") or "node" in hostname
            else "tag:client"
        )
        raw_tags.append(derived)
    return raw_tags


def _installation_uuid_to_tag(installation_uuid: str) -> str:
    """Encode an installation UUID as a Headscale-safe ACL tag.

    Installation UUIDs are ``{owner_email}-{index}`` (e.g.
    ``nick.glezakos@gmail.com-0``) and contain characters Headscale tags do
    not allow (tags must be lowercase ``[a-z0-9-_]``). Hex-encoding keeps the
    tag reversible and lowercase.
    """
    return "tag:install-" + str(installation_uuid).encode("utf-8").hex()


def _installation_uuid_from_tags(tags: list[str]) -> str:
    """Decode the installation UUID from a node's ACL tags.

    Reverse of :func:`_installation_uuid_to_tag`. Returns "" when the node has
    no ``tag:install-*`` tag (e.g. legacy enrollments).
    """
    for tag in tags or []:
        if tag.startswith("tag:install-"):
            payload = tag[len("tag:install-"):]
            try:
                return bytes.fromhex(payload).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                return payload
    return ""


def _find_primary_node_ip(matrix_group_id: str) -> str | None:
    """Return the Tailscale IP of the primary (platform) node in a matrix group, if any.

    Recognises both the legacy ``tag:node`` role and the newer ``tag:platform`` role
    (``tag:node`` is deprecated but existing deployments still use it).
    """
    if not matrix_group_id:
        return None
    try:
        nodes_data = _list_nodes(f"matrix-{matrix_group_id}")
        for node in nodes_data:
            tags = _node_tags(node)
            if "tag:node" in tags or "tag:platform" in tags:
                ips = node.get("ip_addresses") or []
                if ips:
                    return str(ips[0])
    except RuntimeError:
        return None
    return None


def _count_platform_nodes(
    matrix_group_id: str, exclude_installation_uuid: str | None = None
) -> int:
    """Count `tag:platform` nodes in a matrix, deduped by installation identity.

    Multiple nodes for the *same* installation (same ``tag:install-<hex>`` / node
    key) count once — re-enrolling an existing platform must not consume an extra
    slot. Provisioning a new platform still counts, and deleting one frees a slot.

    Args:
        matrix_group_id: UUID of the matrix (headscale user ``matrix-<uuid>``).
        exclude_installation_uuid: Installation whose own platforms are skipped,
            so re-asserting an existing platform isn't gated against itself.

    Returns:
        Number of distinct platform installations currently enrolled.
    """
    if not matrix_group_id:
        return 0
    try:
        nodes_data = _list_nodes(f"matrix-{matrix_group_id}")
    except RuntimeError:
        return 0

    seen: set[str] = set()
    count = 0
    for node in nodes_data:
        node_tags = _node_tags(node)
        if "tag:platform" not in node_tags:
            continue
        install_uuid = _installation_uuid_from_tags(node_tags)
        if exclude_installation_uuid and install_uuid == exclude_installation_uuid:
            continue
        dedup_key = (
            f"install:{_installation_uuid_to_tag(install_uuid)}"
            if install_uuid
            else f"node:{node.get('id', node.get('node_key', ''))}"
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        count += 1
    return count


def _issue_installation_token(installation_uuid: str) -> str:
    """Derive the HMAC-SHA256 installation token used for discovery auth (Issue #8)."""
    return hmac.new(
        INSTALLATION_AUTH_SECRET.encode("utf-8"),
        str(installation_uuid).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


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

        hostname = str(node.get("given_name", node.get("name", "")))
        raw_tags = list(node.get("tags") or [])

        # Derive node/client tag from hostname convention
        # Node installations: contain "node" or "hetzner" in hostname
        # Client devices: all others (cameras, mobile apps, etc.)
        if not any("tag:node" in t or "tag:client" in t for t in raw_tags):
            derived = "tag:node" if hostname.startswith("eyenet-node") or "node" in hostname else "tag:client"
            raw_tags.append(derived)

        nodes.append(VpnNodeInfo(
            node_id=node_id,
            hostname=hostname,
            installation_uuid=_installation_uuid_from_tags(raw_tags),
            tailscale_ip=(
                (node.get("ip_addresses") or [None])[0]
                if node.get("ip_addresses") else None
            ),
            online=bool(node.get("online", False)),
            last_seen=last_seen_str,
            tags=raw_tags,
        ))

    return VpnNodeListResponse(nodes=nodes)


# ---------------------------------------------------------------------------
# Shared enrollment issuance
# ---------------------------------------------------------------------------


def _issue_enrollment(
    installation_uuid: str,
    matrix_group_id: str,
    node_type: str,
    install_identity_tag: str | None = None,
) -> EnrollInstallationResponse:
    """Issue a pre-authorized key for an installation into a matrix mesh.

    Used by both ``/enroll-installation`` (application-key auth) and the
    ``/enroll-token`` redeem path (one-time token auth). Tags, headscale user,
    pre-auth key, and the client's assigned platform are all derived here so the
    two flows stay consistent.

    Args:
        installation_uuid: UUID of the enrolling installation.
        matrix_group_id: UUID of the matrix group (headscale user namespace).
        node_type: Role/type tag (``client``, ``signage``, ``platform``, ...).
        install_identity_tag: Optional ``tag:install-<hex>`` identity tag to pin
            the node back to its installation.

    Returns:
        The enrollment response with the pre-auth key, mesh metadata, and the
        client's assigned platform (when the node is a client).
    """
    tags = [f"tag:matrix-{matrix_group_id}"]
    headscale_user = f"matrix-{matrix_group_id}"

    # Always include the base installation tag
    if "tag:installation" not in tags:
        tags.insert(0, "tag:installation")

    # Add the node type tag (tag:platform / tag:client / tag:signage / ...)
    type_tag = f"tag:{node_type}"
    if type_tag not in tags:
        tags.append(type_tag)

    # Per-installation identity tag so the platform can map a node back to its
    # installation (and hence its VPN IP) via /nodes.
    identity_tag = install_identity_tag or (
        _installation_uuid_to_tag(installation_uuid) if installation_uuid else None
    )
    if identity_tag and identity_tag not in tags:
        tags.append(identity_tag)

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
        installation_uuid,
        matrix_group_id,
        tags,
    )

    # Resolve the primary node's Tailscale IP (used by VPN-direct discovery)
    primary_node_ip = _find_primary_node_ip(matrix_group_id)

    # Issue the installation token for discovery service authentication (Issue #8)
    api_token = _issue_installation_token(installation_uuid)

    # The client's *assigned* platform (mesh IP + hostname) so it knows where to
    # dial after enrollment. A platform/analytics node enrols as its own compute
    # module, so it has no separate assigned platform — but leaf nodes (client,
    # signage, camera, ...) need the platform's mesh IP to reach it over the mesh.
    assigned = get_installation_by_uuid(installation_uuid) or {}
    is_leaf = node_type not in ("platform", "analytics")
    platform_tailscale_ip = (
        assigned.get("platform_tailscale_ip") if is_leaf else None
    )
    platform_hostname = (
        assigned.get("platform_hostname") if is_leaf else None
    )

    return EnrollInstallationResponse(
        auth_key=auth_key,
        tags=tags,
        matrix_group_id=matrix_group_id,
        installation_uuid=installation_uuid,
        primary_node_ip=primary_node_ip,
        headscale_server="https://vpn.eyenet-vision.com",
        expires_in_seconds=PREAUTH_KEY_EXPIRY_HOURS * 3600,
        api_token=api_token,
        platform_tailscale_ip=platform_tailscale_ip,
        platform_hostname=platform_hostname,
    )


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

    # Validate node_type is a known role/type tag (Phase 1 taxonomy).
    node_type = (payload.node_type or "client").lower()
    if node_type not in SUPPORTED_NODE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported node_type '{payload.node_type}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_NODE_TYPES))}",
        )

    # Determine ACL tags and user namespace (per-matrix isolation).
    matrix_group_id = installation.get("matrix_group_id")
    if not matrix_group_id:
        # Auto-provision and PERSIST the matrix group so subsequent enrollments
        # and device lookups reuse the same mesh.
        matrix_group_id = str(uuid.uuid4())
        set_installation_matrix_group(payload.installation_uuid, matrix_group_id)
        logger.info(
            "Auto-provisioned matrix group %s for installation %s",
            matrix_group_id,
            payload.installation_uuid,
        )

    # Enforce the licence's platform-node limit at platform enrollment (Phase 2).
    # ``tag:platform`` enrolments are gated by ``entitlements.max_platform_nodes``.
    # 0 = unlimited. Re-asserting an existing platform (same installation_uuid)
    # does not consume an extra slot.
    if node_type == "platform":
        max_platform_nodes = get_max_platform_nodes(payload.installation_uuid)
        if max_platform_nodes and max_platform_nodes > 0:
            current = _count_platform_nodes(
                matrix_group_id, exclude_installation_uuid=payload.installation_uuid
            )
            if current >= max_platform_nodes:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Platform node limit reached: {current}/{max_platform_nodes}. "
                        "This licence cannot run another platform compute module."
                    ),
                )

    install_identity_tag = (
        _installation_uuid_to_tag(payload.installation_uuid)
        if payload.installation_uuid
        else None
    )
    return _issue_enrollment(
        installation_uuid=payload.installation_uuid,
        matrix_group_id=matrix_group_id,
        node_type=node_type,
        install_identity_tag=install_identity_tag,
    )


# ---------------------------------------------------------------------------
# One-time enrollment tokens (scenario b: platform publishes a token)
# ---------------------------------------------------------------------------


@router.post(
    "/enrollment-tokens",
    response_model=EnrollmentTokenCreateResponse,
)
async def create_enrollment_token_endpoint(
    payload: EnrollmentTokenCreateRequest,
    current_admin: dict[str, str] = Depends(require_platform_admin),
):
    """Mint a one-time, short-lived enrollment token (platform admin only).

    Binds the token to one installation (and thereby its matrix group) +
    ``node_type``. The device presents the token back at ``/enroll-token`` to
    receive a real pre-auth key — the Authority knows exactly which mesh/tenant
    to enroll it into from the token alone. Single-use, expiring in seconds.
    """
    installation = get_installation_by_uuid(payload.installation_uuid.strip())
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    node_type = (payload.node_type or "client").lower()
    if node_type not in SUPPORTED_NODE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported node_type '{payload.node_type}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_NODE_TYPES))}",
        )

    # Resolve (and pin) the matrix group so the token unambiguously targets a mesh.
    matrix_group_id = installation.get("matrix_group_id")
    if not matrix_group_id:
        matrix_group_id = str(uuid.uuid4())
        set_installation_matrix_group(payload.installation_uuid, matrix_group_id)
        logger.info(
            "Auto-provisioned matrix group %s for installation %s",
            matrix_group_id,
            payload.installation_uuid,
        )

    token = f"hsent-{secrets.token_urlsafe(24)}"
    expires_dt = datetime.now(timezone.utc) + timedelta(
        seconds=payload.expires_in_seconds
    )
    expires_at = expires_dt.isoformat()

    create_enrollment_token(
        token=token,
        installation_uuid=installation["installation_uuid"],
        matrix_group_id=matrix_group_id,
        node_type=node_type,
        expires_at=expires_at,
        created_by_user_uuid=current_admin.get("user_uuid"),
    )

    logger.info(
        "Enrollment token minted: installation=%s matrix=%s node_type=%s ttl=%ss "
        "by=%s",
        installation["installation_uuid"],
        matrix_group_id,
        node_type,
        payload.expires_in_seconds,
        current_admin.get("email"),
    )

    return EnrollmentTokenCreateResponse(
        token=token,
        installation_uuid=installation["installation_uuid"],
        matrix_group_id=matrix_group_id,
        node_type=node_type,
        headscale_server="https://vpn.eyenet-vision.com",
        expires_in_seconds=payload.expires_in_seconds,
        expires_at=expires_at,
    )


@router.post("/enroll-token", response_model=EnrollInstallationResponse)
async def enroll_by_token(payload: EnrollmentTokenRedeemRequest):
    """Redeem a reusable enrollment token and enroll the device into its mesh.

    The device presents a token minted by a platform admin (scenario b). The
    Authority validates the token (exists, not revoked, not expired), then issues
    a real pre-auth key bound to the mesh the token was minted for.

    The token is reusable: it is NOT consumed, so a replacement device can
    re-redeem the same token. To keep a single-identity / data-tracing
    guarantee, any existing nodes for the SAME installation (same
    ``tag:install-<hex>``) are retired first, so the new hardware becomes the one
    canonical node for that installation.
    """
    token = (payload.token or "").strip()
    if not token:
        raise HTTPException(status_code=422, detail="Enrollment token is required")

    record = get_enrollment_token(token)
    if record is None:
        raise HTTPException(status_code=404, detail="Unknown enrollment token")

    if record.get("revoked_at"):
        raise HTTPException(status_code=403, detail="Enrollment token is revoked")

    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=410, detail="Enrollment token has expired"
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "Could not parse token expiry %r: %s", record.get("expires_at"), exc
        )
        raise HTTPException(status_code=410, detail="Enrollment token has expired")

    node_type = (payload.node_type or record.get("node_type") or "client").lower()
    if node_type not in SUPPORTED_NODE_TYPES:
        node_type = record.get("node_type") or "client"

    installation_uuid = record["installation_uuid"]
    matrix_group_id = record["matrix_group_id"]

    logger.info(
        "Enrolling device via (reusable) token: installation=%s matrix=%s node_type=%s",
        installation_uuid,
        matrix_group_id,
        node_type,
    )

    # Retire any existing node(s) for this installation so the enrolling device
    # becomes the single canonical node — preserves one-identity data tracing
    # across a device replacement.
    _retire_nodes_for_installation(installation_uuid, matrix_group_id, node_type)

    return _issue_enrollment(
        installation_uuid=installation_uuid,
        matrix_group_id=matrix_group_id,
        node_type=node_type,
    )


def _retire_nodes_for_installation(
    installation_uuid: str, matrix_group_id: str, node_type: str
) -> None:
    """Delete exiting headscale nodes for an installation (best-effort).

    Used on token re-redeem so a replacement device takes over the single
    identity (and mesh IP) for that installation instead of accumulating
    duplicate ``tag:install-<hex>`` nodes. Non-fatal — if deletion fails we still
    proceed (a best-effort cleanup to avoid breaking enrollment).
    """
    if not matrix_group_id:
        return
    target_tag = _installation_uuid_to_tag(installation_uuid)
    try:
        nodes_data = _list_nodes(f"matrix-{matrix_group_id}")
    except RuntimeError as exc:
        logger.warning("Could not list nodes for retirement: %s", exc)
        return

    for node in nodes_data:
        node_id = str(node.get("id", ""))
        if not node_id:
            continue
        tags = _node_tags(node)
        # Only retire nodes belonging to this installation AND this node type
        # (don't accidentally remove a platform node when a signage replaces).
        has_install_tag = any(t == target_tag for t in tags)
        type_tag = f"tag:{node_type}"
        has_type_tag = type_tag in tags or (
            node_type in ("platform", "node")
            and ("tag:platform" in tags or "tag:node" in tags)
        )
        if not has_install_tag or not has_type_tag:
            continue
        try:
            _run_headscale(["nodes", "delete", "--identifier", node_id, "--force"])
            logger.info(
                "Retired node %s for installation %s (%s replacement)",
                node_id,
                installation_uuid,
                node_type,
            )
        except RuntimeError as exc:
            logger.warning("Failed to retire node %s: %s", node_id, exc)


@router.get("/enrollment-tokens", response_model=list[EnrollmentTokenInfo])
async def list_enrollment_tokens(
    current_admin: dict[str, str] = Depends(require_platform_admin),
):
    """List outstanding (and recently used) enrollment tokens (admin only)."""
    tokens: list[dict]
    try:
        tokens = list_enrollment_tokens(limit=100)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to list tokens: {exc}")

    return [
        EnrollmentTokenInfo(
            token=t["token"],
            installation_uuid=t["installation_uuid"],
            matrix_group_id=t["matrix_group_id"],
            node_type=t["node_type"],
            expires_at=t["expires_at"],
            used=t["used_at"] is not None,
            used_at=t["used_at"],
            revoked=t["revoked_at"] is not None,
            revoked_at=t["revoked_at"],
        )
        for t in tokens
    ]


def _find_platform_node_by_id_or_ip(identifier: str | None) -> dict | None:
    """Return a `tag:platform` node matching a Headscale node id or mesh IP.

    Args:
        identifier: Either a Headscale node id or a mesh (``100.64.x.x``) IP.

    Returns:
        The matching headscale node dict, or None if not found.
    """
    if not identifier:
        return None
    identifier = identifier.strip()

    try:
        nodes_data = _run_headscale_and_load_nodes()
    except RuntimeError:
        return None

    for node in nodes_data:
        node_id = str(node.get("id", ""))
        ips = [str(ip) for ip in (node.get("ip_addresses") or [])]
        tags = _node_tags(node)
        if "tag:platform" not in tags:
            continue
        if identifier in (node_id, *ips):
            return node
    return None


def _run_headscale_and_load_nodes() -> list[dict]:
    """Run ``headscale nodes list --output json`` and parse the JSON list."""
    output = _run_headscale(["nodes", "list", "--output", "json"])
    data = json.loads(output)
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# Client↔platform assignment (Phase 2)
# ---------------------------------------------------------------------------


@router.get(
    "/installations/{installation_uuid}/platform",
    response_model=InstallationPlatformResponse,
)
async def get_installation_platform(installation_uuid: str, _request: Request):
    """Resolve the platform assigned to an installation (admin only)."""
    installation = get_installation_by_uuid(installation_uuid)
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    return InstallationPlatformResponse(
        installation_uuid=installation_uuid,
        platform_node_id=installation.get("platform_node_id"),
        platform_tailscale_ip=installation.get("platform_tailscale_ip"),
        platform_hostname=installation.get("platform_hostname"),
        platform_assigned_at=installation.get("platform_assigned_at"),
    )


@router.post(
    "/installations/{installation_uuid}/platform",
    response_model=InstallationPlatformResponse,
)
async def assign_installation_platform(
    installation_uuid: str,
    payload: InstallationPlatformAssignRequest,
    _request: Request,
):
    """Assign an installation to a platform node (admin only).

    The only link between a client and a platform. Provide either the platform's
    Headscale node id or its mesh (``100.64.x.x``) IP; the Authority resolves the
    other fields from the mesh. Re-assigning is idempotent (flips the client).
    """
    installation = get_installation_by_uuid(installation_uuid)
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    if not payload.platform_node_id and not payload.platform_tailscale_ip:
        raise HTTPException(
            status_code=422,
            detail="Provide either platform_node_id or platform_tailscale_ip",
        )

    node = _find_platform_node_by_id_or_ip(
        payload.platform_node_id or payload.platform_tailscale_ip
    )
    if node is None:
        raise HTTPException(
            status_code=404,
            detail="No tag:platform node found for the given node_id / tailscale_ip",
        )

    node_id = str(node.get("id", ""))
    tailscale_ip = (
        (node.get("ip_addresses") or [None])[0]
        if node.get("ip_addresses") else None
    )
    hostname = str(node.get("given_name", node.get("name", "")))

    set_installation_platform(
        installation_uuid,
        node_id,
        tailscale_ip,
        hostname,
    )
    logger.info(
        "Installation %s assigned to platform %s (%s)",
        installation_uuid, node_id, tailscale_ip,
    )

    refreshed = get_installation_by_uuid(installation_uuid)
    return InstallationPlatformResponse(
        installation_uuid=installation_uuid,
        platform_node_id=node_id,
        platform_tailscale_ip=tailscale_ip,
        platform_hostname=hostname,
        platform_assigned_at=refreshed.get("platform_assigned_at") if refreshed else None,
    )


@router.delete(
    "/installations/{installation_uuid}/platform",
    response_model=InstallationPlatformResponse,
)
async def unlink_installation_platform(installation_uuid: str, _request: Request):
    """Clear an installation's platform link, leaving it unassigned (admin only)."""
    installation = get_installation_by_uuid(installation_uuid)
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    clear_installation_platform(installation_uuid)
    logger.info("Installation %s unlinked from its platform", installation_uuid)

    return InstallationPlatformResponse(installation_uuid=installation_uuid)


@router.get("/platforms", response_model=VpnNodeListResponse)
async def list_platforms(_request: Request):
    """List all platform compute modules (filter /nodes by tag:platform).

    This is the discovery mechanism the analytics aggregator uses to enumerate
    every platform in the mesh. Legacy ``tag:node`` platforms (enrolled before the
    ``tag:platform`` role existed) are also matched, so existing deployments show
    up immediately (they can later be retagged to ``tag:platform`` via headscale).
    """
    all_nodes = _fetch_all_nodes()
    platforms = [
        n for n in all_nodes.nodes
        if "tag:platform" in n.tags or "tag:node" in n.tags
    ]
    return VpnNodeListResponse(nodes=platforms)
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
        node_tags = _node_tags(node)
        nodes.append(VpnNodeInfo(
            node_id=str(node.get("id", node.get("node_key", ""))),
            hostname=str(node.get("name", node.get("given_name", ""))),
            installation_uuid=_installation_uuid_from_tags(node_tags),
            tailscale_ip=(
                (node.get("ip_addresses") or [None])[0] if node.get("ip_addresses") else None
            ),
            online=node.get("online", False),
            last_seen=str(node.get("last_seen", "")),
            tags=node_tags,
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