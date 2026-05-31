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


class PresencePolicyRule(BaseModel):
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None


class PresenceGroupPolicy(BaseModel):
    granted: Optional[PresencePolicyRule] = None
    denied: Optional[PresencePolicyRule] = None
    retry_required: Optional[PresencePolicyRule] = None
    failed: Optional[PresencePolicyRule] = None


class UpdateInstallationPolicyRequest(BaseModel):
    installation_uuid: str = "local-installation"
    group_policy: PresenceGroupPolicy


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


class CreatePresenceGroupRequest(BaseModel):
    installation_uuid: str = "local-installation"
    user_uuid: Optional[str] = None
    display_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    group_policy: Optional[PresenceGroupPolicy] = None


class PresenceGroup(BaseModel):
    group_uuid: str
    installation_uuid: str = "local-installation"
    user_uuid: Optional[str] = None
    display_name: str
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    group_policy: Optional[PresenceGroupPolicy] = None
    created_at: datetime
    updated_at: datetime


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
    device_uuid: str
    device_name: str
    device_platform: str
    app_version: str


class PresenceSession(BaseModel):
    session_uuid: str = Field(default_factory=lambda: str(uuid4()))
    installation_uuid: str = "local-installation"
    device_uuid: str
    user_uuid: str = "unknown-user"
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
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    action_log_uuid: Optional[str] = None
    executed_at: Optional[datetime] = None


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


class PresenceQrValidateRequest(BaseModel):
    qr_token: str


class PresenceQrHitRequest(BaseModel):
    qr_token: str
    installation_uuid: str
    scanned_at: datetime


class BindResourcesRequest(BaseModel):
    camera_uuid: str
    collection_uuid: str


class ReserveResourceRequest(BaseModel):
    installation_uuid: str
    resource_uuid: str
    mode: str = "bind"


class ResetInstallationReservationsRequest(BaseModel):
    installation_uuid: str = "local-installation"


class PresenceResult(BaseModel):
    session_uuid: str
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


class PresenceActionPlan(BaseModel):
    session_uuid: str
    matched_group_uuid: Optional[str] = None
    decision: PresenceDecisionState
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None


class PresenceDecisionRecord(BaseModel):
    decision_uuid: str = Field(default_factory=lambda: str(uuid4()))
    session_uuid: str
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
    installation_uuid: str
    user_uuid: str
    device_uuid: str
    outcome: str
    reason_code: str
    matched_group_uuid: Optional[str] = None
    policy_source: Optional[str] = None
    trigger_type: Optional[str] = None
    action_type: Optional[str] = None
    action_execution_status: Optional[str] = None
    resolved_camera_uuid: Optional[str] = None
    resolved_collection_uuid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
