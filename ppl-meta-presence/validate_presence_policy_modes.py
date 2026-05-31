from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4


os.environ.setdefault("PRESENCE_DETECTION_BACKEND_MODE", "simulate")
os.environ["DATABASE_URL"] = os.getenv(
    "PRESENCE_DATABASE_URL",
    "postgresql://nickgklezakos@localhost:5432/ppl_meta_presence",
)

REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.presence_models import (  # noqa: E402
    CreatePresenceGroupRequest,
    CreatePresenceSessionRequest,
    PresenceBurstUploadRequest,
    PresenceFramePayload,
    PresenceGroupPolicy,
    PresencePolicyRule,
    PresenceQrHitRequest,
    UpdateInstallationPolicyRequest,
)
from services.presence_service import PresenceService  # noqa: E402


class StubPlatformClients:
    async def list_cameras(self, _token):
        return [{"device_id": "camera-1", "name": "USB Camera 04", "camera_type": "USB", "status": "connected"}]

    async def get_collection_by_camera_device_id(self, camera_device_id, _token):
        return {"uuid": "collection-1", "name": "USB Camera 04", "camera_device_id": camera_device_id}

    async def create_audit_log(self, _token, payload):
        return {"success": True, "log_uuid": payload.get("event_type", "audit-log")}

    async def get_audit_log(self, _token, log_uuid):
        return {"uuid": log_uuid}

    async def start_instant_detection(self, camera_id):
        return {"session_uuid": f"instant-detect-{camera_id}"}

    async def get_instant_detection_results(self, _camera_id):
        return {"success": True}

    async def startup(self):
        return None

    async def shutdown(self):
        return None


async def run_completed_session(service: PresenceService, user_uuid: str, device_uuid: str) -> dict:
    current_user = {"sub": user_uuid, "token": "stub-token"}
    session = await service.create_session(
        CreatePresenceSessionRequest(
            device_uuid=device_uuid,
            device_name=device_uuid,
            device_platform="android",
            app_version="0.1.0",
        ),
        current_user,
    )

    await service.upload_burst(
        session.session_uuid,
        PresenceBurstUploadRequest(
            device_id=device_uuid,
            session_uuid=session.session_uuid,
            capture_phase="initial",
            frames=[
                PresenceFramePayload(
                    frame_data="ZmFrZV9mcmFtZQ==",
                    timestamp=1717070000.0,
                    width=720,
                    height=1280,
                    format="jpeg",
                    orientation="portrait",
                    rotation_angle=0,
                    fps=15,
                    camera_facing="front",
                )
            ],
            captured_at="2026-05-30T14:55:00Z",
            transport_source="mobile_app",
        ),
    )

    service.qr_hit(
        session.session_uuid,
        PresenceQrHitRequest(
            qr_token=session.qr_token,
            installation_uuid="local-installation",
            scanned_at="2026-05-30T14:55:05Z",
        ),
    )

    result = await service.get_result(session.session_uuid, current_user)
    trace = await service.get_session_trace(session.session_uuid, current_user)
    return {
        "result": result.model_dump(mode="json"),
        "trace": trace.model_dump(mode="json"),
    }


async def main() -> int:
    default_service = PresenceService(platform_clients=StubPlatformClients())
    default_suffix = uuid4().hex[:12]
    default_user = f"def-user-{default_suffix}"
    default_device = f"def-device-{default_suffix}"
    default_run = await run_completed_session(default_service, default_user, default_device)

    service = PresenceService(platform_clients=StubPlatformClients())

    service.update_installation_policy(
        UpdateInstallationPolicyRequest(
            installation_uuid="local-installation",
            group_policy=PresenceGroupPolicy(
                granted=PresencePolicyRule(
                    trigger_type="installation_presence_granted",
                    action_type="installation_open_gate",
                )
            ),
        )
    )

    installation_suffix = uuid4().hex[:12]
    installation_user = f"inst-user-{installation_suffix}"
    installation_device = f"inst-device-{installation_suffix}"
    installation_run = await run_completed_session(service, installation_user, installation_device)

    service.ensure_group(
        CreatePresenceGroupRequest(
            installation_uuid="local-installation",
            user_uuid="7",
            group_policy=PresenceGroupPolicy(
                granted=PresencePolicyRule(
                    trigger_type="group_presence_granted",
                    action_type="group_open_door",
                )
            ),
        ),
        {"sub": "7", "token": "stub-token"},
    )
    group_device = f"group-device-{uuid4().hex[:12]}"
    group_run = await run_completed_session(service, "7", group_device)

    if installation_run["result"].get("policy_source") != "installation_policy":
        raise SystemExit(f"Installation policy validation failed: {json.dumps(installation_run, indent=2)}")

    if group_run["result"].get("policy_source") != "group_policy":
        raise SystemExit(f"Group policy validation failed: {json.dumps(group_run, indent=2)}")

    if default_run["result"].get("policy_source") != "default_policy":
        raise SystemExit(f"Default policy validation failed: {json.dumps(default_run, indent=2)}")
    if default_run["result"].get("trigger_type") != "presence_match":
        raise SystemExit(f"Default policy trigger validation failed: {json.dumps(default_run, indent=2)}")
    if default_run["result"].get("action_type") != "presence_grant":
        raise SystemExit(f"Default policy action validation failed: {json.dumps(default_run, indent=2)}")

    print(json.dumps({
        "default_policy_run": default_run,
        "installation_policy_run": installation_run,
        "group_policy_run": group_run,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))