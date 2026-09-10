"""Local artifact store for uploaded model files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from config import config

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def ensure_artifact_root() -> Path:
    root = config.ARTIFACT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def store_upload(
    *,
    model_id: str,
    version: str,
    filename: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> dict:
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ValueError("upload_too_large")
    suffix = Path(filename).suffix.lower()
    if suffix not in config.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError("unsupported_extension")

    safe_model = _SAFE_NAME.sub("_", model_id)
    safe_version = _SAFE_NAME.sub("_", version)
    safe_name = _SAFE_NAME.sub("_", Path(filename).name)
    digest = hashlib.sha256(data).hexdigest()
    dest_dir = ensure_artifact_root() / safe_model / safe_version
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{digest[:16]}_{safe_name}"
    dest.write_bytes(data)
    return {
        "filename": Path(filename).name,
        "sha256": digest,
        "size_bytes": len(data),
        "uri": str(dest),
        "content_type": content_type or "application/octet-stream",
        "suffix": suffix,
    }
