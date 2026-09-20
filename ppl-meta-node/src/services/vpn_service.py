"""VPN enrollment service for EyeNet Headscale mesh.

One-time bootstrap: calls the authority VPN enrollment endpoint,
gets a headscale pre-auth key, and runs `tailscale up`.

The pre-auth key is only needed for initial enrollment. After
`tailscale up` succeeds, the WireGuard keypair is stored locally
( /var/lib/tailscale/ ) and the device remains enrolled indefinitely.
No periodic re-enrollment is required.

Requirements:
  - tailscale CLI installed on the host/Docker image
  - EYENET_INSTALLATION_UUID and EYENET_APPLICATION_KEY env vars set
  - /var/lib/tailscale volume mounted (in Docker) for key persistence
"""

import os
import subprocess
import sys
import logging

import httpx

from src.services.vpn_login_server import (
    extract_control_url,
    is_eyenet_login_server,
)

logger = logging.getLogger(__name__)

AUTHORITY_URL = (
    os.environ.get("AUTHORITY_BASE_URL")
    or os.environ.get("AUTHORITY_SERVICE_URL")
    or os.environ.get("AUTHORITY_URL")
    or "https://authority.eyenet-vision.com"
)
# Prefer EYENET_* (VPN mesh); fall back to AUTHORITY_* / installer names.
# Module-level defaults; enroll_once/report resolve again via _resolve_credentials()
# so post-bootstrap app_settings keys work without recreating the container .env.
INSTALLATION_UUID = (
    os.environ.get("EYENET_INSTALLATION_UUID")
    or os.environ.get("AUTHORITY_INSTALLATION_UUID")
    or os.environ.get("INSTALLATION_UUID")
    or ""
)
APPLICATION_KEY = (
    os.environ.get("EYENET_APPLICATION_KEY")
    or os.environ.get("AUTHORITY_APPLICATION_KEY")
    or os.environ.get("APPLICATION_KEY")
    or ""
)

# Same keys AuthorityService persists after bootstrap activate.
_APP_SETTING_INSTALL_UUID = "authority_installation_uuid"
_APP_SETTING_APP_KEY = "authority_application_key"


def _credentials_from_app_settings() -> tuple[str, str]:
    """Read installation UUID / application key from Postgres app_settings if present."""
    try:
        from src.database import SessionLocal
        from src.models.app_setting import AppSetting

        db = SessionLocal()
        try:
            rows = {
                row.key: (row.value or "").strip()
                for row in db.query(AppSetting).filter(
                    AppSetting.key.in_([_APP_SETTING_INSTALL_UUID, _APP_SETTING_APP_KEY])
                )
            }
            return (
                rows.get(_APP_SETTING_INSTALL_UUID, ""),
                rows.get(_APP_SETTING_APP_KEY, ""),
            )
        finally:
            db.close()
    except Exception as exc:
        logger.debug("VPN: could not read app_settings credentials: %s", exc)
        return "", ""


def _resolve_credentials() -> tuple[str, str]:
    """Env first, then bootstrap-persisted app_settings (closes empty-.env after activate)."""
    uuid = (
        os.environ.get("EYENET_INSTALLATION_UUID")
        or os.environ.get("AUTHORITY_INSTALLATION_UUID")
        or os.environ.get("INSTALLATION_UUID")
        or INSTALLATION_UUID
        or ""
    ).strip()
    key = (
        os.environ.get("EYENET_APPLICATION_KEY")
        or os.environ.get("AUTHORITY_APPLICATION_KEY")
        or os.environ.get("APPLICATION_KEY")
        or APPLICATION_KEY
        or ""
    ).strip()
    if uuid and key:
        return uuid, key
    db_uuid, db_key = _credentials_from_app_settings()
    return (uuid or db_uuid), (key or db_key)

# Node role/tag this service enrolls as. The platform compute module (this service,
# ppl-meta-node) owns its DB/registry/media and participates in the mesh as a
# ``tag:platform`` node (Phase 3 platform self-registration). Override with
# ``EYENET_VPN_NODE_TYPE=client`` (or ``node`` for the legacy tag) when the peer
# action differs.
VPN_NODE_TYPE = os.environ.get("EYENET_VPN_NODE_TYPE", "platform")

