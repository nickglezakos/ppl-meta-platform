from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import Any, Dict, List
from uuid import uuid4
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

from config import config
from models.presence_models import (
    PresenceActionPlan,
    PresenceAssuranceLevel,
    PresenceAuditLogTrace,
    BindResourcesRequest,
    CreatePresenceSessionRequest,
    PresenceIndividualGroupOption,
    PresenceDecisionRecord,
    PresenceExternalAssets,
    PresenceGrantType,
    PresenceGroupPolicy,
    PresenceAnalyticsEvent,
    PresencePolicyRule,
    PresenceBurstUploadRequest,
    PresenceDecisionState,
    PresenceDetectionAttempt,
    PresenceProfile,
    PresenceQrHitRequest,
    PresenceOwnerQrRenderRequest,
    PresenceOwnerQrHitRequest,
    PresenceQrRenderRequest,
    PresenceResource,
    PresenceResult,
    PresenceSession,
    PresenceSessionSettings,
    PresenceSessionMode,
    PresenceSessionTrace,
    PresenceSessionStatus,
    PresenceTriggerObservation,
    ResetInstallationReservationsRequest,
    ReserveResourceRequest,
    UnreserveResourceRequest,
    UpdateActivePresenceGroupRequest,
    UpdateInstallationSettingsRequest,
    UpdateInstallationPolicyRequest,
)
from .platform_clients import PlatformClients
from .presence_repository import PresenceRepository


