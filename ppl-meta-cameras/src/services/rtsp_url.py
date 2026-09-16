"""Helpers for building/parsing RTSP connection strings safely."""

from __future__ import annotations

from typing import Optional, Tuple
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


def build_rtsp_url(
    host: str,
    port: int,
    path: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """Build rtsp://user:pass@host:port/path with single-encoded credentials."""
    stream_path = path or "/stream1"
    if not stream_path.startswith("/"):
        stream_path = "/" + stream_path

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
