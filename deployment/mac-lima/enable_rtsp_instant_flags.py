"""Enable auto_face / body / instant flags for RTSP cameras (and a target device)."""
import json
import os
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text
from src.database import SessionLocal

TARGET = os.getenv("DEVICE_ID", "bec5f94f-02ce-4620-9dc7-ed50d564c182")


def merge_body(opts):
    if opts is None or opts == {} or opts == "null":
        return {"auto_body_detection": True}
    if isinstance(opts, str):
        try:
            opts = json.loads(opts)
        except Exception:
            opts = {}
    if not isinstance(opts, dict):
        opts = {}
    opts = dict(opts)
    opts["auto_body_detection"] = True
    return opts


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT device_id, name, camera_type::text AS camera_type,
                       auto_face_detection, instant_detection_enabled, processing_options
                FROM cameras
                WHERE device_id = :id
                   OR upper(camera_type::text) LIKE '%RTSP%'
                """
            ),
            {"id": TARGET},
        ).mappings().all()

        for row in rows:
            opts = merge_body(row["processing_options"])
            db.execute(
                text(
                    """
                    UPDATE cameras
                    SET auto_face_detection = TRUE,
                        instant_detection_enabled = TRUE,
                        processing_options = CAST(:opts AS json),
                        updated_at = NOW()
                    WHERE device_id = :id
                    """
                ),
                {"opts": json.dumps(opts), "id": row["device_id"]},
            )
            print(
                "ENABLED",
                row["device_id"],
                row["name"],
                row["camera_type"],
                "was_face=",
                row["auto_face_detection"],
                "was_instant=",
                row["instant_detection_enabled"],
            )
        db.commit()
        print("DONE", len(rows), "cameras")
    finally:
        db.close()


if __name__ == "__main__":
    main()
