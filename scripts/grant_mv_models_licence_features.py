#!/usr/bin/env python3
"""Grant Models licence features on the local Authority entitlement for testing.

Sets:
  eyenet_mv_models, mv_models_upload, mv_models_custom_capability

Then refresh Node:
  curl -X POST http://localhost:8001/api/v1/licensing/authority/refresh -H "Authorization: Bearer $TOKEN"
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

FEATURES = [
    "eyenet_mv_models",
    "mv_models_upload",
    "mv_models_custom_capability",
]

AUTHORITY_SRC = Path(__file__).resolve().parents[1] / "autonomous" / "ppl-meta-authority" / "src"
sys.path.insert(0, str(AUTHORITY_SRC))

# Local Authority Postgres (matches VS Code Authority tasks).
os.environ.setdefault(
    "AUTHORITY_DATABASE_URL",
    "postgresql://authority_user:authority_password@localhost:5432/authority_db",
)

APP_KEY = os.getenv(
    "AUTHORITY_APPLICATION_KEY",
    "lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f",
)


def main() -> None:
    from core.storage import get_entitlement_by_application_key, upsert_entitlement

    existing = get_entitlement_by_application_key(APP_KEY)
    if existing is None:
        # Try any active entitlement
        print(f"No entitlement for {APP_KEY}; looking up any entitlement…")
        raise SystemExit(
            "Set AUTHORITY_APPLICATION_KEY to your Node's key, or create an entitlement first."
        )
    payload = {**existing, "licence_features": FEATURES}
    updated = upsert_entitlement(payload)
    print("Updated entitlement", updated.get("entitlement_uuid") or updated.get("application_key"))
    print("licence_features:", json.dumps(updated.get("licence_features")))
    print(
        "Next: POST Node /api/v1/licensing/authority/refresh as fresh.user, "
        "then confirm authority.licence_features lists all three."
    )


if __name__ == "__main__":
    main()
