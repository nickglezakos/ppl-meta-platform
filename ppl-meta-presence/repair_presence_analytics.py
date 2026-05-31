from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from services.presence_service import PresenceService


def main() -> int:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://nickgklezakos@localhost:5432/ppl_meta_presence",
    )

    service = PresenceService()
    repair_summary = service.repair_analytics_metadata()
    print(json.dumps(repair_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())