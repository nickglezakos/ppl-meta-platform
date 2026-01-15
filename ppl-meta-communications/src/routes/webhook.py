"""
Webhook API routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.webhook import (
    WebhookConfigCreate,
    WebhookConfigResponse,
    WebhookSendRequest,
    WebhookSendResponse,
)
from ..services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/send", response_model=WebhookSendResponse)
async def send_webhook(
    request: WebhookSendRequest,
    db: Session = Depends(get_db)
):
    """
    Send a webhook request.
    
    Sends an HTTP request to the specified URL with the provided payload.
    """
    webhook_service = WebhookService(db)
    
    success, message, log_uuid, status_code, response_body = await webhook_service.send_webhook(
        url=str(request.url),
        payload=request.payload,
        method=request.method,
        headers=request.headers,
        timeout=request.timeout,
        triggered_by=request.triggered_by,
        trigger_type=request.trigger_type,
        trigger_id=request.trigger_id,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return WebhookSendResponse(
        success=success,
        message=message,
        log_uuid=log_uuid,
        status_code=status_code,
        response_body=response_body
    )


@router.post("/send/config/{config_name}", response_model=WebhookSendResponse)
async def send_webhook_from_config(
    config_name: str,
    payload: dict,
    triggered_by: str = None,
    trigger_type: str = None,
    trigger_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Send a webhook using a saved configuration.
    
    Sends a webhook request using a predefined configuration by name.
    """
    webhook_service = WebhookService(db)
    
    success, message, log_uuid, status_code, response_body = await webhook_service.send_webhook_from_config(
        config_name=config_name,
        payload=payload,
        triggered_by=triggered_by,
        trigger_type=trigger_type,
        trigger_id=trigger_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=404 if "not found" in message.lower() else 500,
            detail=message
        )
    
    return WebhookSendResponse(
        success=success,
        message=message,
        log_uuid=log_uuid,
        status_code=status_code,
        response_body=response_body
    )


@router.post("/configs", response_model=WebhookConfigResponse)
async def create_webhook_config(
    config: WebhookConfigCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new webhook configuration.
    """
    webhook_service = WebhookService(db)
    
    try:
        created_config = webhook_service.create_webhook_config(config.dict())
        return WebhookConfigResponse.from_orm(created_config)
    except Exception as e:
        logger.error(f"Failed to create webhook config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{config_name}", response_model=WebhookConfigResponse)
async def get_webhook_config(
    config_name: str,
    db: Session = Depends(get_db)
):
    """
    Get a webhook configuration by name.
    """
    webhook_service = WebhookService(db)
    
    config = webhook_service.get_webhook_config(config_name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Webhook config '{config_name}' not found")
    
    return WebhookConfigResponse.from_orm(config)


@router.get("/configs", response_model=list[WebhookConfigResponse])
async def list_webhook_configs(
    is_active: bool = None,
    db: Session = Depends(get_db)
):
    """
    List all webhook configurations.
    """
    webhook_service = WebhookService(db)
    
    configs = webhook_service.list_webhook_configs(is_active=is_active)
    return [WebhookConfigResponse.from_orm(c) for c in configs]
