"""
Pydantic schemas for notifications and audit logging.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PushNotificationRequest(BaseModel):
    """Request schema for sending push notifications."""
    
    device_tokens: List[str] = Field(..., description="List of device FCM/APNS tokens")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    body: str = Field(..., min_length=1, max_length=500, description="Notification body")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data payload")
    badge: Optional[int] = Field(None, description="Badge count (iOS)")
    sound: Optional[str] = Field(None, description="Notification sound")
    priority: str = Field("high", description="Notification priority (high, normal)")
    
    # Trigger tracking
    triggered_by: Optional[str] = Field(None, description="Service/user that triggered this notification")
    trigger_type: Optional[str] = Field(None, description="Type of trigger")
    trigger_id: Optional[str] = Field(None, description="ID of trigger")
    
    # Phase 3: VPN-aware fields
    device_tailscale_ip: Optional[str] = Field(None, description="Target device's Tailscale VPN IP")
    prefer_vpn: bool = Field(default=False, description="Whether to prefer VPN routing for this notification")


class PushNotificationResponse(BaseModel):
    """Response schema for push notification operations."""
    
    success: bool
    message: str
    log_uuid: UUID
    devices_count: int
    successful_count: int
    failed_count: int
    
    class Config:
        from_attributes = True


class AuditLogRequest(BaseModel):
    """Request schema for creating audit log entries."""
    
    event_type: str = Field(..., description="Type of event (e.g., 'trigger_fired', 'user_login')")
    event_source: str = Field(..., description="Source service/component")
    event_data: Dict[str, Any] = Field(..., description="Event data payload")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    ip_address: Optional[str] = Field(None, description="IP address if applicable")
    source_network: Optional[str] = Field(None, description="Network type: tailscale_vpn or local (Phase 3)")
    severity: str = Field("info", description="Log severity: info, warning, error, critical")


class AuditLogResponse(BaseModel):
    """Response schema for audit log operations."""
    
    success: bool
    message: str
    log_uuid: UUID
    
    class Config:
        from_attributes = True


class CommunicationLogQuery(BaseModel):
    """Query schema for retrieving communication logs."""
    
    type: Optional[str] = Field(None, description="Filter by communication type")
    status: Optional[str] = Field(None, description="Filter by status")
    recipient: Optional[str] = Field(None, description="Filter by recipient")
    triggered_by: Optional[str] = Field(None, description="Filter by trigger source")
    trigger_id: Optional[str] = Field(None, description="Filter by trigger ID")
    installation_id: Optional[str] = Field(None, description="Filter by installation/tenant ID")
    tenant_name: Optional[str] = Field(None, description="Filter by tenant name (partial match)")
    start_date: Optional[str] = Field(None, description="Filter by start date (ISO format)")
    end_date: Optional[str] = Field(None, description="Filter by end date (ISO format)")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=500, description="Results per page")


class CommunicationLogResponse(BaseModel):
    """Response schema for communication log."""
    
    id: int
    uuid: UUID
    type: str
    status: str
    recipient: str
    subject: Optional[str]
    content: Optional[str]
    payload: Optional[Dict[str, Any]]
    triggered_by: Optional[str]
    trigger_type: Optional[str]
    trigger_id: Optional[str]
    installation_id: Optional[str]
    tenant_name: Optional[str]
    attempts: int
    last_attempt_at: Optional[str]
    delivered_at: Optional[str]
    failed_at: Optional[str]
    error_message: Optional[str]
    response_status_code: Optional[int]
    response_body: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CommunicationLogListResponse(BaseModel):
    """Paginated list of communication logs."""
    
    logs: List[CommunicationLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
