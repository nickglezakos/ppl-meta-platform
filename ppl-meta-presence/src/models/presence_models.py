from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PresenceSessionStatus(str, Enum):
    CREATED = "created"
    AWAITING_FRONT_BURST = "awaiting_front_burst"
    BURST_RECEIVED = "burst_received"
    QR_RESOLVED = "qr_resolved"
    COMPLETED = "completed"
    FAILED = "failed"


class PresenceDecisionState(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    RETRY_REQUIRED = "retry_required"
    FAILED = "failed"


class PresenceSessionMode(str, Enum):
    QR_ONLY = "qr_only"
    CAMERA_ONLY = "camera_only"
    QR_PLUS_CAMERA = "qr_plus_camera"


class PresenceAssuranceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PresenceGrantType(str, Enum):
    CHECK_IN = "check_in"
    PRESENCE_MATCH = "presence_match"
    VERIFIED_PRESENCE = "verified_presence"


class PresencePolicyRule(BaseModel):
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None


class PresenceGroupPolicy(BaseModel):
    granted: Optional[PresencePolicyRule] = None
    denied: Optional[PresencePolicyRule] = None
    retry_required: Optional[PresencePolicyRule] = None
    failed: Optional[PresencePolicyRule] = None
    qr_only: Optional[Dict[str, PresencePolicyRule]] = None
    camera_only: Optional[Dict[str, PresencePolicyRule]] = None
    qr_plus_camera: Optional[Dict[str, PresencePolicyRule]] = None


class PresenceSessionSettings(BaseModel):
    session_timeout_seconds: int = 300
    max_unsuccessful_attempts: int = 3
    allow_concurrent_trigger_operations: bool = True
    qr_to_camera_transition_window_minutes: int = 10


class UpdateInstallationSettingsRequest(BaseModel):
    installation_uuid: str = "local-installation"
    session_settings: PresenceSessionSettings


class UpdateInstallationPolicyRequest(BaseModel):
    installation_uuid: str = "local-installation"
    group_policy: PresenceGroupPolicy


class UpdateActivePresenceGroupRequest(BaseModel):
    installation_uuid: str = "local-installation"
    individual_group_id: Optional[str] = None
    group_name: Optional[str] = None
    clear_active_group: bool = False


class PresenceIndividualGroupOption(BaseModel):
    individual_group_id: str
    name: str
    description: Optional[str] = None
    member_count: int = 0


class PresenceProfile(BaseModel):
    presence_profile_uuid: str = Field(default_factory=lambda: str(uuid4()))
    profile_type: str
    parent_presence_profile_uuid: Optional[str] = None
    installation_uuid: Optional[str] = None
    device_uuid: Optional[str] = None
    user_uuid: Optional[str] = None
    display_name: str
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PresenceResource(BaseModel):
    resource_uuid: str = Field(default_factory=lambda: str(uuid4()))
    resource_type: str
    installation_uuid: str
    platform_resource_uuid: str
    status: str = "reserved"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreatePresenceSessionRequest(BaseModel):
    session_mode: PresenceSessionMode = PresenceSessionMode.QR_PLUS_CAMERA
    device_uuid: str
    device_name: str
    device_platform: str
    app_version: str


class PresenceSession(BaseModel):
    session_uuid: str = Field(default_factory=lambda: str(uuid4()))
    installation_uuid: str = "local-installation"
    device_uuid: str
    user_uuid: str = "unknown-user"
    session_mode: PresenceSessionMode = PresenceSessionMode.QR_PLUS_CAMERA
    assurance_level: PresenceAssuranceLevel = PresenceAssuranceLevel.HIGH
    grant_type: PresenceGrantType = PresenceGrantType.VERIFIED_PRESENCE
    status: PresenceSessionStatus = PresenceSessionStatus.CREATED
    qr_token: str = Field(default_factory=lambda: str(uuid4()))
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    retry_allowed: bool = True
    detection_status: str = "not_started"
    instant_detection_request_id: Optional[str] = None
    qr_status: str = "not_scanned"
    resolved_camera_uuid: Optional[str] = None
    resolved_collection_uuid: Optional[str] = None
    decision: PresenceDecisionState = PresenceDecisionState.PENDING
    matched_group_uuid: Optional[str] = None
    matched_individual_group_id: Optional[str] = None
    matched_individual_group_name: Optional[str] = None
    matched_member_number: Optional[int] = None
    matched_member_name: Optional[str] = None
    matched_gender: Optional[str] = None
    matched_age_min: Optional[int] = None
    matched_age_max: Optional[int] = None
    matched_ppp_uuid: Optional[str] = None
    matched_member_uuid: Optional[str] = None
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    action_log_uuid: Optional[str] = None
    executed_at: Optional[datetime] = None
    external_assets: Optional[PresenceExternalAssets] = None
    failure_reason_code: Optional[str] = None


class PresenceFramePayload(BaseModel):
    frame_data: str
    timestamp: float
    width: int
    height: int
    format: str
    orientation: str
    rotation_angle: int
    fps: int
    camera_facing: Optional[str] = None


class PresenceBurstUploadRequest(BaseModel):
    device_id: str
    session_uuid: str
    capture_phase: str
    frames: List[PresenceFramePayload]
    captured_at: datetime
    transport_source: str


class PresenceDetectionAttempt(BaseModel):
    attempt_uuid: str = Field(default_factory=lambda: str(uuid4()))
    session_uuid: str
    attempt_index: int
    capture_phase: str
    instant_detection_request_id: str = Field(default_factory=lambda: str(uuid4()))
    instant_detection_status: str = "submitted"
    instant_detection_result_payload: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PresenceQrRenderRequest(BaseModel):
    installation_uuid: str = "local-installation"
    device_reference: Optional[str] = None
    device_display_name: Optional[str] = None
    location: Optional[Dict[str, Any]] = None


class PresenceOwnerQrRenderRequest(BaseModel):
    installation_uuid: str = "local-installation"
    owner_user_uuid: Optional[str] = None
    owner_display_name: Optional[str] = None


class PresenceQrValidateRequest(BaseModel):
    qr_token: str


class PresenceQrHitRequest(BaseModel):
    qr_token: str
    installation_uuid: str
    scanned_at: datetime
    qr_payload: Optional[Dict[str, Any]] = None


class PresenceOwnerQrHitRequest(BaseModel):
    qr_payload: Dict[str, Any]
    installation_uuid: str
    scanned_at: datetime


class BindResourcesRequest(BaseModel):
    camera_uuid: str
    collection_uuid: str


class ReserveResourceRequest(BaseModel):
    installation_uuid: str
    resource_uuid: str
    mode: str = "bind"


class UnreserveResourceRequest(BaseModel):
    installation_uuid: str
    resource_uuid: str


class ResetInstallationReservationsRequest(BaseModel):
    installation_uuid: str = "local-installation"


class TriggerMatchRequest(BaseModel):
    """Service-to-service payload issued by the media service when a
    people-match trigger (ppl_match or vprofile_match) fires successfully and
    a presence action is attached."""

    camera_device_id: str
    trigger_uuid: str
    action_uuid: Optional[str] = None
    match_info: Dict[str, Any] = Field(default_factory=dict)
    matched_member_uuid: Optional[str] = None
    similarity_score: Optional[float] = None
    source_mvr_uuid: Optional[str] = None
    matched_at: Optional[str] = None
    matched_individual_group_id: Optional[str] = None
    matched_individual_group_name: Optional[str] = None
    matched_member_number: Optional[int] = None
    matched_member_name: Optional[str] = None
    matched_gender: Optional[str] = None
    matched_age_min: Optional[int] = None
    matched_age_max: Optional[int] = None


class PresencePeopleProfile(BaseModel):
    """A people-centric identity record (PPP) used as the canonical place to
    set and retrieve a real person's name and details across individual groups
    and presence sessions."""

    ppp_uuid: str = Field(default_factory=lambda: str(uuid4()))
    profile_type: str = "people"
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    external_ref: Optional[str] = None
    parent_ppp_uuid: Optional[str] = None
    installation_uuid: str = "local-installation"
    linked_member_count: int = 0
    status: str = "active"  # active | inactive | merged
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PresencePeopleProfileLink(BaseModel):
    """Links a PPP to one member in one individual group."""

    link_uuid: str = Field(default_factory=lambda: str(uuid4()))
    ppp_uuid: str
    group_id: str
    individual_id: str
    linked_at: datetime = Field(default_factory=datetime.utcnow)
    linked_by: Optional[str] = None


class CreatePeopleProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    external_ref: Optional[str] = None
    installation_uuid: str = "local-installation"


class UpdatePeopleProfileRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    external_ref: Optional[str] = None
    status: Optional[str] = None


class LinkMemberRequest(BaseModel):
    group_id: str
    individual_id: str


class UnlinkMemberRequest(BaseModel):
    group_id: str
    individual_id: str


class PresenceExternalAssets(BaseModel):
    individual_group_id: Optional[str] = None
    trigger_uuid: Optional[str] = None
    action_uuid: Optional[str] = None


class PresenceTriggerObservation(BaseModel):
    trigger_uuid: Optional[str] = None
    configured_action_uuids: List[str] = Field(default_factory=list)
    configured_action_names: List[str] = Field(default_factory=list)
    last_fired_at: Optional[str] = None
    last_matched_at: Optional[str] = None
    ppl_match_group_id: Optional[str] = None


class PresenceResult(BaseModel):
    session_uuid: str
    session_mode: PresenceSessionMode
    assurance_level: PresenceAssuranceLevel
    grant_type: PresenceGrantType
    status: PresenceSessionStatus
    decision: PresenceDecisionState
    reason_code: str
    matched_group_uuid: Optional[str] = None
    policy_source: Optional[str] = None
    detection_backend_mode: Optional[str] = None
    simulated_detection: bool = False
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    action_log_uuid: Optional[str] = None
    executed_at: Optional[datetime] = None
    resolved_camera_uuid: Optional[str] = None
    resolved_collection_uuid: Optional[str] = None
    external_assets: Optional[PresenceExternalAssets] = None
    trigger_observation: Optional[PresenceTriggerObservation] = None


class PresenceActionPlan(BaseModel):
    session_uuid: str
    session_mode: PresenceSessionMode
    assurance_level: PresenceAssuranceLevel
    grant_type: PresenceGrantType
    matched_group_uuid: Optional[str] = None
    decision: PresenceDecisionState
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    external_assets: Optional[PresenceExternalAssets] = None
    trigger_observation: Optional[PresenceTriggerObservation] = None


class PresenceDecisionRecord(BaseModel):
    decision_uuid: str = Field(default_factory=lambda: str(uuid4()))
    session_uuid: str
    session_mode: PresenceSessionMode = PresenceSessionMode.QR_PLUS_CAMERA
    assurance_level: PresenceAssuranceLevel = PresenceAssuranceLevel.HIGH
    grant_type: PresenceGrantType = PresenceGrantType.VERIFIED_PRESENCE
    installation_uuid: str
    user_uuid: str
    device_uuid: str
    decision: PresenceDecisionState
    reason_code: str
    matched_group_uuid: Optional[str] = None
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    action_log_uuid: Optional[str] = None
    simulated_detection: bool = False
    resolved_camera_uuid: Optional[str] = None
    resolved_collection_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PresenceAuditLogTrace(BaseModel):
    log_uuid: Optional[str] = None
    found: bool = False
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PresenceSessionTrace(BaseModel):
    session: PresenceSession
    action_plan: PresenceActionPlan
    decision_history: List[PresenceDecisionRecord] = Field(default_factory=list)
    audit_log: Optional[PresenceAuditLogTrace] = None


class PresenceAnalyticsEvent(BaseModel):
    event_uuid: str = Field(default_factory=lambda: str(uuid4()))
    session_uuid: str
    session_mode: PresenceSessionMode = PresenceSessionMode.QR_PLUS_CAMERA
    assurance_level: PresenceAssuranceLevel = PresenceAssuranceLevel.HIGH
    grant_type: PresenceGrantType = PresenceGrantType.VERIFIED_PRESENCE
    installation_uuid: str
    user_uuid: str
    device_uuid: str
    outcome: str
    reason_code: str
    matched_group_uuid: Optional[str] = None
    matched_individual_group_id: Optional[str] = None
    matched_individual_group_name: Optional[str] = None
    matched_member_number: Optional[int] = None
    matched_member_name: Optional[str] = None
    matched_gender: Optional[str] = None
    matched_age_min: Optional[int] = None
    matched_age_max: Optional[int] = None
    matched_ppp_uuid: Optional[str] = None
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    resolved_camera_uuid: Optional[str] = None
    resolved_collection_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
