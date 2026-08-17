from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from presence_auth import get_current_user, require_admin_user
from models.presence_models import (
    BindResourcesRequest,
    CreatePresenceSessionRequest,
    PresenceBurstUploadRequest,
    PresenceOwnerQrRenderRequest,
    PresenceOwnerQrHitRequest,
    PresenceQrHitRequest,
    PresenceQrRenderRequest,
    PresenceQrValidateRequest,
    ResetInstallationReservationsRequest,
    ReserveResourceRequest,
    TriggerMatchRequest,
    UnreserveResourceRequest,
    UpdateActivePresenceGroupRequest,
    UpdateInstallationSettingsRequest,
    UpdateInstallationPolicyRequest,
)
from services.presence_service import PresenceService

logger = logging.getLogger(__name__)


def _parse_filter_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def build_presence_router(service: PresenceService) -> APIRouter:
    router = APIRouter(dependencies=[Depends(get_current_user)])

    @router.get("/installations/current")
    async def get_current_installation(current_user: dict = Depends(get_current_user)):
        await service.refresh_local_installation_reference(current_user)
        return {"success": True, "data": service.get_current_installation_context()}

    @router.post("/installations/current/reset-reservations")
    async def reset_current_installation_reservations(
        request: ResetInstallationReservationsRequest,
    ):
        return {"success": True, "data": service.reset_installation_reservations(request)}

    @router.get("/installations/current/policy")
    async def get_current_installation_policy():
        return {"success": True, "data": {"group_policy": service.get_current_installation_context().get("group_policy")}}

    @router.post("/installations/current/policy")
    async def update_current_installation_policy(request: UpdateInstallationPolicyRequest):
        return {"success": True, "data": service.update_installation_policy(request)}

    @router.get("/installations/current/available-groups")
    async def list_current_installation_available_groups(current_user: dict = Depends(get_current_user)):
        items = await service.list_available_individual_groups(current_user)
        return {"success": True, "data": {"items": [item.model_dump() for item in items]}}

    @router.post("/installations/current/active-group")
    async def update_current_installation_active_group(
        request: UpdateActivePresenceGroupRequest,
        current_user: dict = Depends(get_current_user),
    ):
        return {"success": True, "data": await service.update_active_presence_group(request, current_user)}

    @router.get("/installations/current/settings")
    async def get_current_installation_settings():
        context = service.get_current_installation_context()
        return {"success": True, "data": {"session_settings": context.get("session_settings")}}

    @router.post("/installations/current/settings")
    async def update_current_installation_settings(request: UpdateInstallationSettingsRequest):
        return {"success": True, "data": service.update_installation_settings(request)}

    @router.get("/profiles/me")
    async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
        return {"success": True, "data": service.get_current_user_profile(current_user)}

    @router.get("/mobile/sessions/{session_uuid}/action-plan")
    async def get_action_plan(session_uuid: str):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        return {"success": True, "data": service.get_action_plan(session_uuid).model_dump()}

    @router.get("/mobile/sessions/{session_uuid}/decision-history")
    async def get_decision_history(session_uuid: str):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        return {
            "success": True,
            "data": {"items": [item.model_dump() for item in service.list_decision_history(session_uuid)]},
        }

    @router.get("/decision-history")
    async def query_decision_history(
        session_uuid: str | None = None,
        user_uuid: str | None = None,
        installation_uuid: str | None = None,
        policy_source: str | None = None,
        limit: int | None = None,
    ):
        result = service.query_decision_history(
            session_uuid=session_uuid,
            user_uuid=user_uuid,
            installation_uuid=installation_uuid,
            policy_source=policy_source,
            limit=limit,
        )
        return {
            "success": True,
            "data": {
                **{key: value for key, value in result.items() if key != "items"},
                "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in result["items"]],
            },
        }

    @router.get("/mobile/sessions/{session_uuid}/trace")
    async def get_session_trace(
        session_uuid: str,
        current_user: dict = Depends(get_current_user),
    ):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        trace = await service.get_session_trace(session_uuid, current_user)
        return {"success": True, "data": trace.model_dump()}

    @router.get("/mobile/session-traces")
    async def query_session_traces(
        session_uuid: str | None = None,
        user_uuid: str | None = None,
        installation_uuid: str | None = None,
        policy_source: str | None = None,
        user_query: str | None = None,
        camera_uuid: str | None = None,
        grant_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        current_user: dict = Depends(get_current_user),
    ):
        parsed_start_date = _parse_filter_datetime(start_date)
        parsed_end_date = _parse_filter_datetime(end_date)
        result = await service.query_session_traces(
            current_user,
            session_uuid=session_uuid,
            user_uuid=user_uuid,
            installation_uuid=installation_uuid,
            policy_source=policy_source,
            user_query=user_query,
            camera_uuid=camera_uuid,
            grant_type=grant_type,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset,
        )
        return {
            "success": True,
            "data": {
                **{key: value for key, value in result.items() if key != "items"},
                "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in result["items"]],
            },
        }

    @router.get("/mobile/session-awards/by-user-day")
    async def query_user_day_award_summary(
        user_query: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        current_user: dict = Depends(get_current_user),
    ):
        parsed_start_date = _parse_filter_datetime(start_date)
        parsed_end_date = _parse_filter_datetime(end_date)
        result = await service.query_user_day_award_summary(
            current_user,
            user_query=user_query,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset,
        )
        return {
            "success": True,
            "data": {
                **{key: value for key, value in result.items() if key != "items"},
                "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in result["items"]],
            },
        }

    @router.post("/mobile/sessions")
    async def create_session(
        request: CreatePresenceSessionRequest,
        current_user: dict = Depends(get_current_user),
    ):
        session = await service.create_session(request, current_user)
        return {"success": True, "data": session.model_dump()}

    @router.get("/mobile/sessions/{session_uuid}")
    async def get_session(session_uuid: str):
        session = service.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Presence session not found")
        return {"success": True, "data": session.model_dump()}

    @router.post("/mobile/sessions/{session_uuid}/feeds/front-burst")
    async def upload_front_burst(session_uuid: str, request: PresenceBurstUploadRequest):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        try:
            attempt = await service.upload_burst(session_uuid, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": attempt.model_dump()}

    @router.post("/mobile/sessions/{session_uuid}/feeds/front-burst/retry")
    async def upload_front_burst_retry(session_uuid: str, request: PresenceBurstUploadRequest):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        try:
            attempt = await service.upload_burst(session_uuid, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": attempt.model_dump()}

    @router.get("/mobile/sessions/{session_uuid}/instant-detection-status")
    async def get_detection_status(session_uuid: str):
        if not service.get_session(session_uuid):
            raise HTTPException(status_code=404, detail="Presence session not found")
        return {"success": True, "data": await service.get_detection_status(session_uuid)}

    @router.post("/mobile/sessions/{session_uuid}/qr-hit")
    async def submit_qr_hit(session_uuid: str, request: PresenceQrHitRequest):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        try:
            session = service.qr_hit(session_uuid, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": session.model_dump()}

    @router.post("/mobile/sessions/{session_uuid}/owner-qr-hit")
    async def submit_owner_qr_hit(
        session_uuid: str,
        request: PresenceOwnerQrHitRequest,
        current_user: dict = Depends(get_current_user),
    ):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        try:
            session = await service.owner_qr_hit_complete(session_uuid, request, current_user)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": session.model_dump()}

    @router.post("/mobile/sessions/{session_uuid}/bind-resources")
    async def bind_resources(session_uuid: str, request: BindResourcesRequest):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        try:
            session = service.bind_resources(session_uuid, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": session.model_dump()}

    @router.get("/mobile/sessions/{session_uuid}/result")
    async def get_result(
        session_uuid: str,
        current_user: dict = Depends(get_current_user),
    ):
        if session_uuid not in service.sessions:
            raise HTTPException(status_code=404, detail="Presence session not found")
        result = await service.get_result(session_uuid, current_user)
        return {"success": True, "data": result.model_dump()}

    @router.post("/qr/render")
    async def render_qr(
        request: PresenceQrRenderRequest,
        current_user: dict = Depends(get_current_user),
    ):
        await service.refresh_local_installation_reference(current_user)
        return {"success": True, "data": service.qr_render(request, current_user)}

    @router.post("/qr/render-owner")
    async def render_owner_qr(
        request: PresenceOwnerQrRenderRequest,
        current_user: dict = Depends(get_current_user),
    ):
        await service.refresh_local_installation_reference(current_user)
        return {"success": True, "data": service.render_owner_qr(request, current_user)}

    @router.get("/qr/current")
    async def get_current_qr(installation_uuid: str = "local-installation", device_reference: str | None = None):
        return {"success": True, "data": service.qr_current(installation_uuid, device_reference)}

    @router.post("/qr/validate")
    async def validate_qr(request: PresenceQrValidateRequest):
        return {"success": True, "data": service.qr_validate(request.qr_token)}

    @router.get("/cameras")
    async def list_cameras(current_user: dict = Depends(get_current_user)):
        return {"success": True, "data": {"items": await service.list_cameras(current_user)}}

    @router.post("/cameras/reserve")
    async def reserve_camera(
        request: ReserveResourceRequest,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            resource = await service.reserve_camera(request, current_user)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": resource.model_dump()}

    @router.post("/cameras/unreserve")
    async def unreserve_camera(
        request: UnreserveResourceRequest,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            result = service.unreserve_camera(request, current_user)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": result}

    @router.get("/collections")
    async def list_collections():
        return {"success": True, "data": {"items": [item.model_dump() for item in service.list_collections()]}}

    @router.post("/collections/reserve")
    async def reserve_collection(
        request: ReserveResourceRequest,
        current_user: dict = Depends(get_current_user),
    ):
        try:
            resource = await service.reserve_collection(request, current_user)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "data": resource.model_dump()}

    @router.get("/analytics/summary")
    async def analytics_summary():
        return {"success": True, "data": service.analytics_summary()}

    @router.get("/analytics/by-user")
    async def analytics_by_user():
        return {"success": True, "data": {"items": service.analytics_by_user()}}

    @router.get("/analytics/by-device")
    async def analytics_by_device():
        return {"success": True, "data": {"items": service.analytics_by_device()}}

    @router.get("/analytics/outcomes")
    async def analytics_outcomes():
        return {"success": True, "data": {"items": service.analytics_outcomes()}}

    @router.get("/analytics/by-policy-source")
    async def analytics_by_policy_source():
        return {"success": True, "data": {"items": service.analytics_by_policy_source()}}

    @router.get("/analytics/by-installation")
    async def analytics_by_installation():
        return {"success": True, "data": {"items": service.analytics_by_installation()}}

    @router.get("/analytics/by-session-mode")
    async def analytics_by_session_mode():
        return {"success": True, "data": {"items": service.analytics_by_session_mode()}}

    @router.get("/analytics/by-grant-type")
    async def analytics_by_grant_type():
        return {"success": True, "data": {"items": service.analytics_by_grant_type()}}

    @router.get("/analytics/by-reserved-collection")
    async def analytics_by_reserved_collection():
        return {"success": True, "data": {"items": service.analytics_by_reserved_collection()}}

    @router.get("/analytics/action-outcomes")
    async def analytics_action_outcomes():
        return {"success": True, "data": {"items": service.analytics_action_outcomes()}}

    @router.post("/analytics/repair")
    async def repair_analytics_metadata(current_user: dict = Depends(require_admin_user)):
        return {
            "success": True,
            "data": {
                **service.repair_analytics_metadata(),
                "requested_by": current_user.get("sub") or current_user.get("user_id"),
            },
        }

    return router


def build_internal_router(service: PresenceService) -> APIRouter:
    """Service-to-service router (no user-auth dependency).

    These endpoints are invoked by other platform services (e.g. the media
    service trigger executor), not by authenticated end users.
    """
    router = APIRouter()

    @router.post("/trigger-match")
    async def record_trigger_match(request: TriggerMatchRequest):
        try:
            session = await service.process_trigger_match(
                camera_device_id=request.camera_device_id,
                trigger_uuid=request.trigger_uuid,
                action_uuid=request.action_uuid,
                match_info=request.match_info,
            )
        except Exception as exc:  # noqa: BLE001 - surface as HTTP 500 service-to-service
            logger.exception("trigger-match processing failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"presence trigger-match failed: {exc}") from exc
        return {
            "success": True,
            "data": {
                "session_uuid": session.session_uuid,
                "decision": session.decision.value,
                "session_mode": session.session_mode.value,
                "grant_type": session.grant_type.value,
            },
        }

    return router