class PresenceService:
    def __init__(self, platform_clients: PlatformClients | None = None) -> None:
        self.repository = PresenceRepository()
        self.sessions: Dict[str, PresenceSession] = self.repository.load_sessions()
        self.attempts: Dict[str, List[PresenceDetectionAttempt]] = self.repository.load_attempts()
        self.profiles: Dict[str, PresenceProfile] = self.repository.load_profiles()
        self.analytics_events: List[PresenceAnalyticsEvent] = self.repository.load_analytics_events()
        self.decision_history: List[PresenceDecisionRecord] = self.repository.load_decision_history()
        self._session_timeout_tasks: Dict[str, asyncio.Task[None]] = {}
        self._repair_terminal_session_metadata()
        self._backfill_analytics_event_metadata()
        self.qr_tokens: Dict[str, str] = {}
        self.cameras: Dict[str, PresenceResource] = self.repository.load_resources("camera")
        self.collections: Dict[str, PresenceResource] = self.repository.load_resources("collection")
        self.platform_clients = platform_clients or PlatformClients()
        self.installation_profile = self._load_or_create_installation_profile()
        for session in self.sessions.values():
            self.qr_tokens[session.qr_token] = session.session_uuid

    def _load_or_create_installation_profile(self) -> PresenceProfile:
        installation_profiles = [
            profile
            for profile in self.profiles.values()
            if profile.profile_type == "installation"
            and (profile.installation_uuid == "local-installation" or profile.display_name == "Local Installation")
        ]
        existing = max(
            installation_profiles,
            key=lambda profile: (
                isinstance(profile.metadata, dict) and "session_settings" in profile.metadata,
                profile.updated_at,
            ),
            default=None,
        )
        if existing is not None:
            self.profiles[existing.presence_profile_uuid] = existing
            return existing

        profile = PresenceProfile(
            presence_profile_uuid="installation-local-installation",
            profile_type="installation",
            installation_uuid="local-installation",
            display_name="Local Installation",
        )
        self.profiles[profile.presence_profile_uuid] = profile
        self.repository.save_profile(profile)
        return profile

    def get_current_user_profile(self, current_user: dict) -> dict:
        profile = self._get_or_create_user_profile(current_user=current_user)
        return {
            "user_uuid": profile.user_uuid,
            "presence_profile_uuid": profile.presence_profile_uuid,
            "presence_enabled": profile.status == "active",
            "group_uuid": self._active_presence_individual_group_id(),
            "resolved_camera_uuid": self._get_default_camera_id(),
            "resolved_collection_uuid": self._get_default_collection_id(),
            "detection_backend_mode": config.DETECTION_BACKEND_MODE,
        }

    def get_action_plan(self, session_uuid: str) -> PresenceActionPlan:
        session = self.sessions[session_uuid]
        self._sync_session_external_assets(session)
        trigger_observation = self._trigger_observation_for_session(session)
        matched_group_uuid = self._resolve_matched_group_uuid(session)
        trigger_type, action_type, policy_source = self._resolve_trigger_and_action(session)
        return PresenceActionPlan(
            session_uuid=session_uuid,
            session_mode=session.session_mode,
            assurance_level=session.assurance_level,
            grant_type=session.grant_type,
            matched_group_uuid=matched_group_uuid,
            decision=session.decision,
            policy_source=policy_source,
            trigger_type=trigger_type,
            action_type=action_type,
            action_execution_status=session.action_execution_status,
            external_assets=session.external_assets,
            trigger_observation=trigger_observation,
        )

    async def get_session_trace(self, session_uuid: str, current_user: dict) -> PresenceSessionTrace:
        session = self.sessions[session_uuid]
        self._sync_session_external_assets(session)
        action_plan = self.get_action_plan(session_uuid)
        decision_history = self.list_decision_history(session_uuid)
        audit_log = await self._get_audit_log_trace(session, current_user)
        return PresenceSessionTrace(
            session=session,
            action_plan=action_plan,
            decision_history=decision_history,
            audit_log=audit_log,
        )

    def list_decision_history(self, session_uuid: str) -> list[PresenceDecisionRecord]:
        return [
            record for record in self.decision_history
            if record.session_uuid == session_uuid
        ]

    def query_decision_history(
        self,
        *,
        session_uuid: str | None = None,
        user_uuid: str | None = None,
        installation_uuid: str | None = None,
        policy_source: str | None = None,
        limit: int | None = None,
    ) -> dict:
        items = sorted(
            self.decision_history,
            key=lambda record: record.created_at,
            reverse=True,
        )

        filtered: list[PresenceDecisionRecord] = []
        for record in items:
            if session_uuid and record.session_uuid != session_uuid:
                continue
            if user_uuid and record.user_uuid != user_uuid:
                continue
            if installation_uuid and record.installation_uuid != installation_uuid:
                continue
            if policy_source and record.policy_source != policy_source:
                continue
            filtered.append(record)
        total = len(filtered)
        if limit is not None:
            filtered = filtered[:limit]
        return {
            "items": filtered,
            "total": total,
            "returned": len(filtered),
            "limit": limit,
            "has_more": limit is not None and total > len(filtered),
        }

    async def query_session_traces(
        self,
        current_user: dict,
        *,
        session_uuid: str | None = None,
        user_uuid: str | None = None,
        installation_uuid: str | None = None,
        policy_source: str | None = None,
        limit: int | None = None,
    ) -> dict:
        sessions = sorted(
            self.sessions.values(),
            key=lambda session: session.updated_at,
            reverse=True,
        )

        matched_sessions = []
        for session in sessions:
            if session_uuid and session.session_uuid != session_uuid:
                continue
            if user_uuid and session.user_uuid != user_uuid:
                continue
            if installation_uuid and session.installation_uuid != installation_uuid:
                continue
            if policy_source and session.policy_source != policy_source:
                continue
            matched_sessions.append(session)

        total = len(matched_sessions)
        if limit is not None:
            matched_sessions = matched_sessions[:limit]

        traces = [
            await self.get_session_trace(session.session_uuid, current_user)
            for session in matched_sessions
        ]
        return {
            "items": traces,
            "total": total,
            "returned": len(traces),
            "limit": limit,
            "has_more": limit is not None and total > len(traces),
        }

    async def startup(self) -> None:
        from database import test_connection

        if not test_connection():
            raise RuntimeError("Presence database connection failed")
        await self.platform_clients.startup()
        self._schedule_existing_session_timeouts()

    async def shutdown(self) -> None:
        await self.platform_clients.shutdown()

    def get_current_installation_context(self) -> dict:
        reserved_camera = next(iter(self.cameras.values()), None)
        reserved_collection = next(iter(self.collections.values()), None)
        local_reference = self._local_installation_reference()
        return {
            "installation_uuid": self.installation_profile.installation_uuid,
            "presence_profile_uuid": self.installation_profile.presence_profile_uuid,
            "installation_name": self.installation_profile.display_name,
            "licence_status": local_reference.get("licence_status") or "unknown",
            "detection_backend_mode": config.DETECTION_BACKEND_MODE,
            "preferred_camera_types": config.PREFERRED_CAMERA_TYPES,
            "preferred_camera_names": config.PREFERRED_CAMERA_NAMES,
            "allowed_camera_statuses": config.ALLOWED_CAMERA_STATUSES,
            "installation_reference": local_reference,
            "active_presence_individual_group_id": self._active_presence_individual_group_id(),
            "active_presence_individual_group_name": self._active_presence_individual_group_name(),
            "group_policy": self._group_policy_from_profile(self.installation_profile),
            "session_settings": self._session_settings_from_profile(self.installation_profile).model_dump(),
            "reserved_camera_uuid": reserved_camera.platform_resource_uuid if reserved_camera else None,
            "reserved_collection_uuid": reserved_collection.platform_resource_uuid if reserved_collection else None,
            "reserved_camera": reserved_camera.model_dump() if reserved_camera else None,
            "reserved_collection": reserved_collection.model_dump() if reserved_collection else None,
        }

    async def list_available_individual_groups(self, current_user: dict) -> list[PresenceIndividualGroupOption]:
        token = current_user.get("token")
        if not token:
            return []
        groups = await self.platform_clients.list_individual_groups(token)
        items: list[PresenceIndividualGroupOption] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_id = group.get("id")
            group_name = group.get("name")
            if not group_id or not group_name:
                continue
            member_ids = group.get("member_ids") if isinstance(group.get("member_ids"), list) else []
            member_count = group.get("member_count")
            if not isinstance(member_count, int):
                member_count = len(member_ids)
            items.append(
                PresenceIndividualGroupOption(
                    individual_group_id=str(group_id),
                    name=str(group_name),
                    description=group.get("description") if isinstance(group.get("description"), str) else None,
                    member_count=member_count,
                )
            )
        return items

    async def update_active_presence_group(self, request: UpdateActivePresenceGroupRequest, current_user: dict) -> dict:
        token = current_user.get("token")
        if token:
            group_id, group_name = await self._resolve_or_create_active_individual_group(
                token=token,
                installation_uuid=request.installation_uuid,
                selected_group_id=request.individual_group_id,
                requested_group_name=request.group_name,
            )
            previous_group_id = self._active_presence_individual_group_id()
            metadata = {
                **(self.installation_profile.metadata or {}),
                "active_presence_individual_group_id": group_id,
                "active_presence_individual_group_name": group_name,
            }
            if previous_group_id != group_id:
                metadata.pop("presence_trigger_uuid", None)
                metadata.pop("presence_action_uuid", None)
                metadata.pop("presence_seed_member_id", None)
                metadata.pop("presence_seeded_at", None)
            self.installation_profile.installation_uuid = request.installation_uuid
            self.installation_profile.metadata = metadata
            self.installation_profile.updated_at = datetime.utcnow()
            self.profiles[self.installation_profile.presence_profile_uuid] = self.installation_profile
            self.repository.save_profile(self.installation_profile)
        return self.get_current_installation_context()

    def update_installation_policy(self, request: UpdateInstallationPolicyRequest) -> dict:
        self.installation_profile.installation_uuid = request.installation_uuid
        self.installation_profile.metadata = {
            **self.installation_profile.metadata,
            "action_policy": request.group_policy.model_dump(exclude_none=True),
        }
        self.installation_profile.updated_at = datetime.utcnow()
        self.profiles[self.installation_profile.presence_profile_uuid] = self.installation_profile
        self.repository.save_profile(self.installation_profile)
        return self.get_current_installation_context()

    def update_installation_settings(self, request: UpdateInstallationSettingsRequest) -> dict:
        self.installation_profile.installation_uuid = request.installation_uuid
        self.installation_profile.metadata = {
            **self.installation_profile.metadata,
            "session_settings": request.session_settings.model_dump(),
        }
        self.installation_profile.updated_at = datetime.utcnow()
        self.profiles[self.installation_profile.presence_profile_uuid] = self.installation_profile
        self.repository.save_profile(self.installation_profile)
        return self.get_current_installation_context()

    async def refresh_local_installation_reference(self, current_user: dict) -> dict:
        token = current_user.get("token")
        if not token:
            return self._local_installation_reference()

        reference = await self.platform_clients.get_local_installation_reference(token)
        installation_uuid = reference.get("installation_uuid") or self.installation_profile.installation_uuid or "local-installation"
        reference = {key: value for key, value in reference.items() if value not in (None, "")}

        self.installation_profile.installation_uuid = installation_uuid
        self.installation_profile.metadata = {
            **self.installation_profile.metadata,
            "installation_reference": reference,
        }
        if reference.get("node_name"):
            self.installation_profile.display_name = str(reference["node_name"])
        self.installation_profile.updated_at = datetime.utcnow()
        self.profiles[self.installation_profile.presence_profile_uuid] = self.installation_profile
        self.repository.save_profile(self.installation_profile)
        return reference

    def reset_installation_reservations(
        self,
        request: ResetInstallationReservationsRequest,
    ) -> dict:
        self._clear_existing_resources("camera", request.installation_uuid)
        self._clear_existing_resources("collection", request.installation_uuid)
        return {
            "installation_uuid": request.installation_uuid,
            "cleared": True,
            "reserved_camera_uuid": None,
            "reserved_collection_uuid": None,
        }

    async def create_session(self, request: CreatePresenceSessionRequest, current_user: dict) -> PresenceSession:
        profile = self._get_or_create_user_profile(current_user=current_user, device_uuid=request.device_uuid)
        session_settings = self._current_session_settings()
        await self._ensure_default_resources(current_user)
        session = PresenceSession(
            device_uuid=request.device_uuid,
            user_uuid=profile.user_uuid or "unknown-user",
            session_mode=request.session_mode,
            assurance_level=self._assurance_level_for_mode(request.session_mode),
            grant_type=self._grant_type_for_mode(request.session_mode),
            expires_at=datetime.utcnow() + timedelta(seconds=session_settings.session_timeout_seconds),
            status=(
                PresenceSessionStatus.CREATED
                if request.session_mode in {PresenceSessionMode.QR_ONLY, PresenceSessionMode.CAMERA_ONLY}
                else PresenceSessionStatus.AWAITING_FRONT_BURST
            ),
            resolved_camera_uuid=self._get_default_camera_id(),
            resolved_collection_uuid=self._get_default_collection_id(),
        )
        await self._ensure_presence_automation_assets(session, current_user)
        self._sync_session_external_assets(session)
        self.sessions[session.session_uuid] = session
        self.qr_tokens[session.qr_token] = session.session_uuid
        self.repository.save_session(session)
        self._schedule_session_timeout(session)

        if request.session_mode == PresenceSessionMode.CAMERA_ONLY:
            await self._start_camera_only_detection(session)

        return session

    async def _start_camera_only_detection(self, session: PresenceSession) -> None:
        if self._remaining_attempt_capacity(session) <= 0:
            self._fail_session(session, "presence_attempt_limit_reached")
            return

        await self._start_live_detection_attempt(session, capture_phase="camera_only_initial")

    async def _start_verified_detection(self, session: PresenceSession) -> None:
        if self._remaining_attempt_capacity(session) <= 0:
            self._fail_session(session, "presence_attempt_limit_reached")
            return

        await self._start_live_detection_attempt(session, capture_phase="qr_plus_camera_initial")

    async def _start_live_detection_attempt(self, session: PresenceSession, *, capture_phase: str) -> None:
        attempt = PresenceDetectionAttempt(
            session_uuid=session.session_uuid,
            attempt_index=len(self.attempts.get(session.session_uuid, [])) + 1,
            capture_phase=capture_phase,
        )
        self.attempts.setdefault(session.session_uuid, []).append(attempt)

        camera_id = session.resolved_camera_uuid or self._get_default_camera_id()
        if not camera_id:
            attempt.instant_detection_status = "camera_unbound"
            session.detection_status = "camera_unbound"
            session.updated_at = datetime.utcnow()
            self.repository.save_attempt(attempt)
            self.repository.save_session(session)
            return

        try:
            await self.platform_clients.connect_camera(camera_id)
            result = await self.platform_clients.start_instant_detection(camera_id)
            attempt.instant_detection_request_id = result.get(
                "session_uuid",
                attempt.instant_detection_request_id,
            )
            attempt.instant_detection_status = "started"
            session.instant_detection_request_id = attempt.instant_detection_request_id
            session.detection_status = "started"
            session.resolved_camera_uuid = camera_id
        except httpx.HTTPError:
            attempt.instant_detection_status = "start_failed"
            session.detection_status = "start_failed"

        session.updated_at = datetime.utcnow()
        self.repository.save_attempt(attempt)
        self.repository.save_session(session)

    def get_session(self, session_uuid: str) -> PresenceSession | None:
        session = self.sessions.get(session_uuid)
        if session:
            self._apply_session_limits(session)
            self._sync_session_external_assets(session)
        return session

    async def upload_burst(self, session_uuid: str, request: PresenceBurstUploadRequest) -> PresenceDetectionAttempt:
        session = self.sessions[session_uuid]
        self._apply_session_limits(session)
        if session.status == PresenceSessionStatus.FAILED:
            raise ValueError(self._human_reason_for_code(session.failure_reason_code))
        if self._remaining_attempt_capacity(session) <= 0:
            self._fail_session(session, "presence_attempt_limit_reached")
            raise ValueError(self._human_reason_for_code(session.failure_reason_code))

        attempt = PresenceDetectionAttempt(
            session_uuid=session_uuid,
            attempt_index=len(self.attempts.get(session_uuid, [])) + 1,
            capture_phase=request.capture_phase,
        )
        self.attempts.setdefault(session_uuid, []).append(attempt)
        session.status = PresenceSessionStatus.BURST_RECEIVED
        session.detection_status = "submitted"

        camera_id = session.resolved_camera_uuid or self._get_default_camera_id()
        if camera_id:
            if self._should_simulate_detection():
                self._mark_detection_completed(session, attempt, request.capture_phase, camera_id, simulated=True)
            try:
                if not self._should_simulate_detection():
                    result = await self.platform_clients.start_instant_detection(camera_id)
                    attempt.instant_detection_request_id = result.get("session_uuid", attempt.instant_detection_request_id)
                    attempt.instant_detection_status = "started"
                    session.instant_detection_request_id = attempt.instant_detection_request_id
                    session.detection_status = "started"
                    session.resolved_camera_uuid = camera_id
            except httpx.HTTPError:
                if self._should_auto_fallback_detection():
                    self._mark_detection_completed(session, attempt, request.capture_phase, camera_id, simulated=True)
                else:
                    attempt.instant_detection_status = "start_failed"
                    session.detection_status = "start_failed"
        else:
            attempt.instant_detection_status = "camera_unbound"
            session.detection_status = "camera_unbound"

        session.updated_at = datetime.utcnow()
        self.repository.save_attempt(attempt)
        self.repository.save_session(session)
        return attempt

    def qr_render(self, request: PresenceQrRenderRequest, current_user: dict | None = None) -> dict:
        session = self._find_latest_session_for_device(request.device_reference)
        qr_token = session.qr_token if session else str(uuid4())
        created_at = datetime.utcnow()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        if session:
            self.qr_tokens[qr_token] = session.session_uuid
        payload = self._build_station_qr_payload(
            installation_uuid=request.installation_uuid,
            device_reference=request.device_reference,
            device_display_name=request.device_display_name,
            location=request.location,
            qr_token=qr_token,
            session=session,
            current_user=current_user,
            created_at=created_at,
            expires_at=expires_at,
        )
        return {
            "qr_token": qr_token,
            "expires_at": expires_at.isoformat(),
            "payload": payload,
        }

    def qr_current(self, installation_uuid: str = "local-installation", device_reference: str | None = None) -> dict:
        session = self._find_latest_session_for_device(device_reference)
        if not session:
            return {
                "found": False,
                "installation_uuid": installation_uuid,
                "device_reference": device_reference,
                "qr_token": None,
                "expires_at": None,
                "payload": None,
                "session_uuid": None,
                "session_status": None,
                "qr_status": None,
            }

        self.qr_tokens[session.qr_token] = session.session_uuid
        payload = self._build_station_qr_payload(
            installation_uuid=installation_uuid,
            device_reference=device_reference,
            device_display_name=None,
            location=None,
            qr_token=session.qr_token,
            session=session,
            current_user=None,
            created_at=session.created_at,
            expires_at=session.expires_at,
        )
        return {
            "found": True,
            "installation_uuid": installation_uuid,
            "device_reference": device_reference,
            "qr_token": session.qr_token,
            "expires_at": session.expires_at.isoformat(),
            "payload": payload,
            "session_uuid": session.session_uuid,
            "session_status": session.status,
            "qr_status": session.qr_status,
        }

    def qr_validate(self, qr_token: str) -> dict:
        session_uuid = self.qr_tokens.get(qr_token)
        session = self.sessions.get(session_uuid) if session_uuid else None
        return {
            "valid": session_uuid is not None,
            "session_uuid": session_uuid,
            "installation_uuid": session.installation_uuid if session else self.installation_profile.installation_uuid,
            "qr_type": "station_challenge",
            "reference_source": "node_installation_cache",
        }

    def render_owner_qr(self, request: PresenceOwnerQrRenderRequest, current_user: dict) -> dict:
        created_at = datetime.utcnow()
        owner_user_uuid = request.owner_user_uuid or current_user.get("sub") or current_user.get("email") or "demo-user"
        owner_display_name = request.owner_display_name or current_user.get("username") or current_user.get("email") or "Presence Owner"
        owner_email = current_user.get("email")
        payload = {
            "schema": "ppl_meta_presence_qr/v1",
            "qr_type": "owner_identity",
            "challenge_uuid": str(uuid4()),
            "created_at": created_at.isoformat() + "Z",
            "installation": self._installation_reference_block(request.installation_uuid),
            "owner": {
                "owner_user_uuid": owner_user_uuid,
                "owner_email": owner_email,
                "owner_display_name": owner_display_name,
                "owner_profile_uuid": self._get_or_create_user_profile(current_user=current_user).presence_profile_uuid,
                "owner_type": "approved_owner" if owner_email and owner_email == self._local_installation_reference().get("approved_owner_email") else "user",
            },
            "integrity": self._integrity_block(),
        }
        return {"payload": payload}

    def _build_station_qr_payload(
        self,
        *,
        installation_uuid: str,
        device_reference: str | None,
        device_display_name: str | None,
        location: dict | None,
        qr_token: str,
        session: PresenceSession | None,
        current_user: dict | None,
        created_at: datetime,
        expires_at: datetime,
    ) -> dict:
        return {
            "schema": "ppl_meta_presence_qr/v1",
            "qr_type": "station_challenge",
            "challenge_uuid": str(uuid4()),
            "qr_token": qr_token,
            "created_at": created_at.isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
            "installation": self._installation_reference_block(installation_uuid),
            "device": {
                "device_reference": device_reference,
                "display_name": device_display_name or device_reference or "mobile-presence-station",
            },
            "actor": self._actor_block(session, current_user),
            "location": location,
            "integrity": self._integrity_block(),
            "session_uuid": session.session_uuid if session else None,
        }

    def _actor_block(self, session: PresenceSession | None, current_user: dict | None) -> dict:
        if current_user:
            return {
                "user_uuid": current_user.get("sub") or current_user.get("email"),
                "user_email": current_user.get("email"),
            }
        user_profile = None
        if session:
            user_profile = next(
                (profile for profile in self.profiles.values() if profile.profile_type == "user" and profile.user_uuid == session.user_uuid),
                None,
            )
        actor_email = None
        if isinstance(user_profile.metadata, dict):
            actor_email = user_profile.metadata.get("email")
        return {
            "user_uuid": session.user_uuid if session else None,
            "user_email": actor_email or (user_profile.display_name if user_profile and "@" in user_profile.display_name else None),
        }

    def _installation_reference_block(self, installation_uuid: str | None) -> dict:
        local_reference = self._local_installation_reference()
        payload = {"installation_uuid": installation_uuid or self.installation_profile.installation_uuid or "local-installation"}
        for key in ("application_key", "licence_status", "approved_owner_email", "authority_entitlement_uuid", "tenant_name", "node_uuid", "node_name"):
            value = local_reference.get(key)
            if value:
                payload[key] = value
        if len(payload) > 1:
            payload["reference_source"] = "node_installation_cache"
        return payload

    def _local_installation_reference(self) -> dict:
        metadata = self.installation_profile.metadata if isinstance(self.installation_profile.metadata, dict) else {}
        installation_reference = metadata.get("installation_reference")
        if isinstance(installation_reference, dict):
            return installation_reference
        local_keys = {
            key: metadata.get(key)
            for key in (
                "application_key",
                "licence_status",
                "approved_owner_email",
                "authority_entitlement_uuid",
                "tenant_name",
                "node_uuid",
                "node_name",
            )
            if metadata.get(key)
        }
        return local_keys

    def _integrity_block(self) -> dict:
        return {
            "algorithm": "unsigned-local-reference",
            "key_id": "presence-local-reference",
            "signature": None,
        }

    def qr_hit(self, session_uuid: str, request: PresenceQrHitRequest) -> PresenceSession:
        session = self.sessions[session_uuid]
        self._apply_session_limits(session)
        if session.status == PresenceSessionStatus.FAILED:
            raise ValueError(self._human_reason_for_code(session.failure_reason_code))
        self.qr_tokens[request.qr_token] = session_uuid
        session.qr_status = "scanned"
        session.status = PresenceSessionStatus.QR_RESOLVED
        session.updated_at = datetime.utcnow()
        self.repository.save_session(session)
        return session

    def owner_qr_hit(self, session_uuid: str, request: PresenceOwnerQrHitRequest) -> PresenceSession:
        session = self.sessions[session_uuid]
        self._apply_session_limits(session)
        if session.status == PresenceSessionStatus.FAILED:
            raise ValueError(self._human_reason_for_code(session.failure_reason_code))

        payload = request.qr_payload if isinstance(request.qr_payload, dict) else {}
        if payload.get("qr_type") != "owner_identity":
            raise ValueError("Scanned QR is not an owner identity QR")

        installation = payload.get("installation") if isinstance(payload.get("installation"), dict) else {}
        payload_installation_uuid = installation.get("installation_uuid")
        if payload_installation_uuid and payload_installation_uuid != request.installation_uuid:
            raise ValueError("Owner QR installation does not match the current installation")

        owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
        session.qr_status = "scanned"
        session.status = PresenceSessionStatus.QR_RESOLVED
        session.updated_at = datetime.utcnow()
        user_profile = self._get_or_create_user_profile()
        if owner:
            user_profile.metadata = {
                **user_profile.metadata,
                "scanned_owner_user_uuid": owner.get("owner_user_uuid"),
                "scanned_owner_email": owner.get("owner_email"),
                "scanned_owner_display_name": owner.get("owner_display_name"),
                "scanned_owner_type": owner.get("owner_type"),
            }
            user_profile.updated_at = datetime.utcnow()
            self.repository.save_profile(user_profile)
        self.repository.save_session(session)
        return session

    async def owner_qr_hit_complete(
        self,
        session_uuid: str,
        request: PresenceOwnerQrHitRequest,
        current_user: dict,
    ) -> PresenceSession:
        session = self.owner_qr_hit(session_uuid, request)
        if (
            session.session_mode == PresenceSessionMode.QR_ONLY
            and session.decision == PresenceDecisionState.PENDING
        ):
            await self._grant_qr_check_in(session, current_user)
        return session

    def bind_resources(self, session_uuid: str, request: BindResourcesRequest) -> PresenceSession:
        session = self.sessions[session_uuid]
        camera_resource = self._find_reserved_resource(self.cameras, request.camera_uuid)
        if not camera_resource:
            raise ValueError(f"Camera '{request.camera_uuid}' is not reserved for presence")

        collection_resource = self._find_reserved_resource(self.collections, request.collection_uuid)
        if not collection_resource:
            raise ValueError(f"Collection '{request.collection_uuid}' is not reserved for presence")

        session.resolved_camera_uuid = camera_resource.platform_resource_uuid
        session.resolved_collection_uuid = collection_resource.platform_resource_uuid
        session.updated_at = datetime.utcnow()
        self.repository.save_session(session)
        return session

    async def reserve_camera(self, request: ReserveResourceRequest, current_user: dict) -> PresenceResource:
        self._validate_reservation_mode(request.mode, "camera")
        token = current_user.get("token")
        if not token:
            raise ValueError("Missing auth token for camera reservation")

        platform_cameras = await self.platform_clients.list_cameras(token)
        selected_camera = next(
            (camera for camera in platform_cameras if camera.get("device_id") == request.resource_uuid),
            None,
        )
        if not selected_camera:
            raise ValueError(f"Camera '{request.resource_uuid}' not found in platform cameras service")

        resource = PresenceResource(
            resource_type="camera",
            installation_uuid=request.installation_uuid,
            platform_resource_uuid=request.resource_uuid,
            metadata={
                "name": selected_camera.get("name"),
                "camera_type": selected_camera.get("camera_type"),
                "status": selected_camera.get("status"),
                "reservation_mode": request.mode,
                "reserved_by": "presence",
            },
        )
        self._clear_existing_resources("camera", request.installation_uuid)
        self.cameras[resource.resource_uuid] = resource
        self.repository.save_resource(resource)

        collection = await self.platform_clients.get_collection_by_camera_device_id(request.resource_uuid, token)
        if collection:
            collection_resource = PresenceResource(
                resource_type="collection",
                installation_uuid=request.installation_uuid,
                platform_resource_uuid=collection.get("uuid"),
                metadata={
                    "name": collection.get("name"),
                    "camera_device_id": collection.get("camera_device_id"),
                    "reservation_mode": "bind",
                    "reserved_by": "presence",
                    "auto_bound_from_camera_uuid": request.resource_uuid,
                },
            )
            self._clear_existing_resources("collection", request.installation_uuid)
            self.collections[collection_resource.resource_uuid] = collection_resource
            self.repository.save_resource(collection_resource)

        return resource

    def unreserve_camera(self, request: UnreserveResourceRequest, _current_user: dict) -> dict:
        target = self._find_reserved_resource(self.cameras, request.resource_uuid)
        if not target:
            raise ValueError(f"Camera '{request.resource_uuid}' is not reserved for presence")

        stale_keys = [target.resource_uuid]
        del self.cameras[target.resource_uuid]

        linked_collection_keys = [
            key
            for key, resource in self.collections.items()
            if resource.installation_uuid == target.installation_uuid
            and resource.metadata.get("auto_bound_from_camera_uuid") == request.resource_uuid
        ]
        for key in linked_collection_keys:
            del self.collections[key]
        stale_keys.extend(linked_collection_keys)

        self.repository.delete_resources(stale_keys)
        return {
            "installation_uuid": target.installation_uuid,
            "resource_uuid": request.resource_uuid,
            "released_collection_count": len(linked_collection_keys),
        }

    async def reserve_collection(self, request: ReserveResourceRequest, current_user: dict) -> PresenceResource:
        self._validate_reservation_mode(request.mode, "collection")
        token = current_user.get("token")
        if not token:
            raise ValueError("Missing auth token for collection reservation")

        platform_collections = await self.platform_clients.list_collections(token)
        selected_collection = next(
            (
                collection
                for collection in platform_collections
                if str(collection.get("uuid")) == request.resource_uuid
            ),
            None,
        )
        if not selected_collection:
            raise ValueError(
                f"Collection '{request.resource_uuid}' not found in platform media service"
            )

        resource = PresenceResource(
            resource_type="collection",
            installation_uuid=request.installation_uuid,
            platform_resource_uuid=request.resource_uuid,
            metadata={
                "name": selected_collection.get("name"),
                "camera_device_id": selected_collection.get("camera_device_id"),
                "reservation_mode": request.mode,
                "reserved_by": "presence",
            },
        )
        self._clear_existing_resources("collection", request.installation_uuid)
        self.collections[resource.resource_uuid] = resource
        self.repository.save_resource(resource)
        return resource

    async def list_cameras(self, current_user: dict) -> list[dict]:
        token = current_user.get("token")
        if not token:
            return []

        platform_cameras = await self.platform_clients.list_cameras(token)
        reserved_device_ids = {
            resource.platform_resource_uuid for resource in self.cameras.values()
        }
        items = []
        for camera in platform_cameras:
            reserved_resource = self._find_reserved_resource(self.cameras, str(camera.get("device_id")))
            items.append(
                {
                    "device_id": camera.get("device_id"),
                    "name": camera.get("name"),
                    "camera_type": camera.get("camera_type"),
                    "status": camera.get("status"),
                    "reserved_for_presence": camera.get("device_id") in reserved_device_ids,
                    "reserved_resource_uuid": reserved_resource.resource_uuid if reserved_resource else None,
                    "reserved_installation_uuid": reserved_resource.installation_uuid if reserved_resource else None,
                    "linked_collection_uuid": self._linked_collection_for_camera(str(camera.get("device_id"))),
                }
            )
        return items

    def list_collections(self) -> list[PresenceResource]:
        return list(self.collections.values())

    async def get_detection_status(self, session_uuid: str) -> dict:
        session = self.sessions[session_uuid]
        self._apply_session_limits(session)
        attempts = self.attempts.get(session_uuid, [])
        latest_attempt = attempts[-1] if attempts else None
        external_result = None

        terminal_or_unavailable_states = {"start_failed", "camera_unbound", "status_error"}
        if latest_attempt and latest_attempt.instant_detection_status in terminal_or_unavailable_states:
            session.detection_status = latest_attempt.instant_detection_status
            self.repository.save_session(session)
            return {
                "session_uuid": session_uuid,
                "latest_attempt_index": latest_attempt.attempt_index,
                "instant_detection_status": session.detection_status,
                "instant_detection_request_id": session.instant_detection_request_id,
                "presence_decision_state": session.decision,
                "instant_detection_result_payload": latest_attempt.instant_detection_result_payload,
                "detection_backend_mode": self._backend_mode_for_attempt(latest_attempt),
                "simulated_detection": self._attempt_is_simulated(latest_attempt),
            }

        if latest_attempt and latest_attempt.instant_detection_status == "completed":
            session.detection_status = "completed"
            self.repository.save_session(session)
            return {
                "session_uuid": session_uuid,
                "latest_attempt_index": latest_attempt.attempt_index,
                "instant_detection_status": session.detection_status,
                "instant_detection_request_id": session.instant_detection_request_id,
                "presence_decision_state": session.decision,
                "instant_detection_result_payload": latest_attempt.instant_detection_result_payload,
                "detection_backend_mode": self._backend_mode_for_attempt(latest_attempt),
                "simulated_detection": self._attempt_is_simulated(latest_attempt),
            }

        if session.resolved_camera_uuid:
            try:
                external_result = await self.platform_clients.get_instant_detection_results(
                    session.resolved_camera_uuid
                )
                if not self._external_detection_succeeded(external_result):
                    session.detection_status = "pending_results"
                else:
                    session.detection_status = "completed"
                    if latest_attempt:
                        latest_attempt.instant_detection_status = "completed"
                        latest_attempt.instant_detection_result_payload = self._normalize_external_detection_result(
                            external_result,
                            session,
                        )
                        self.repository.save_attempt(latest_attempt)
            except httpx.HTTPError:
                session.detection_status = "status_error"

        self.repository.save_session(session)

        return {
            "session_uuid": session_uuid,
            "latest_attempt_index": latest_attempt.attempt_index if latest_attempt else 0,
            "instant_detection_status": session.detection_status,
            "instant_detection_request_id": session.instant_detection_request_id,
            "presence_decision_state": session.decision,
            "instant_detection_result_payload": latest_attempt.instant_detection_result_payload if latest_attempt else None,
            "detection_backend_mode": self._backend_mode_for_attempt(latest_attempt),
            "simulated_detection": self._attempt_is_simulated(latest_attempt),
        }

    async def get_result(self, session_uuid: str, current_user: dict) -> PresenceResult:
        session = self.sessions[session_uuid]
        self._apply_session_limits(session)
        self._sync_session_external_assets(session)
        latest_attempt = self._latest_attempt(session_uuid)
        live_detection_ready = session.status == PresenceSessionStatus.QR_RESOLVED or session.session_mode == PresenceSessionMode.CAMERA_ONLY

        if session.status == PresenceSessionStatus.FAILED or session.decision == PresenceDecisionState.FAILED:
            return PresenceResult(
                session_uuid=session_uuid,
                session_mode=session.session_mode,
                assurance_level=session.assurance_level,
                grant_type=session.grant_type,
                status=session.status,
                decision=session.decision,
                reason_code=session.failure_reason_code or "presence_failed",
                matched_group_uuid=session.matched_group_uuid,
                policy_source=session.policy_source,
                trigger_type=session.trigger_type,
                action_type=session.action_type,
                action_execution_status=session.action_execution_status,
                resolved_camera_uuid=session.resolved_camera_uuid,
                resolved_collection_uuid=session.resolved_collection_uuid,
            )

        if (
            session.session_mode == PresenceSessionMode.QR_ONLY
            and session.qr_status == "scanned"
            and session.decision == PresenceDecisionState.PENDING
        ):
            await self._grant_qr_check_in(session, current_user)

        if (
            session.session_mode == PresenceSessionMode.QR_PLUS_CAMERA
            and live_detection_ready
            and session.decision == PresenceDecisionState.PENDING
            and latest_attempt is None
        ):
            await self._start_verified_detection(session)
            latest_attempt = self._latest_attempt(session_uuid)

        if live_detection_ready and session.decision == PresenceDecisionState.PENDING:
            await self._advance_live_detection(session)
            latest_attempt = self._latest_attempt(session_uuid)

        simulated_detection = self._attempt_is_simulated(latest_attempt)
        if (
            live_detection_ready
            and session.detection_status == "completed"
            and session.decision == PresenceDecisionState.PENDING
        ):
            seeded_member = await self._ensure_presence_group_seed_member(session, latest_attempt, current_user)
            if simulated_detection:
                await self._grant_presence_match(session, simulated_detection, current_user, reason_code="presence_match_simulated")
            else:
                trigger_match = await self._resolve_trigger_backed_match(session, latest_attempt, current_user)
                if trigger_match:
                    if session.resolved_camera_uuid:
                        await self._cleanup_detection_camera(session.resolved_camera_uuid)
                    await self._grant_presence_match(
                        session,
                        simulated_detection,
                        current_user,
                        reason_code="presence_ppl_match",
                        trigger_match=trigger_match,
                    )
                else:
                    if seeded_member:
                        await self._start_confirmation_detection(session)
                    if session.decision == PresenceDecisionState.PENDING and self._remaining_attempt_capacity(session) <= 0:
                        self._fail_session(session, "presence_attempt_limit_reached")
                    session.trigger_type, session.action_type, session.policy_source = self._resolve_trigger_and_action(session)
                    session.action_execution_status = "pending_trigger_match"
                    if session.status != PresenceSessionStatus.FAILED and session.detection_status == "completed":
                        session.detection_status = "awaiting_trigger_match"
                    session.updated_at = datetime.utcnow()
                    self.repository.save_session(session)
        elif live_detection_ready and session.decision == PresenceDecisionState.PENDING:
            session.trigger_type, session.action_type, session.policy_source = self._resolve_trigger_and_action(session)
            session.action_execution_status = session.action_execution_status or "pending"
            self.repository.save_session(session)
        return PresenceResult(
            session_uuid=session_uuid,
            session_mode=session.session_mode,
            assurance_level=session.assurance_level,
            grant_type=session.grant_type,
            status=session.status,
            decision=session.decision,
            reason_code=(
                "presence_check_in"
                if session.decision == PresenceDecisionState.GRANTED and session.session_mode == PresenceSessionMode.QR_ONLY
                else
                "presence_match_simulated"
                if session.decision == PresenceDecisionState.GRANTED and simulated_detection
                else "presence_ppl_match"
                if session.decision == PresenceDecisionState.GRANTED
                else session.failure_reason_code
                if session.decision == PresenceDecisionState.FAILED
                else "pending"
            ),
            matched_group_uuid=session.matched_group_uuid,
            policy_source=session.policy_source,
            detection_backend_mode=self._backend_mode_for_attempt(latest_attempt),
            simulated_detection=simulated_detection,
            trigger_type=session.trigger_type,
            action_type=session.action_type,
            action_execution_status=session.action_execution_status,
            action_log_uuid=getattr(session, "action_log_uuid", None),
            executed_at=session.executed_at,
            resolved_camera_uuid=session.resolved_camera_uuid,
            resolved_collection_uuid=session.resolved_collection_uuid,
            external_assets=session.external_assets,
            trigger_observation=self._trigger_observation_for_session(session),
        )

    async def _advance_live_detection(self, session: PresenceSession) -> None:
        if self._should_simulate_detection() or not session.resolved_camera_uuid:
            return

        latest_attempt = self._latest_attempt(session.session_uuid)
        if not latest_attempt:
            return

        camera_id = session.resolved_camera_uuid
        try:
            external_result = await self.platform_clients.get_instant_detection_results(camera_id)
        except httpx.HTTPError:
            session.detection_status = "status_error"
            self.repository.save_session(session)
            return

        if self._external_detection_succeeded(external_result):
            session.detection_status = "completed"
            latest_attempt.instant_detection_status = "completed"
            latest_attempt.instant_detection_result_payload = self._normalize_external_detection_result(
                external_result,
                session,
            )
            self.repository.save_attempt(latest_attempt)
            self.repository.save_session(session)
            return

        retry_count = self._detection_retry_count(latest_attempt)
        try:
            status_payload = await self.platform_clients.get_instant_detection_status()
        except httpx.HTTPError:
            session.detection_status = "status_error"
            latest_attempt.instant_detection_status = "status_error"
            latest_attempt.instant_detection_result_payload = {
                "success": False,
                "camera_id": camera_id,
                "session_uuid": session.session_uuid,
                "simulated": False,
                "retry_count": retry_count,
                "raw_payload": external_result,
                "failure_reason": "instant_detection_status_error",
            }
            session.updated_at = datetime.utcnow()
            self.repository.save_attempt(latest_attempt)
            self.repository.save_session(session)
            return
        camera_status = self._instant_detection_camera_status(status_payload, camera_id)

        if camera_status.get("running"):
            session.detection_status = "pending_results"
            self.repository.save_session(session)
            return

        max_retries = 3
        if retry_count >= max_retries:
            latest_attempt.instant_detection_status = "results_timeout"
            latest_attempt.instant_detection_result_payload = {
                "success": False,
                "camera_id": camera_id,
                "session_uuid": session.session_uuid,
                "simulated": False,
                "retry_count": retry_count,
                "raw_payload": external_result,
                "failure_reason": "instant_detection_results_timeout",
            }
            session.detection_status = "results_timeout"
            session.decision = PresenceDecisionState.FAILED
            session.action_execution_status = "failed"
            session.updated_at = datetime.utcnow()
            self.repository.save_attempt(latest_attempt)
            self.repository.save_session(session)
            await self._cleanup_detection_camera(camera_id)
            return

        try:
            await self.platform_clients.connect_camera(camera_id)
            restart_result = await self.platform_clients.start_instant_detection(camera_id)
        except httpx.HTTPError:
            latest_attempt.instant_detection_status = "start_failed"
            latest_attempt.instant_detection_result_payload = {
                "success": False,
                "camera_id": camera_id,
                "session_uuid": session.session_uuid,
                "simulated": False,
                "retry_count": retry_count,
                "raw_payload": external_result,
                "failure_reason": "instant_detection_restart_failed",
            }
            session.detection_status = "start_failed"
            session.instant_detection_request_id = None
            session.updated_at = datetime.utcnow()
            self.repository.save_attempt(latest_attempt)
            self.repository.save_session(session)
            return
        latest_attempt.instant_detection_request_id = restart_result.get(
            "session_uuid",
            latest_attempt.instant_detection_request_id,
        )
        latest_attempt.instant_detection_status = "restarted"
        latest_attempt.instant_detection_result_payload = {
            "success": False,
            "camera_id": camera_id,
            "session_uuid": session.session_uuid,
            "simulated": False,
            "retry_count": retry_count + 1,
            "raw_payload": external_result,
            "failure_reason": "instant_detection_results_pending",
        }
        session.instant_detection_request_id = latest_attempt.instant_detection_request_id
        session.detection_status = "started"
        session.updated_at = datetime.utcnow()
        self.repository.save_attempt(latest_attempt)
        self.repository.save_session(session)

    async def _cleanup_detection_camera(self, camera_id: str) -> None:
        try:
            await self.platform_clients.stop_instant_detection(camera_id)
        except httpx.HTTPError as exc:
            logger.warning("Failed to stop instant detection for %s during cleanup: %s", camera_id, exc)

        try:
            await self.platform_clients.disconnect_camera(camera_id)
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.warning("Failed to disconnect camera %s during cleanup: %s", camera_id, exc)

    async def _ensure_presence_automation_assets(self, session: PresenceSession, current_user: dict) -> None:
        token = current_user.get("token")
        if not token or not session.user_uuid or not session.resolved_camera_uuid:
            return

        metadata = dict(self.installation_profile.metadata or {})
        changed = False

        individual_group_id = await self._ensure_external_individual_group(session, token)
        if metadata.get("active_presence_individual_group_id") != individual_group_id:
            metadata["active_presence_individual_group_id"] = individual_group_id
            metadata["active_presence_individual_group_name"] = self._active_presence_individual_group_name() or "presence"
            changed = True

        action_uuid = metadata.get("presence_action_uuid")
        if not action_uuid:
            action_uuid = await self._ensure_external_presence_action(session, token)
            metadata["presence_action_uuid"] = action_uuid
            changed = True

        trigger_uuid = metadata.get("presence_trigger_uuid")
        if not trigger_uuid:
            trigger_uuid = await self._ensure_external_presence_trigger(
                session,
                token,
                individual_group_id,
                action_uuid,
            )
            metadata["presence_trigger_uuid"] = trigger_uuid
            metadata["presence_trigger_threshold"] = 0.6
            changed = True

        if changed:
            self.installation_profile.metadata = metadata
            self.installation_profile.updated_at = datetime.utcnow()
            self.repository.save_profile(self.installation_profile)

        self._sync_session_external_assets(session)

    async def _ensure_external_individual_group(self, session: PresenceSession, token: str) -> str:
        group_id, group_name = await self._resolve_or_create_active_individual_group(
            token=token,
            installation_uuid=session.installation_uuid,
            requested_group_name=self._active_presence_individual_group_name() or "presence",
        )
        current_group_id = self._active_presence_individual_group_id()
        current_group_name = self._active_presence_individual_group_name()
        if current_group_id != group_id or current_group_name != group_name:
            self.installation_profile.metadata = {
                **(self.installation_profile.metadata or {}),
                "active_presence_individual_group_id": group_id,
                "active_presence_individual_group_name": group_name,
            }
            self.installation_profile.updated_at = datetime.utcnow()
            self.repository.save_profile(self.installation_profile)
        return group_id

    async def _ensure_external_presence_action(self, session: PresenceSession, token: str) -> str:
        expected_name = self._presence_action_name(session.user_uuid)
        actions = await self.platform_clients.list_user_actions(token)
        existing = next((action for action in actions if action.get("name") == expected_name), None)
        if existing and existing.get("uuid"):
            return str(existing["uuid"])

        payload = {
            "name": expected_name,
            "description": f"Presence automation action for user {session.user_uuid}",
            "action_type": "log",
            "action_config": json.dumps(
                {
                    "severity": "info",
                    "data": {
                        "category": "presence",
                        "tags": ["presence", "auto", f"user:{session.user_uuid}"],
                    },
                }
            ),
            "is_active": True,
            "created_by": str(session.user_uuid),
        }
        response = await self.platform_clients.create_user_action(token, payload)
        action_uuid = response.get("uuid") if isinstance(response, dict) else None
        if not action_uuid:
            raise RuntimeError("Presence action creation did not return a uuid")
        return str(action_uuid)

    async def _ensure_external_presence_trigger(
        self,
        session: PresenceSession,
        token: str,
        individual_group_id: str,
        action_uuid: str,
    ) -> str:
        expected_name = self._presence_trigger_name(session.user_uuid)
        triggers = await self.platform_clients.list_triggers(token)
        existing = next((trigger for trigger in triggers if trigger.get("name") == expected_name), None)
        if existing and existing.get("uuid"):
            return str(existing["uuid"])

        payload = {
            "demographic_conditions": [],
            "time_span": "any",
            "camera_device_id": session.resolved_camera_uuid,
            "camera_name": session.resolved_camera_uuid,
            "action_uuid": action_uuid,
            "tracking_duration": "10 minutes",
            "is_active": True,
            "cooldown_seconds": 60,
            "name": expected_name,
            "description": f"Presence ppl_match trigger for user {session.user_uuid}",
            "trigger_mode": "ppl_match",
            "ppl_match_group_id": individual_group_id,
            "ppl_match_similarity_threshold": 0.6,
            "ppl_match_top_k": 1,
            "ppl_match_negate": False,
        }
        response = await self.platform_clients.create_trigger(token, payload)
        trigger_uuid = response.get("uuid") if isinstance(response, dict) else None
        if not trigger_uuid:
            raise RuntimeError("Presence trigger creation did not return a uuid")
        return str(trigger_uuid)

    async def _ensure_presence_group_seed_member(
        self,
        session: PresenceSession,
        latest_attempt: PresenceDetectionAttempt | None,
        current_user: dict,
    ) -> bool:
        if not latest_attempt or not latest_attempt.instant_detection_result_payload:
            return False

        token = current_user.get("token")
        if not token:
            return False

        metadata = dict(self.installation_profile.metadata or {})
        group_id = metadata.get("active_presence_individual_group_id")
        if not group_id:
            return False

        members = await self.platform_clients.get_individual_group_members(token, group_id)
        if members:
            return False

        identity_ids = self._extract_detection_identity_ids(latest_attempt.instant_detection_result_payload)
        if not identity_ids:
            return False

        await self.platform_clients.add_individual_group_members(
            token,
            group_id,
            {"individual_ids": [identity_ids[0]]},
        )
        metadata["presence_seed_member_id"] = identity_ids[0]
        metadata["presence_seeded_at"] = datetime.utcnow().isoformat()
        self.installation_profile.metadata = metadata
        self.installation_profile.updated_at = datetime.utcnow()
        self.repository.save_profile(self.installation_profile)
        self._sync_session_external_assets(session)
        return True

    def _external_assets_for_user(self, user_uuid: str | None) -> PresenceExternalAssets | None:
        metadata = self.installation_profile.metadata if isinstance(self.installation_profile.metadata, dict) else None
        if not metadata:
            return None
        assets = PresenceExternalAssets(
            individual_group_id=metadata.get("active_presence_individual_group_id"),
            trigger_uuid=metadata.get("presence_trigger_uuid"),
            action_uuid=metadata.get("presence_action_uuid"),
        )
        if not any([assets.individual_group_id, assets.trigger_uuid, assets.action_uuid]):
            return None
        return assets

    def _sync_session_external_assets(self, session: PresenceSession) -> None:
        session.external_assets = self._external_assets_for_user(session.user_uuid)

    async def _resolve_trigger_backed_match(
        self,
        session: PresenceSession,
        latest_attempt: PresenceDetectionAttempt | None,
        current_user: dict,
    ) -> dict | None:
        token = current_user.get("token")
        if not token:
            return None

        metadata = self.installation_profile.metadata if isinstance(self.installation_profile.metadata, dict) else None
        if not metadata:
            return None

        trigger_uuid = metadata.get("presence_trigger_uuid")
        if not trigger_uuid:
            return None

        try:
            trigger = await self.platform_clients.get_trigger(token, trigger_uuid)
        except httpx.HTTPError:
            return None

        match_info = trigger.get("last_match_info") if isinstance(trigger, dict) else None
        last_matched_at = self._parse_datetime(trigger.get("last_matched_at")) if isinstance(trigger, dict) else None
        if not isinstance(match_info, dict) or not last_matched_at:
            return None
        if last_matched_at < session.created_at:
            return None
        if match_info.get("mode") != "ppl_match":
            return None

        best_match = match_info.get("best_match") if isinstance(match_info.get("best_match"), dict) else {}
        if not best_match:
            return None

        attempt_identity_ids = set(self._extract_detection_identity_ids(latest_attempt.instant_detection_result_payload if latest_attempt else None))
        source_mvr_uuid = best_match.get("source_mvr_uuid")
        if attempt_identity_ids and source_mvr_uuid and source_mvr_uuid not in attempt_identity_ids:
            return None

        return {
            "trigger_uuid": trigger_uuid,
            "matched_at": last_matched_at.isoformat(),
            "match_info": match_info,
            "matched_member_uuid": best_match.get("matched_member_uuid"),
            "source_mvr_uuid": source_mvr_uuid,
            "similarity_score": best_match.get("similarity_score"),
        }

    async def _grant_presence_match(
        self,
        session: PresenceSession,
        simulated_detection: bool,
        current_user: dict,
        reason_code: str,
        trigger_match: dict | None = None,
    ) -> None:
        if self._session_has_terminal_resolution(session):
            return
        self._cancel_session_timeout(session.session_uuid)
        session.status = PresenceSessionStatus.COMPLETED
        session.decision = PresenceDecisionState.GRANTED
        session.failure_reason_code = None
        session.retry_allowed = False
        session.detection_status = "completed"
        session.instant_detection_request_id = None
        session.matched_group_uuid = self._resolve_matched_group_uuid(session)
        session.trigger_type, session.action_type, session.policy_source = self._resolve_trigger_and_action(session)
        if trigger_match:
            session.policy_source = "platform_trigger"
        session.action_execution_status, action_log_uuid = await self._execute_action(
            session,
            simulated_detection,
            current_user,
        )
        session.action_log_uuid = action_log_uuid
        session.executed_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        self.repository.save_session(session)
        self._record_decision(session, simulated_detection, reason_code)
        if not any(event.session_uuid == session.session_uuid for event in self.analytics_events):
            event = PresenceAnalyticsEvent(
                session_uuid=session.session_uuid,
                session_mode=session.session_mode,
                assurance_level=session.assurance_level,
                grant_type=session.grant_type,
                installation_uuid=session.installation_uuid,
                user_uuid=session.user_uuid,
                device_uuid=session.device_uuid,
                outcome=session.decision.value,
                reason_code=reason_code,
                matched_group_uuid=session.matched_group_uuid,
                policy_source=session.policy_source,
                trigger_type=session.trigger_type,
                action_type=session.action_type,
                action_execution_status=session.action_execution_status,
                resolved_camera_uuid=session.resolved_camera_uuid,
                resolved_collection_uuid=session.resolved_collection_uuid,
            )
            self.analytics_events.append(event)
            self.repository.save_analytics_event(event)

    async def _grant_qr_check_in(self, session: PresenceSession, current_user: dict) -> None:
        if self._session_has_terminal_resolution(session):
            return
        self._cancel_session_timeout(session.session_uuid)
        session.status = PresenceSessionStatus.COMPLETED
        session.decision = PresenceDecisionState.GRANTED
        session.failure_reason_code = None
        session.retry_allowed = False
        session.detection_status = "completed"
        session.instant_detection_request_id = None
        session.trigger_type, session.action_type, session.policy_source = self._resolve_trigger_and_action(session)
        session.action_execution_status, action_log_uuid = await self._execute_action(
            session,
            simulated_detection=False,
            current_user=current_user,
        )
        session.action_log_uuid = action_log_uuid
        session.executed_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        self.repository.save_session(session)
        self._record_decision(session, simulated_detection=False, reason_code="presence_check_in")
        if not any(event.session_uuid == session.session_uuid for event in self.analytics_events):
            event = PresenceAnalyticsEvent(
                session_uuid=session.session_uuid,
                session_mode=session.session_mode,
                assurance_level=session.assurance_level,
                grant_type=session.grant_type,
                installation_uuid=session.installation_uuid,
                user_uuid=session.user_uuid,
                device_uuid=session.device_uuid,
                outcome=session.decision.value,
                reason_code="presence_check_in",
                matched_group_uuid=session.matched_group_uuid,
                policy_source=session.policy_source,
                trigger_type=session.trigger_type,
                action_type=session.action_type,
                action_execution_status=session.action_execution_status,
                resolved_camera_uuid=session.resolved_camera_uuid,
                resolved_collection_uuid=session.resolved_collection_uuid,
            )
            self.analytics_events.append(event)
            self.repository.save_analytics_event(event)

    async def _start_confirmation_detection(self, session: PresenceSession) -> bool:
        if not session.resolved_camera_uuid:
            return False

        attempts = self.attempts.get(session.session_uuid, [])
        if any(attempt.capture_phase == "confirmation" for attempt in attempts):
            return False

        confirmation_attempt = PresenceDetectionAttempt(
            session_uuid=session.session_uuid,
            attempt_index=len(attempts) + 1,
            capture_phase="confirmation",
        )
        self.attempts.setdefault(session.session_uuid, []).append(confirmation_attempt)

        try:
            await self.platform_clients.connect_camera(session.resolved_camera_uuid)
            result = await self.platform_clients.start_instant_detection(session.resolved_camera_uuid)
            confirmation_attempt.instant_detection_request_id = result.get(
                "session_uuid",
                confirmation_attempt.instant_detection_request_id,
            )
            confirmation_attempt.instant_detection_status = "started"
            session.instant_detection_request_id = confirmation_attempt.instant_detection_request_id
            session.detection_status = "confirmation_started"
        except httpx.HTTPError:
            confirmation_attempt.instant_detection_status = "start_failed"
            session.detection_status = "confirmation_start_failed"

        session.updated_at = datetime.utcnow()
        self.repository.save_attempt(confirmation_attempt)
        self.repository.save_session(session)
        return True

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def analytics_summary(self) -> dict:
        total = sum(len(attempts) for attempts in self.attempts.values())
        granted = len([event for event in self.analytics_events if event.outcome == PresenceDecisionState.GRANTED.value])
        failed = len([event for event in self.analytics_events if event.outcome == PresenceDecisionState.FAILED.value])
        retries = len([a for attempts in self.attempts.values() for a in attempts if a.attempt_index > 1])
        return {
            "attempts": total,
            "granted": granted,
            "denied": 0,
            "failed": failed,
            "retry_count": retries,
        }

    def analytics_by_user(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            aggregates[event.user_uuid] = aggregates.get(event.user_uuid, 0) + 1
        return [{"user_uuid": user_uuid, "event_count": count} for user_uuid, count in aggregates.items()]

    def analytics_by_device(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            aggregates[event.device_uuid] = aggregates.get(event.device_uuid, 0) + 1
        return [{"device_uuid": device_uuid, "event_count": count} for device_uuid, count in aggregates.items()]

    def analytics_outcomes(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            aggregates[event.outcome] = aggregates.get(event.outcome, 0) + 1
        return [{"outcome": outcome, "event_count": count} for outcome, count in aggregates.items()]

    def analytics_by_policy_source(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            key = event.policy_source or "unknown"
            aggregates[key] = aggregates.get(key, 0) + 1
        return [
            {"policy_source": policy_source, "event_count": count}
            for policy_source, count in aggregates.items()
        ]

    def analytics_by_installation(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            key = event.installation_uuid or "unknown"
            aggregates[key] = aggregates.get(key, 0) + 1
        return [
            {"installation_uuid": installation_uuid, "event_count": count}
            for installation_uuid, count in aggregates.items()
        ]

    def analytics_by_session_mode(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            key = event.session_mode.value if hasattr(event.session_mode, "value") else str(event.session_mode or "unknown")
            aggregates[key] = aggregates.get(key, 0) + 1
        return [
            {"session_mode": session_mode, "event_count": count}
            for session_mode, count in aggregates.items()
        ]

    def analytics_by_grant_type(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            key = event.grant_type.value if hasattr(event.grant_type, "value") else str(event.grant_type or "unknown")
            aggregates[key] = aggregates.get(key, 0) + 1
        return [
            {"grant_type": grant_type, "event_count": count}
            for grant_type, count in aggregates.items()
        ]

    def analytics_by_reserved_collection(self) -> list[dict]:
        aggregates: Dict[str, int] = {}
        for event in self.analytics_events:
            key = event.resolved_collection_uuid or "unbound"
            aggregates[key] = aggregates.get(key, 0) + 1
        return [
            {"resolved_collection_uuid": resolved_collection_uuid, "event_count": count}
            for resolved_collection_uuid, count in aggregates.items()
        ]

    def analytics_action_outcomes(self) -> list[dict]:
        aggregates: Dict[tuple[str, str], int] = {}
        for event in self.analytics_events:
            action_type = event.action_type or "unknown"
            action_execution_status = event.action_execution_status or "unknown"
            key = (action_type, action_execution_status)
            aggregates[key] = aggregates.get(key, 0) + 1
        return [
            {
                "action_type": action_type,
                "action_execution_status": action_execution_status,
                "event_count": count,
            }
            for (action_type, action_execution_status), count in aggregates.items()
        ]

    def repair_analytics_metadata(self) -> dict:
        repaired_session_count = self._repair_terminal_session_metadata()
        repaired_event_count = self._backfill_analytics_event_metadata()
        return {
            "analytics_event_count": len(self.analytics_events),
            "repaired_session_count": repaired_session_count,
            "repaired_event_count": repaired_event_count,
            "policy_source_breakdown": self.analytics_by_policy_source(),
            "installation_breakdown": self.analytics_by_installation(),
            "session_mode_breakdown": self.analytics_by_session_mode(),
            "grant_type_breakdown": self.analytics_by_grant_type(),
            "reserved_collection_breakdown": self.analytics_by_reserved_collection(),
            "action_outcome_breakdown": self.analytics_action_outcomes(),
        }

    def _backfill_analytics_event_metadata(self) -> int:
        decision_by_session = {
            record.session_uuid: record
            for record in self.decision_history
        }
        updated_events: list[PresenceAnalyticsEvent] = []

        for event in self.analytics_events:
            decision_record = decision_by_session.get(event.session_uuid)
            session = self.sessions.get(event.session_uuid)
            changed = False

            if event.policy_source is None:
                event.policy_source = (
                    getattr(decision_record, "policy_source", None)
                    or getattr(session, "policy_source", None)
                )
                changed = event.policy_source is not None

            if event.trigger_type is None:
                event.trigger_type = (
                    getattr(decision_record, "trigger_type", None)
                    or getattr(session, "trigger_type", None)
                )
                changed = changed or event.trigger_type is not None

            if event.action_type is None:
                event.action_type = (
                    getattr(decision_record, "action_type", None)
                    or getattr(session, "action_type", None)
                )
                changed = changed or event.action_type is not None

            if changed:
                updated_events.append(event)

        for event in updated_events:
            self.repository.save_analytics_event(event)
        return len(updated_events)

    def _repair_terminal_session_metadata(self) -> int:
        latest_decision_by_session: Dict[str, PresenceDecisionRecord] = {}
        for record in self.decision_history:
            existing = latest_decision_by_session.get(record.session_uuid)
            if existing is None or record.created_at >= existing.created_at:
                latest_decision_by_session[record.session_uuid] = record

        repaired_sessions: list[PresenceSession] = []
        for session in self.sessions.values():
            latest_decision = latest_decision_by_session.get(session.session_uuid)
            changed = False

            if latest_decision and latest_decision.decision == PresenceDecisionState.GRANTED:
                if session.decision != PresenceDecisionState.GRANTED:
                    session.decision = PresenceDecisionState.GRANTED
                    changed = True
                if session.status != PresenceSessionStatus.COMPLETED:
                    session.status = PresenceSessionStatus.COMPLETED
                    changed = True
                if session.failure_reason_code is not None:
                    session.failure_reason_code = None
                    changed = True
                if session.detection_status != "completed":
                    session.detection_status = "completed"
                    changed = True
                if session.retry_allowed:
                    session.retry_allowed = False
                    changed = True
            elif latest_decision and latest_decision.decision == PresenceDecisionState.FAILED:
                if session.decision != PresenceDecisionState.FAILED:
                    session.decision = PresenceDecisionState.FAILED
                    changed = True
                if session.status != PresenceSessionStatus.FAILED:
                    session.status = PresenceSessionStatus.FAILED
                    changed = True
                if session.failure_reason_code != latest_decision.reason_code:
                    session.failure_reason_code = latest_decision.reason_code
                    changed = True
                if session.detection_status != latest_decision.reason_code:
                    session.detection_status = latest_decision.reason_code
                    changed = True
                if session.retry_allowed:
                    session.retry_allowed = False
                    changed = True

            if changed:
                session.updated_at = datetime.utcnow()
                repaired_sessions.append(session)

        for session in repaired_sessions:
            self.repository.save_session(session)
        return len(repaired_sessions)

    def _get_default_camera_id(self) -> str | None:
        reserved_camera = next(iter(self.cameras.values()), None)
        return reserved_camera.platform_resource_uuid if reserved_camera else None

    def _get_default_collection_id(self) -> str | None:
        reserved_collection = next(iter(self.collections.values()), None)
        return reserved_collection.platform_resource_uuid if reserved_collection else None

    def _clear_existing_resources(self, resource_type: str, installation_uuid: str) -> None:
        resource_map = self.cameras if resource_type == "camera" else self.collections
        stale_keys = [
            key
            for key, resource in resource_map.items()
            if resource.installation_uuid == installation_uuid
        ]
        for key in stale_keys:
            del resource_map[key]
        self.repository.delete_resources(stale_keys)

    async def _ensure_default_resources(self, current_user: dict) -> None:
        if self._get_default_camera_id() and self._get_default_collection_id():
            return

        token = current_user.get("token")
        if not token:
            return

        platform_cameras = await self.platform_clients.list_cameras(token)
        if not platform_cameras:
            return

        preferred_camera = self._select_preferred_camera(platform_cameras)
        if not preferred_camera:
            return

        await self.reserve_camera(
            ReserveResourceRequest(
                installation_uuid=self.installation_profile.installation_uuid or "local-installation",
                resource_uuid=preferred_camera.get("device_id"),
            ),
            current_user,
        )

    def _select_preferred_camera(self, platform_cameras: List[dict]) -> dict | None:
        eligible_cameras = [
            camera
            for camera in platform_cameras
            if self._camera_status_allowed(camera)
        ]
        if not eligible_cameras:
            eligible_cameras = platform_cameras

        named_camera = self._select_camera_by_name(eligible_cameras)
        if named_camera:
            return named_camera

        for camera_type in config.PREFERRED_CAMERA_TYPES:
            for camera in eligible_cameras:
                if str(camera.get("camera_type", "")).upper() == camera_type:
                    return camera
        return eligible_cameras[0] if eligible_cameras else None

    def _select_camera_by_name(self, platform_cameras: List[dict]) -> dict | None:
        if not config.PREFERRED_CAMERA_NAMES:
            return None

        for preferred_name in config.PREFERRED_CAMERA_NAMES:
            for camera in platform_cameras:
                camera_name = str(camera.get("name", "")).lower()
                device_id = str(camera.get("device_id", "")).lower()
                if preferred_name in camera_name or preferred_name == device_id:
                    return camera
        return None

    def _camera_status_allowed(self, camera: dict) -> bool:
        status = str(camera.get("status", "")).lower()
        if not config.ALLOWED_CAMERA_STATUSES:
            return True
        return status in config.ALLOWED_CAMERA_STATUSES

    def _resolve_matched_group_uuid(self, session: PresenceSession) -> str | None:
        return self._active_presence_individual_group_id()

    def _resolve_trigger_and_action(self, session: PresenceSession) -> tuple[str | None, str | None, str | None]:
        policy_rule = self._resolve_group_policy_rule(session)
        if policy_rule:
            return policy_rule.trigger_type, policy_rule.action_type, "group_policy"

        installation_policy_rule = self._resolve_installation_policy_rule(session)
        if installation_policy_rule:
            return installation_policy_rule.trigger_type, installation_policy_rule.action_type, "installation_policy"

        if session.decision == PresenceDecisionState.GRANTED:
            if session.session_mode == PresenceSessionMode.QR_ONLY:
                return "presence_check_in", "presence_log", "default_policy"
            if session.session_mode == PresenceSessionMode.CAMERA_ONLY:
                return "presence_match", "presence_grant", "default_policy"
            if session.session_mode == PresenceSessionMode.QR_PLUS_CAMERA:
                return "presence_verified_match", "presence_grant", "default_policy"
            return "presence_match", "presence_grant", "default_policy"
        if session.decision == PresenceDecisionState.RETRY_REQUIRED:
            return "presence_retry_required", "presence_notify", "default_policy"
        if session.decision == PresenceDecisionState.DENIED:
            return "presence_no_match", "presence_deny", "default_policy"
        if session.decision == PresenceDecisionState.FAILED:
            return "presence_failed", "presence_notify", "default_policy"
        return None, None, None

    def _session_settings_from_profile(self, profile: PresenceProfile) -> PresenceSessionSettings:
        settings = profile.metadata.get("session_settings") if isinstance(profile.metadata, dict) else None
        if not isinstance(settings, dict):
            return PresenceSessionSettings()
        try:
            return PresenceSessionSettings.model_validate(settings)
        except Exception:
            return PresenceSessionSettings()

    def _current_session_settings(self) -> PresenceSessionSettings:
        return self._session_settings_from_profile(self.installation_profile)

    def _remaining_attempt_capacity(self, session: PresenceSession) -> int:
        max_attempts = max(1, self._current_session_settings().max_unsuccessful_attempts)
        return max_attempts - len(self.attempts.get(session.session_uuid, []))

    def _apply_session_limits(self, session: PresenceSession) -> None:
        if session.decision == PresenceDecisionState.GRANTED:
            return
        now = datetime.utcnow()
        if session.expires_at <= now:
            self._fail_session(session, "presence_session_expired")
            return
        if session.decision == PresenceDecisionState.PENDING and self._remaining_attempt_capacity(session) <= 0:
            self._fail_session(session, "presence_attempt_limit_reached")

    def _session_has_terminal_resolution(self, session: PresenceSession) -> bool:
        return session.decision in {PresenceDecisionState.GRANTED, PresenceDecisionState.FAILED}

    def _fail_session(self, session: PresenceSession, reason_code: str) -> None:
        if self._session_has_terminal_resolution(session):
            return
        camera_id = session.resolved_camera_uuid
        self._cancel_session_timeout(session.session_uuid)
        session.status = PresenceSessionStatus.FAILED
        session.decision = PresenceDecisionState.FAILED
        session.failure_reason_code = reason_code
        session.retry_allowed = False
        session.trigger_type, session.action_type, session.policy_source = self._resolve_trigger_and_action(session)
        session.action_execution_status = "failed_user_alert_required"
        session.detection_status = reason_code
        session.instant_detection_request_id = None
        session.updated_at = datetime.utcnow()
        self.repository.save_session(session)
        self._record_decision(session, simulated_detection=False, reason_code=reason_code)
        if camera_id:
            self._schedule_detection_cleanup(camera_id)

    def _schedule_existing_session_timeouts(self) -> None:
        for session in self.sessions.values():
            if session.decision == PresenceDecisionState.GRANTED:
                continue
            if session.status in {PresenceSessionStatus.COMPLETED, PresenceSessionStatus.FAILED}:
                continue
            self._schedule_session_timeout(session)

    def _schedule_session_timeout(self, session: PresenceSession) -> None:
        if session.decision == PresenceDecisionState.GRANTED:
            return
        if session.status in {PresenceSessionStatus.COMPLETED, PresenceSessionStatus.FAILED}:
            return

        self._cancel_session_timeout(session.session_uuid)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop available to schedule timeout for session %s", session.session_uuid)
            return

        self._session_timeout_tasks[session.session_uuid] = loop.create_task(
            self._enforce_session_timeout_after_delay(session.session_uuid)
        )

    def _cancel_session_timeout(self, session_uuid: str) -> None:
        task = self._session_timeout_tasks.pop(session_uuid, None)
        if task and not task.done():
            task.cancel()

    async def _enforce_session_timeout_after_delay(self, session_uuid: str) -> None:
        try:
            while True:
                session = self.sessions.get(session_uuid)
                if session is None:
                    return
                if session.decision == PresenceDecisionState.GRANTED:
                    return
                if session.status in {PresenceSessionStatus.COMPLETED, PresenceSessionStatus.FAILED}:
                    return

                remaining_seconds = (session.expires_at - datetime.utcnow()).total_seconds()
                if remaining_seconds <= 0:
                    self._fail_session(session, "presence_session_expired")
                    return

                await asyncio.sleep(min(remaining_seconds, 5.0))
        except asyncio.CancelledError:
            return
        finally:
            current_task = self._session_timeout_tasks.get(session_uuid)
            if current_task is asyncio.current_task():
                self._session_timeout_tasks.pop(session_uuid, None)

    def _schedule_detection_cleanup(self, camera_id: str) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop available to clean up detection camera %s", camera_id)
            return
        loop.create_task(self._cleanup_detection_camera(camera_id))

    def _human_reason_for_code(self, reason_code: str | None) -> str:
        if reason_code == "presence_session_expired":
            return "Presence session expired before a successful match was completed."
        if reason_code == "presence_attempt_limit_reached":
            return "Presence session reached the maximum number of unsuccessful attempts."
        return "Presence session failed."

    def _group_policy_from_profile(self, profile: PresenceProfile) -> PresenceGroupPolicy | None:
        policy = profile.metadata.get("action_policy") if isinstance(profile.metadata, dict) else None
        if not isinstance(policy, dict):
            return None
        return PresenceGroupPolicy.model_validate(policy)

    def _resolve_group_policy_rule(self, session: PresenceSession) -> PresencePolicyRule | None:
        matched_group_uuid = self._resolve_matched_group_uuid(session)
        if not matched_group_uuid:
            return None

        profile = self.profiles.get(matched_group_uuid)
        if not profile:
            return None

        group_policy = self._group_policy_from_profile(profile)
        if not group_policy:
            return None

        mode_specific_rule = self._mode_specific_policy_rule(group_policy, session)
        if mode_specific_rule:
            return mode_specific_rule

        return getattr(group_policy, session.decision.value, None)

    def _resolve_installation_policy_rule(self, session: PresenceSession) -> PresencePolicyRule | None:
        installation_policy = self._group_policy_from_profile(self.installation_profile)
        if not installation_policy:
            return None

        mode_specific_rule = self._mode_specific_policy_rule(installation_policy, session)
        if mode_specific_rule:
            return mode_specific_rule
        return getattr(installation_policy, session.decision.value, None)

    def _mode_specific_policy_rule(
        self,
        group_policy: PresenceGroupPolicy,
        session: PresenceSession,
    ) -> PresencePolicyRule | None:
        mode_policy = None
        if session.session_mode == PresenceSessionMode.QR_ONLY:
            mode_policy = group_policy.qr_only
        elif session.session_mode == PresenceSessionMode.CAMERA_ONLY:
            mode_policy = group_policy.camera_only
        elif session.session_mode == PresenceSessionMode.QR_PLUS_CAMERA:
            mode_policy = group_policy.qr_plus_camera

        if not isinstance(mode_policy, dict):
            return None
        return mode_policy.get(session.decision.value)

    async def _get_audit_log_trace(
        self,
        session: PresenceSession,
        current_user: dict,
    ) -> PresenceAuditLogTrace | None:
        if not session.action_log_uuid:
            return None

        token = current_user.get("token")
        if not token:
            return PresenceAuditLogTrace(
                log_uuid=session.action_log_uuid,
                found=False,
                error="missing_auth_token",
            )

        try:
            payload = await self.platform_clients.get_audit_log(token, session.action_log_uuid)
            return PresenceAuditLogTrace(
                log_uuid=session.action_log_uuid,
                found=True,
                payload=payload,
            )
        except httpx.HTTPStatusError as exc:
            error = f"http_{exc.response.status_code}"
            return PresenceAuditLogTrace(
                log_uuid=session.action_log_uuid,
                found=False,
                error=error,
            )
        except httpx.HTTPError:
            return PresenceAuditLogTrace(
                log_uuid=session.action_log_uuid,
                found=False,
                error="communications_unavailable",
            )

    async def _execute_action(
        self,
        session: PresenceSession,
        simulated_detection: bool,
        current_user: dict,
    ) -> tuple[str, str | None]:
        if not session.action_type:
            return "not_applicable", None
        if simulated_detection:
            return "executed_simulated", None

        token = current_user.get("token")
        if not token:
            return "execution_skipped_missing_token", None

        assets = session.external_assets or self._external_assets_for_user(session.user_uuid)
        trigger_uuid = assets.trigger_uuid if assets else None
        configured_action_uuid = assets.action_uuid if assets else None
        trigger = self.platform_clients.trigger_lookup.get(trigger_uuid or "") if trigger_uuid else None
        configured_action_uuids = []
        configured_action_names = []
        if isinstance(trigger, dict):
            trigger_action_uuids = trigger.get("action_uuids") or []
            if not trigger_action_uuids and trigger.get("action_uuid"):
                trigger_action_uuids = [trigger.get("action_uuid")]
            configured_action_uuids = [str(item) for item in trigger_action_uuids if item]

            trigger_action_names = trigger.get("action_names") or []
            if not trigger_action_names and trigger.get("action_name"):
                trigger_action_names = [trigger.get("action_name")]
            configured_action_names = [str(item) for item in trigger_action_names if item]

        if configured_action_uuid and configured_action_uuid not in configured_action_uuids:
            configured_action_uuids.append(configured_action_uuid)
            action = self.platform_clients.action_lookup.get(configured_action_uuid)
            if isinstance(action, dict) and action.get("name"):
                configured_action_names.append(str(action["name"]))

        try:
            response = await self.platform_clients.create_audit_log(
                token,
                {
                    "event_type": session.action_type,
                    "event_source": "ppl-meta-presence",
                    "event_data": {
                        "session_uuid": session.session_uuid,
                        "trigger_type": session.trigger_type,
                        "trigger_uuid": trigger_uuid,
                        "configured_action_uuid": configured_action_uuid,
                        "configured_action_uuids": configured_action_uuids,
                        "configured_action_names": configured_action_names,
                        "matched_group_uuid": session.matched_group_uuid,
                        "resolved_camera_uuid": session.resolved_camera_uuid,
                        "resolved_collection_uuid": session.resolved_collection_uuid,
                    },
                    "user_id": session.user_uuid,
                    "severity": "info",
                },
            )
            return "executed", str(response.get("log_uuid")) if isinstance(response, dict) else None
        except (httpx.HTTPError, HTTPException, ValueError, TypeError):
            return "execution_failed", None

    def _record_decision(
        self,
        session: PresenceSession,
        simulated_detection: bool,
        reason_code: str,
    ) -> None:
        existing = next(
            (
                record for record in self.decision_history
                if record.session_uuid == session.session_uuid and record.decision == session.decision
            ),
            None,
        )
        if existing:
            existing.reason_code = reason_code
            existing.session_mode = session.session_mode
            existing.assurance_level = session.assurance_level
            existing.grant_type = session.grant_type
            existing.matched_group_uuid = session.matched_group_uuid
            existing.policy_source = session.policy_source
            existing.trigger_type = session.trigger_type
            existing.action_type = session.action_type
            existing.action_execution_status = session.action_execution_status
            existing.action_log_uuid = session.action_log_uuid
            existing.simulated_detection = simulated_detection
            existing.resolved_camera_uuid = session.resolved_camera_uuid
            existing.resolved_collection_uuid = session.resolved_collection_uuid
            self.repository.save_decision_record(existing)
            return

        decision_record = PresenceDecisionRecord(
            session_uuid=session.session_uuid,
            session_mode=session.session_mode,
            assurance_level=session.assurance_level,
            grant_type=session.grant_type,
            installation_uuid=session.installation_uuid,
            user_uuid=session.user_uuid,
            device_uuid=session.device_uuid,
            decision=session.decision,
            reason_code=reason_code,
            matched_group_uuid=session.matched_group_uuid,
            policy_source=session.policy_source,
            trigger_type=session.trigger_type,
            action_type=session.action_type,
            action_execution_status=session.action_execution_status,
            action_log_uuid=session.action_log_uuid,
            simulated_detection=simulated_detection,
            resolved_camera_uuid=session.resolved_camera_uuid,
            resolved_collection_uuid=session.resolved_collection_uuid,
        )
        self.decision_history.append(decision_record)
        self.repository.save_decision_record(decision_record)

    def _assurance_level_for_mode(self, session_mode: PresenceSessionMode) -> PresenceAssuranceLevel:
        if session_mode == PresenceSessionMode.QR_ONLY:
            return PresenceAssuranceLevel.LOW
        if session_mode == PresenceSessionMode.CAMERA_ONLY:
            return PresenceAssuranceLevel.MEDIUM
        return PresenceAssuranceLevel.HIGH

    def _grant_type_for_mode(self, session_mode: PresenceSessionMode) -> PresenceGrantType:
        if session_mode == PresenceSessionMode.QR_ONLY:
            return PresenceGrantType.CHECK_IN
        if session_mode == PresenceSessionMode.CAMERA_ONLY:
            return PresenceGrantType.PRESENCE_MATCH
        return PresenceGrantType.VERIFIED_PRESENCE

    def _active_presence_individual_group_id(self) -> str | None:
        metadata = self.installation_profile.metadata or {}
        value = metadata.get("active_presence_individual_group_id")
        return value if isinstance(value, str) and value else None

    def _active_presence_individual_group_name(self) -> str | None:
        metadata = self.installation_profile.metadata or {}
        value = metadata.get("active_presence_individual_group_name")
        return value.strip() if isinstance(value, str) and value.strip() else None

    async def _resolve_or_create_active_individual_group(
        self,
        token: str,
        installation_uuid: str | None,
        selected_group_id: str | None = None,
        requested_group_name: str | None = None,
    ) -> tuple[str, str]:
        groups = await self.platform_clients.list_individual_groups(token)
        if selected_group_id:
            existing_by_id = next((group for group in groups if str(group.get("id")) == selected_group_id), None)
            if existing_by_id and existing_by_id.get("id") and existing_by_id.get("name"):
                return str(existing_by_id["id"]), str(existing_by_id["name"])

        effective_name = (requested_group_name or self._active_presence_individual_group_name() or "presence").strip() or "presence"
        existing_by_name = next(
            (group for group in groups if str(group.get("name", "")).strip().lower() == effective_name.lower()),
            None,
        )
        if existing_by_name and existing_by_name.get("id") and existing_by_name.get("name"):
            return str(existing_by_name["id"]), str(existing_by_name["name"])

        payload = {
            "name": effective_name,
            "description": f"Presence individuals group for installation {installation_uuid or self.installation_profile.installation_uuid}",
            "visibility": "private",
            "tags": ["presence", "bootstrap", f"installation:{installation_uuid or self.installation_profile.installation_uuid}"],
            "initial_member_ids": [],
        }
        response = await self.platform_clients.create_individual_group(token, payload)
        group = response.get("group") if isinstance(response.get("group"), dict) else response
        group_id = group.get("id") if isinstance(group, dict) else None
        group_name = group.get("name") if isinstance(group, dict) else None
        if not group_id:
            raise RuntimeError("Presence individual group creation did not return an id")
        return str(group_id), str(group_name or effective_name)

    def _should_simulate_detection(self) -> bool:
        return config.DETECTION_BACKEND_MODE == "simulate"

    def _should_auto_fallback_detection(self) -> bool:
        return config.DETECTION_BACKEND_MODE == "auto"

    def _latest_attempt(self, session_uuid: str) -> PresenceDetectionAttempt | None:
        attempts = self.attempts.get(session_uuid, [])
        return attempts[-1] if attempts else None

    def _attempt_is_simulated(self, attempt: PresenceDetectionAttempt | None) -> bool:
        if not attempt or not attempt.instant_detection_result_payload:
            return False
        return bool(attempt.instant_detection_result_payload.get("simulated"))

    def _detection_retry_count(self, attempt: PresenceDetectionAttempt | None) -> int:
        if not attempt or not attempt.instant_detection_result_payload:
            return 0
        return int(attempt.instant_detection_result_payload.get("retry_count", 0))

    def _backend_mode_for_attempt(self, attempt: PresenceDetectionAttempt | None) -> str:
        if self._attempt_is_simulated(attempt):
            return "simulated"
        return config.DETECTION_BACKEND_MODE

    def _external_detection_succeeded(self, payload: dict | None) -> bool:
        if not payload:
            return False
        if payload.get("success") is False:
            return False

        return self._payload_has_detection_evidence(payload)

    def _payload_has_detection_evidence(self, payload: dict | None) -> bool:
        if not isinstance(payload, dict):
            return False

        match = payload.get("match")
        if isinstance(match, dict) and match.get("detected") is True:
            return True

        identity_ids = self._extract_identity_ids_from_payload(payload)
        if identity_ids:
            return True

        person_objects = payload.get("person_objects")
        if isinstance(person_objects, list) and person_objects:
            return True

        people_count = payload.get("people_count")
        if isinstance(people_count, (int, float)) and people_count > 0:
            return True

        people_detected = payload.get("people_detected")
        if isinstance(people_detected, (int, float)) and people_detected > 0:
            return True

        data = payload.get("data")
        if isinstance(data, dict):
            return self._payload_has_detection_evidence(data)

        return False

    def _instant_detection_camera_status(self, payload: dict | None, camera_id: str) -> dict:
        if not payload:
            return {}

        status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
        active_cameras = status.get("active_cameras") if isinstance(status.get("active_cameras"), dict) else {}
        camera_status = active_cameras.get(camera_id)
        return camera_status if isinstance(camera_status, dict) else {}

    def _normalize_external_detection_result(self, payload: dict, session: PresenceSession) -> dict:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        match = data.get("match") if isinstance(data.get("match"), dict) else {}
        identity_ids = self._extract_identity_ids_from_payload(payload)
        return {
            "success": True,
            "camera_id": data.get("camera_id") or session.resolved_camera_uuid,
            "session_uuid": data.get("session_uuid") or session.session_uuid,
            "capture_phase": data.get("capture_phase") or "initial",
            "simulated": False,
            "raw_payload": payload,
            "identity_ids": identity_ids,
            "match": {
                "detected": True,
                "confidence": match.get("confidence", data.get("confidence", 1.0)),
                "user_uuid": match.get("user_uuid") or session.user_uuid,
                "mvr_person_uuid": match.get("mvr_person_uuid") or next((identity_id for identity_id in identity_ids if identity_id), None),
            },
        }

    def _extract_identity_ids_from_payload(self, payload: dict | None) -> list[str]:
        if not payload:
            return []

        candidates: list[str] = []

        def append_candidate(value: Any) -> None:
            if isinstance(value, str) and value and value not in candidates:
                candidates.append(value)

        data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            return candidates

        match = data.get("match")
        if isinstance(match, dict):
            append_candidate(match.get("mvr_person_uuid"))
            append_candidate(match.get("individual_uuid"))

        for person in data.get("person_objects", []) if isinstance(data.get("person_objects"), list) else []:
            if not isinstance(person, dict):
                continue
            append_candidate(person.get("mvr_person_uuid"))
            append_candidate(person.get("individual_uuid"))

            best_face = person.get("best_face")
            if isinstance(best_face, dict):
                append_candidate(best_face.get("mvr_person_uuid"))
                append_candidate(best_face.get("individual_uuid"))

            for face in person.get("faces", []) if isinstance(person.get("faces"), list) else []:
                if not isinstance(face, dict):
                    continue
                append_candidate(face.get("mvr_person_uuid"))
                append_candidate(face.get("individual_uuid"))

        return candidates

    def _extract_detection_identity_ids(self, payload: dict | None) -> list[str]:
        if not payload:
            return []
        identity_ids = payload.get("identity_ids")
        if isinstance(identity_ids, list):
            return [value for value in identity_ids if isinstance(value, str) and value]
        raw_payload = payload.get("raw_payload") if isinstance(payload.get("raw_payload"), dict) else payload
        return self._extract_identity_ids_from_payload(raw_payload)

    def _presence_individual_group_name(self, user_uuid: str | None) -> str:
        return f"Presence Individuals {user_uuid or 'unknown-user'}"

    def _presence_action_name(self, user_uuid: str | None) -> str:
        return f"Presence Action {user_uuid or 'unknown-user'}"

    def _presence_trigger_name(self, user_uuid: str | None) -> str:
        return f"Presence Trigger {user_uuid or 'unknown-user'}"

    def _mark_detection_completed(
        self,
        session: PresenceSession,
        attempt: PresenceDetectionAttempt,
        capture_phase: str,
        camera_id: str,
        simulated: bool = False,
    ) -> None:
        attempt.instant_detection_status = "completed"
        attempt.instant_detection_result_payload = {
            "success": True,
            "camera_id": camera_id,
            "session_uuid": session.session_uuid,
            "capture_phase": capture_phase,
            "simulated": simulated,
            "match": {
                "detected": True,
                "confidence": 0.98 if simulated else 1.0,
                "user_uuid": session.user_uuid,
            },
        }
        session.detection_status = "completed"
        session.resolved_camera_uuid = camera_id

    def _find_latest_session_for_device(self, device_uuid: str | None) -> PresenceSession | None:
        if not device_uuid:
            return None

        device_sessions = [session for session in self.sessions.values() if session.device_uuid == device_uuid]
        if not device_sessions:
            return None

        active_sessions: list[PresenceSession] = []
        for session in device_sessions:
            self._apply_session_limits(session)
            if session.status == PresenceSessionStatus.FAILED:
                continue
            if session.decision == PresenceDecisionState.FAILED:
                continue
            if session.expires_at <= datetime.utcnow():
                continue
            active_sessions.append(session)

        if not active_sessions:
            return None

        return max(active_sessions, key=lambda session: session.created_at)

    def _find_reserved_resource(
        self,
        resources: Dict[str, PresenceResource],
        requested_uuid: str | None,
    ) -> PresenceResource | None:
        if not requested_uuid:
            return None

        for resource in resources.values():
            if resource.resource_uuid == requested_uuid or resource.platform_resource_uuid == requested_uuid:
                return resource
        return None

    def _linked_collection_for_camera(self, camera_device_id: str | None) -> str | None:
        if not camera_device_id:
            return None
        for resource in self.collections.values():
            if resource.metadata.get("camera_device_id") == camera_device_id:
                return resource.platform_resource_uuid
        return None

    def _validate_reservation_mode(self, mode: str | None, resource_type: str) -> None:
        if mode != "bind":
            raise ValueError(
                f"Reservation mode '{mode}' is not supported for {resource_type} reservations; use 'bind'"
            )

    def _trigger_observation_for_session(self, session: PresenceSession) -> PresenceTriggerObservation | None:
        assets = session.external_assets or self._external_assets_for_user(session.user_uuid)
        if not assets or not assets.trigger_uuid:
            return None

        metadata = self.installation_profile.metadata if isinstance(self.installation_profile.metadata, dict) else None
        if not metadata:
            return PresenceTriggerObservation(trigger_uuid=assets.trigger_uuid)

        configured_action_uuid = metadata.get("presence_action_uuid")
        trigger = getattr(self.platform_clients, "trigger_lookup", {}).get(assets.trigger_uuid)
        if not isinstance(trigger, dict):
            return PresenceTriggerObservation(
                trigger_uuid=assets.trigger_uuid,
                configured_action_uuids=[configured_action_uuid] if configured_action_uuid else [],
            )

        action_uuids = trigger.get("action_uuids") or []
        if not action_uuids and trigger.get("action_uuid"):
            action_uuids = [trigger.get("action_uuid")]
        action_names = trigger.get("action_names") or []
        if not action_names and trigger.get("action_name"):
            action_names = [trigger.get("action_name")]
        return PresenceTriggerObservation(
            trigger_uuid=str(trigger.get("uuid") or assets.trigger_uuid),
            configured_action_uuids=[str(item) for item in action_uuids if item],
            configured_action_names=[str(item) for item in action_names if item],
            last_fired_at=trigger.get("last_fired_at"),
            last_matched_at=trigger.get("last_matched_at"),
            ppl_match_group_id=trigger.get("ppl_match_group_id"),
        )

    def _get_or_create_user_profile(
        self,
        current_user: dict | None = None,
        device_uuid: str | None = None,
    ) -> PresenceProfile:
        user_uuid = None
        display_name = "Presence User"
        if current_user:
            user_uuid = current_user.get("sub") or current_user.get("username") or current_user.get("email")
            display_name = current_user.get("username") or current_user.get("email") or display_name

        existing = next(
            (
                profile
                for profile in self.profiles.values()
                if profile.profile_type == "user" and (not user_uuid or profile.user_uuid == user_uuid)
            ),
            None,
        )
        if existing:
            if device_uuid and existing.device_uuid != device_uuid:
                existing.device_uuid = device_uuid
            if current_user:
                existing.metadata = {
                    **existing.metadata,
                    "email": current_user.get("email"),
                    "username": current_user.get("username"),
                }
                self.repository.save_profile(existing)
            return existing

        profile = PresenceProfile(
            profile_type="user",
            parent_presence_profile_uuid=self.installation_profile.presence_profile_uuid,
            installation_uuid=self.installation_profile.installation_uuid,
            device_uuid=device_uuid,
            user_uuid=user_uuid or "demo-user",
            display_name=display_name,
            metadata={
                "email": current_user.get("email") if current_user else None,
                "username": current_user.get("username") if current_user else None,
            },
        )
        self.profiles[profile.presence_profile_uuid] = profile
        self.repository.save_profile(profile)
        return profile
