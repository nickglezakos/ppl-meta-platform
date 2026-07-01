"""
Audit logging and communication log query API routes.

Phase 3: VPN-aware — classifies request source networks as
tailscale_vpn or local based on CGNAT IP range (100.64.0.0/10).
"""

import ipaddress
import logging
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.notification import (
    AuditLogRequest,
    AuditLogResponse,
    CommunicationLogListResponse,
    CommunicationLogResponse,
)
from ..services.notification_service import (
    AuditLogService,
    CommunicationLogService,
)

logger = logging.getLogger(__name__)

# Tailscale CGNAT range (100.64.0.0/10)
TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def classify_request_network(request: Request) -> str:
    """Classify the source network of a request.

    Phase 3: Detects if the request came from a Tailscale VPN IP
    (100.64.0.0/10) or a local network.

    Args:
        request: The FastAPI request object.

    Returns:
        "tailscale_vpn" if from CGNAT range, "local" otherwise.
    """
    client_ip = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(client_ip) in TAILSCALE_CGNAT:
            return "tailscale_vpn"
    except ValueError:
        pass
    return "local"

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/log", response_model=AuditLogResponse)
async def create_audit_log(
    request: AuditLogRequest,
    db: Session = Depends(get_db)
):
    """
    Create an audit log entry.
    
    Logs an event for audit trail purposes.
    """
    audit_service = AuditLogService(db)
    
    success, message, log_uuid = await audit_service.log_audit_event(
        event_type=request.event_type,
        event_source=request.event_source,
        event_data=request.event_data,
        user_id=request.user_id,
    ip_address=request.ip_address,
    severity=request.severity,
    source_network=request.source_network,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return AuditLogResponse(
        success=success,
        message=message,
        log_uuid=log_uuid
    )


@router.get("/logs", response_model=CommunicationLogListResponse)
async def get_communication_logs(
    log_type: Optional[str] = Query(None, alias="type", description="Filter by communication type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    recipient: Optional[str] = Query(None, description="Filter by recipient"),
    triggered_by: Optional[str] = Query(None, description="Filter by trigger source"),
    trigger_id: Optional[str] = Query(None, description="Filter by trigger ID"),
    installation_id: Optional[str] = Query(None, description="Filter by installation ID"),
    tenant_name: Optional[str] = Query(None, description="Filter by tenant name"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Query communication logs with filters.
    
    Returns paginated list of communication logs matching the specified filters.
    """
    log_service = CommunicationLogService(db)
    
    # Parse dates if provided
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    logs, total = log_service.get_logs(
        type=log_type,
        status=status,
        recipient=recipient,
        triggered_by=triggered_by,
        trigger_id=trigger_id,
        installation_id=installation_id,
        tenant_name=tenant_name,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        page_size=page_size,
    )
    
    # Convert to response models
    log_responses = [
        CommunicationLogResponse(
            id=log.id,
            uuid=log.uuid,
            type=log.type.value,
            status=log.status.value,
            recipient=log.recipient,
            subject=log.subject,
            content=log.content,
            payload=log.payload,
            triggered_by=log.triggered_by,
            trigger_type=log.trigger_type,
            trigger_id=log.trigger_id,
            installation_id=log.installation_id,
            tenant_name=log.tenant_name,
            attempts=log.attempts,
            last_attempt_at=log.last_attempt_at.isoformat() if log.last_attempt_at else None,
            delivered_at=log.delivered_at.isoformat() if log.delivered_at else None,
            failed_at=log.failed_at.isoformat() if log.failed_at else None,
            error_message=log.error_message,
            response_status_code=log.response_status_code,
            response_body=log.response_body,
            created_at=log.created_at.isoformat(),
            updated_at=log.updated_at.isoformat(),
        )
        for log in logs
    ]
    
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return CommunicationLogListResponse(
        logs=log_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/logs/{log_uuid}", response_model=CommunicationLogResponse)
async def get_communication_log(
    log_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Get a single communication log by UUID.
    """
    from uuid import UUID
    
    log_service = CommunicationLogService(db)
    
    try:
        log_uuid_obj = UUID(log_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from exc
    
    log = log_service.get_log_by_uuid(log_uuid_obj)
    if not log:
        raise HTTPException(status_code=404, detail=f"Log with UUID '{log_uuid}' not found")
    
    return CommunicationLogResponse(
        id=log.id,
        uuid=log.uuid,
        type=log.type.value,
        status=log.status.value,
        recipient=log.recipient,
        subject=log.subject,
        content=log.content,
        payload=log.payload,
        triggered_by=log.triggered_by,
        trigger_type=log.trigger_type,
        trigger_id=log.trigger_id,
        installation_id=log.installation_id,
        tenant_name=log.tenant_name,
        attempts=log.attempts,
        last_attempt_at=log.last_attempt_at.isoformat() if log.last_attempt_at else None,
        delivered_at=log.delivered_at.isoformat() if log.delivered_at else None,
        failed_at=log.failed_at.isoformat() if log.failed_at else None,
        error_message=log.error_message,
        response_status_code=log.response_status_code,
        response_body=log.response_body,
        created_at=log.created_at.isoformat(),
        updated_at=log.updated_at.isoformat(),
    )