# Optional: set a custom hostname for MagicDNS.
# If not set, derived from INSTALLATION_UUID (sanitized).
VPN_HOSTNAME = os.environ.get("EYENET_VPN_HOSTNAME", "")


def _derive_hostname(install_uuid: str) -> str:
    """Derive a unique MagicDNS hostname from the installation UUID."""
    sanitized = install_uuid.replace("@", "-").replace(".", "-")
    # Strip anything not alphanumeric, dash, or underscore
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in "-_")
    return sanitized if sanitized else "eyenet-node"


def _tailscale_cmd(args: list[str]) -> list[str]:
    cmd = ["tailscale"]
    socket_path = os.environ.get("EYENET_TS_SOCKET") or os.environ.get("TS_SOCKET", "")
    if socket_path:
        cmd.extend(["--socket", socket_path])
    return cmd + args


def _get_control_url() -> str:
    """Return this daemon's coordination server URL, or ''."""
    try:
        prefs_result = subprocess.run(
            _tailscale_cmd(["debug", "prefs"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        prefs = None
        if prefs_result.returncode == 0 and prefs_result.stdout.strip():
            import json
            prefs = json.loads(prefs_result.stdout)
        status_result = subprocess.run(
            _tailscale_cmd(["status", "--json"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = None
        if status_result.returncode == 0 and status_result.stdout.strip():
            import json
            status = json.loads(status_result.stdout)
        return extract_control_url(prefs=prefs, status=status) or ""
    except Exception:
        return ""


def _is_tailscale_installed() -> bool:
    """Check if tailscale CLI is available."""
    try:
        subprocess.run(
            _tailscale_cmd(["version"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _is_already_enrolled() -> bool:
    """True only when this daemon has an IP on the EyeNet Headscale mesh."""
    return bool(_get_tailscale_ip())


def _connected_to_other_server() -> bool:
    control = _get_control_url()
    ip = _get_tailscale_ip(require_eyenet=False)
    if ip and not is_eyenet_login_server(control):
        return True
    return bool(control) and not is_eyenet_login_server(control)


def _get_tailscale_ip(require_eyenet: bool = True) -> str:
    """Return this node's mesh IP (``100.64.x.x``) if enrolled, else ''.

    By default only returns an IP when the daemon is on EyeNet Headscale,
    so Tailscale.com / lab-mesh addresses are not reported as platform IPs.
    """
    try:
        result = subprocess.run(
            _tailscale_cmd(["status", "--json"]),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ""
        import json
        status = json.loads(result.stdout)
        ips = status.get("Self", {}).get("TailscaleIPs") or []
        if not ips:
            return ""
        if require_eyenet and not is_eyenet_login_server(_get_control_url()):
            return ""
        return ips[0]
    except Exception:
        return ""


def _is_docker_bridge_ip(ip: str) -> bool:
    """True for Docker/WSL/Lima bridge addresses phones cannot route to."""
    parts = ip.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        return False
    a, b = int(parts[0]), int(parts[1])
    return a == 172 and 16 <= b <= 31


def _get_local_ip() -> str:
    """Detect this host's primary local LAN IP (the platform's LAN address).

    Preference: installer ``ADVERTISE_HOST`` (Windows LAN / Ubuntu NIC) so
    containers do not report their Docker-bridge address (``172.18.0.x``).
    Fallback: UDP connect to a public address so the kernel picks the egress
    interface. Excludes loopback, Docker bridges, and CGNAT (Tailscale
    ``100.64.x.x``) addresses.
    """
    import socket

    advertise_host = (os.getenv("ADVERTISE_HOST") or "").strip().split(":")[0]
    if (
        advertise_host
        and not advertise_host.startswith("127.")
        and not advertise_host.startswith("100.")
        and not _is_docker_bridge_ip(advertise_host)
    ):
        return advertise_host

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if (
                ip
                and not ip.startswith("127.")
                and not ip.startswith("100.")
                and not _is_docker_bridge_ip(ip)
            ):
                return ip
    except Exception:
        pass
    return advertise_host if advertise_host and not _is_docker_bridge_ip(advertise_host) else ""


def report_platform_local_ip() -> bool:
    """Detect and report this platform's local LAN IP to the Authority.

    Called after enrollment and periodically so the Authority can hand leaf
    devices the platform's current LAN address at *their* enrollment. Non-fatal
    on failure — VPN remains optional.
    """
    install_uuid, application_key = _resolve_credentials()
    if not install_uuid or not application_key:
        return False
    local_ip = _get_local_ip()
    if not local_ip:
        logger.warning("VPN: could not detect a local LAN IP to report")
        return False
    tailscale_ip = _get_tailscale_ip()
    try:
        resp = httpx.post(
            f"{AUTHORITY_URL}/api/v1/vpn/installations/{install_uuid}/platform/local-ip",
            json={
                "application_key": application_key,
                "platform_local_ip": local_ip,
                "platform_tailscale_ip": tailscale_ip or None,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info(
                "VPN: reported platform local IP %s to authority%s",
                local_ip,
                f" (mesh {tailscale_ip})" if tailscale_ip else "",
            )
            return True
        logger.warning(
            "VPN: platform local-IP report rejected (HTTP %s): %s",
            resp.status_code,
            resp.text,
        )
        return False
    except Exception as exc:
        logger.warning("VPN: platform local-IP report failed: %s", exc)
        return False


def enroll_once() -> bool:
    """One-time VPN enrollment. Safe to call on every boot — will skip if already enrolled.

    Returns:
        True if enrollment succeeded or already enrolled, False on error.
    """
    install_uuid, application_key = _resolve_credentials()
    if not install_uuid or not application_key:
        logger.warning(
            "VPN: installation UUID / application key not set in env or app_settings — "
            "VPN mesh enrollment skipped. Complete /bootstrap or set EYENET_* env vars."
        )
        return False

    if not _is_tailscale_installed():
        logger.warning(
            "VPN: tailscale CLI not found — VPN mesh enrollment skipped. "
            "Install tailscale on this device to join the EyeNet VPN."
        )
        return False

    if _is_already_enrolled():
        logger.info("VPN: already enrolled on EyeNet — skipping enrollment")
        report_platform_local_ip()
        return True

    if _connected_to_other_server():
        control = _get_control_url() or "another coordination server"
        logger.warning(
            "VPN: tailscale is connected to %s — skipping in-place EyeNet "
            "enrollment so the existing mesh is not logged out. Set "
            "EYENET_TS_SOCKET to a userspace daemon to join EyeNet.",
            control,
        )
        return False

    try:
        resp = httpx.post(
            f"{AUTHORITY_URL}/api/v1/vpn/enroll-installation",
            json={
                "installation_uuid": install_uuid,
                "application_key": application_key,
                "node_type": VPN_NODE_TYPE,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        auth_key = data["auth_key"]
        headscale_server = data["headscale_server"]
        matrix_group_id = data.get("matrix_group_id", "")

        result = subprocess.run(
            _tailscale_cmd([
                "up",
                "--login-server", headscale_server,
                "--auth-key", auth_key,
                "--accept-routes=false",
                "--accept-dns=false",
                "--hostname", VPN_HOSTNAME or _derive_hostname(install_uuid),
            ]),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(
                "VPN: enrollment succeeded — matrix_group=%s headscale_server=%s",
                matrix_group_id,
                headscale_server,
            )
            report_platform_local_ip()
            return True

        redacted_err = (result.stderr or "").replace(auth_key, "[redacted]")
        logger.error(
            "VPN: tailscale up failed (exit=%d): %s",
            result.returncode,
            redacted_err.strip(),
        )
        if os.geteuid() != 0:
            logger.error(
                "VPN: tailscale CLI is not root (container USER is non-root). "
                "Host tailscaled requires root or --operator to apply enrollment. "
                "Use deployment/windows-installer/enroll-host-tailscale.sh on WSL."
            )
        return False

    except httpx.HTTPError as e:
        logger.warning("VPN: authority enrollment request failed (non-fatal): %s", e)
        return False
    except subprocess.TimeoutExpired:
        logger.warning("VPN: tailscale up timed out (non-fatal)")
        return False
    except Exception as e:
        logger.warning("VPN: enrollment failed (non-fatal): %s", e)
        return False
