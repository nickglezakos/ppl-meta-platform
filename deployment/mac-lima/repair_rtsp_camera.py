"""One-shot: normalize RTSP connection_string for a camera using app DB config."""
import sys

sys.path.insert(0, "/app")

from urllib.parse import quote
from src.database import SessionLocal
from src.services.rtsp_url import (
    normalize_credential,
    rebuild_rtsp_url_from_camera,
    parse_rtsp_host_path,
)

DEVICE_ID = "bec5f94f-02ce-4620-9dc7-ed50d564c182"


def main() -> None:
    db = SessionLocal()
    try:
        row = db.execute(
            __import__("sqlalchemy").text(
                "SELECT device_id, name, connection_string, username, password, port "
                "FROM cameras WHERE device_id = :id"
            ),
            {"id": DEVICE_ID},
        ).mappings().first()
        if not row:
            print("CAMERA_NOT_FOUND")
            return

        cs = row["connection_string"] or ""
        user_n = normalize_credential(row["username"] or "")
        pwd_n = normalize_credential(row["password"] or "")
        port = row["port"] or 554

        print("BEFORE_has2540", "%2540" in cs)
        # Redact password in printed URL
        safe_before = cs
        if "@" in cs:
            scheme, rest = cs.split("://", 1)
            auth, hostpart = rest.rsplit("@", 1)
            if ":" in auth:
                u, _ = auth.split(":", 1)
                safe_before = f"{scheme}://{u}:***@{hostpart}"
            else:
                safe_before = f"{scheme}://{auth}:***@{hostpart}"
        print("BEFORE", safe_before)
        print("USER", user_n)
        print("PORT", port)

        if not user_n or not pwd_n:
            # Fall back to credentials embedded in connection_string
            if cs.startswith("rtsp://") and "@" in cs:
                auth = cs[7:].rsplit("@", 1)[0]
                if ":" in auth:
                    u, p = auth.split(":", 1)
                    user_n = user_n or normalize_credential(u)
                    pwd_n = pwd_n or normalize_credential(p)

        rebuilt = rebuild_rtsp_url_from_camera(cs, user_n, pwd_n, port)
        if not rebuilt:
            host, path = parse_rtsp_host_path(cs)
            if not host:
                print("CANNOT_PARSE_HOST")
                return
            cred = ""
            if user_n and pwd_n:
                cred = f"{quote(user_n, safe='')}:{quote(pwd_n, safe='')}@"
            elif user_n:
                cred = f"{quote(user_n, safe='')}@"
            rebuilt = f"rtsp://{cred}{host}:{port}{path or '/stream1'}"

        db.execute(
            __import__("sqlalchemy").text(
                "UPDATE cameras SET connection_string = :cs, username = :u, password = :p "
                "WHERE device_id = :id"
            ),
            {"cs": rebuilt, "u": user_n or row["username"], "p": pwd_n or row["password"], "id": DEVICE_ID},
        )
        db.commit()

        safe_after = rebuilt
        if "@" in rebuilt:
            scheme, rest = rebuilt.split("://", 1)
            auth, hostpart = rest.rsplit("@", 1)
            if ":" in auth:
                u, _ = auth.split(":", 1)
                safe_after = f"{scheme}://{u}:***@{hostpart}"
        print("AFTER", safe_after)
        print("AFTER_has2540", "%2540" in rebuilt)
        print("AFTER_has40", "%40" in rebuilt)
        print("DONE")
    finally:
        db.close()


if __name__ == "__main__":
    main()
