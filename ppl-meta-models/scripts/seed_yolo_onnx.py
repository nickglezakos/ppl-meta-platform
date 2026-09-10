#!/usr/bin/env python3
"""Download open-source YOLOv8n / YOLOv8n-pose ONNX into the Models artifact store.

Usage (from repo root):
  python ppl-meta-models/scripts/seed_yolo_onnx.py

Uses ultralytics export when available; otherwise uses files under seed_weights/.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import config  # noqa: E402
from database import SessionLocal, create_tables  # noqa: E402
from catalog import (  # noqa: E402
    BODY_YOLO,
    BODY_YOLO_POSE,
    DEFAULT_VERSION,
    FACE_YOLO,
    seed_builtins,
)
from models import MvArtifact, MvModelVersion  # noqa: E402


def _copy_or_export(dest: Path, *, seed_names: tuple[str, ...], ultralytics_name: str) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)

    for name in seed_names:
        for candidate in (
            ROOT / "seed_weights" / name,
            Path.cwd() / name,
        ):
            if candidate.is_file() and candidate.stat().st_size > 0:
                dest.write_bytes(candidate.read_bytes())
                return dest

    try:
        from ultralytics import YOLO

        model = YOLO(ultralytics_name)
        out = model.export(format="onnx", imgsz=640, simplify=True)
        exported = Path(str(out))
        if exported.is_file():
            dest.write_bytes(exported.read_bytes())
            return dest
    except Exception as exc:
        print(f"ultralytics export failed for {ultralytics_name}: {exc}")

    raise SystemExit(
        f"Could not obtain {dest.name}. Place one at ppl-meta-models/seed_weights/{seed_names[0]} "
        f"or install ultralytics and re-run."
    )


def _register(db, model_id: str, path: Path, *, runtime: str = "onnx") -> None:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    existing = (
        db.query(MvArtifact).filter_by(model_id=model_id, version=DEFAULT_VERSION).first()
    )
    if existing:
        existing.uri = str(path.resolve())
        existing.sha256 = digest
        existing.size_bytes = len(data)
        existing.filename = path.name
    else:
        db.add(
            MvArtifact(
                model_id=model_id,
                version=DEFAULT_VERSION,
                filename=path.name,
                sha256=digest,
                size_bytes=len(data),
                uri=str(path.resolve()),
                content_type="application/octet-stream",
            )
        )
    version = (
        db.query(MvModelVersion)
        .filter_by(model_id=model_id, version=DEFAULT_VERSION)
        .one_or_none()
    )
    if version:
        version.status = "ready"
        version.runtime = runtime


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        seed_builtins(db)
        face_path = config.ARTIFACT_ROOT / FACE_YOLO / DEFAULT_VERSION / "yolov8n.onnx"
        body_path = config.ARTIFACT_ROOT / BODY_YOLO / DEFAULT_VERSION / "yolov8n.onnx"
        pose_path = (
            config.ARTIFACT_ROOT / BODY_YOLO_POSE / DEFAULT_VERSION / "yolov8n-pose.onnx"
        )
        shared = _copy_or_export(
            face_path,
            seed_names=("yolov8n.onnx",),
            ultralytics_name="yolov8n.pt",
        )
        if body_path != shared:
            body_path.parent.mkdir(parents=True, exist_ok=True)
            body_path.write_bytes(shared.read_bytes())
        _register(db, FACE_YOLO, face_path, runtime="onnx")
        _register(db, BODY_YOLO, body_path, runtime="onnx")
        try:
            _copy_or_export(
                pose_path,
                seed_names=("yolov8n-pose.onnx",),
                ultralytics_name="yolov8n-pose.pt",
            )
            _register(db, BODY_YOLO_POSE, pose_path, runtime="onnx_pose")
            print(f"Seeded {BODY_YOLO_POSE} -> {pose_path}")
        except SystemExit as exc:
            print(f"WARN: pose seed skipped: {exc}")
        db.commit()
        print(f"Seeded {FACE_YOLO} -> {face_path}")
        print(f"Seeded {BODY_YOLO} -> {body_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
