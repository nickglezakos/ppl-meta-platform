"""Helpers for building/parsing RTSP connection strings safely."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, unquote


def normalize_credential(value: Optional[str]) -> str:
    """Decode any prior percent-encoding, then encode exactly once."""
    if value is None:
        return ""
    text = str(value)
    # Collapse accidental double-encoding (%2540 -> %40 -> @)
    for _ in range(3):
        decoded = unquote(text)
        if decoded == text:
            break
        text = decoded
    return text


def normalize_stream_path(path: Optional[str], default: str = "/stream1") -> str:
    """Ensure a stream path starts with / and is non-empty."""
    if path is None:
        return default
    text = str(path).strip()
    if not text:
        return default
    if not text.startswith("/"):
        text = "/" + text
    return text


def build_rtsp_url(
    host: str,
    port: int,
    path: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """Build rtsp://user:pass@host:port/path with single-encoded credentials."""
    stream_path = normalize_stream_path(path, default="/stream1")

    credentials = ""
    user = normalize_credential(username)
    if user:
        user_q = quote(user, safe="")
        pwd = normalize_credential(password)
        if pwd:
            credentials = f"{user_q}:{quote(pwd, safe='')}@"
        else:
            credentials = f"{user_q}@"

    return f"rtsp://{credentials}{host}:{int(port)}{stream_path}"


def parse_rtsp_host_path(connection_string: Optional[str]) -> Tuple[Optional[str], str]:
    """
    Extract host and path from an RTSP URL.

    Uses the last '@' so email usernames (user@domain) do not break parsing.
    """
    if not connection_string or not connection_string.startswith("rtsp://"):
        return None, "/stream1"

    remaining = connection_string[len("rtsp://") :]
    at = remaining.rfind("@")
    if at >= 0:
        remaining = remaining[at + 1 :]

    slash = remaining.find("/")
    if slash >= 0:
        hostport, path = remaining[:slash], remaining[slash:]
    else:
        hostport, path = remaining, "/stream1"

    colon = hostport.rfind(":")
    if colon > 0:
        host = hostport[:colon]
    else:
        host = hostport
    return host or None, path or "/stream1"


def rebuild_rtsp_url_from_camera(
    connection_string: Optional[str],
    username: Optional[str],
    password: Optional[str],
    port: Optional[int],
) -> Optional[str]:
    """Rebuild a clean RTSP URL from DB columns + existing connection_string host/path."""
    if not username and not connection_string:
        return connection_string
    host, path = parse_rtsp_host_path(connection_string)
    if not host:
        return connection_string
    return build_rtsp_url(
        host=host,
        port=port or 554,
        path=path,
        username=username,
        password=password,
    )


def get_rtsp_substream_path(settings: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return optional RTSP substream path from cameras.settings, or None."""
    if not isinstance(settings, dict):
        return None
    rtsp = settings.get("rtsp")
    if not isinstance(rtsp, dict):
        return None
    raw = rtsp.get("substream_path")
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return normalize_stream_path(text)


def merge_rtsp_substream_settings(
    settings: Optional[Dict[str, Any]],
    substream_path: Optional[str],
) -> Dict[str, Any]:
    """
    Merge optional substream_path into cameras.settings without wiping other keys.

    Empty / None substream_path removes the stored substream path.
    """
    merged: Dict[str, Any] = dict(settings) if isinstance(settings, dict) else {}
    rtsp: Dict[str, Any] = (
        dict(merged["rtsp"]) if isinstance(merged.get("rtsp"), dict) else {}
    )

    text = (substream_path or "").strip()
    if text:
        rtsp["substream_path"] = normalize_stream_path(text)
        merged["rtsp"] = rtsp
    else:
        rtsp.pop("substream_path", None)
        if rtsp:
            merged["rtsp"] = rtsp
        else:
            merged.pop("rtsp", None)

    return merged


def record_connection_string(
    connection_string: Optional[str],
    username: Optional[str],
    password: Optional[str],
    port: Optional[int],
) -> Optional[str]:
    """Main / recording URL — always the path stored in connection_string."""
    return rebuild_rtsp_url_from_camera(
        connection_string, username, password, port
    )


def live_connection_string(
    connection_string: Optional[str],
    username: Optional[str],
    password: Optional[str],
    port: Optional[int],
    settings: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Live-view / instant-detection URL.

    Uses settings.rtsp.substream_path when set; otherwise the main path.
    """
    main = record_connection_string(
        connection_string, username, password, port
    )
    sub = get_rtsp_substream_path(settings)
    if not sub:
        return main
    host, _ = parse_rtsp_host_path(connection_string or main)
    if not host:
        return main
    return build_rtsp_url(
        host=host,
        port=port or 554,
        path=sub,
        username=username,
        password=password,
    )
