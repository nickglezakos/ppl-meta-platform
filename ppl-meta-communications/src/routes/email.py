"""
Email API routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.email import (
    EmailSendRequest,
    EmailSendResponse,
    EmailTemplateCreate,
    EmailTemplateRequest,
    EmailTemplateResponse,
)
from ..services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/send", response_model=EmailSendResponse)
async def send_email(
    request: EmailSendRequest,
    db: Session = Depends(get_db)
):
    """
    Send an email.
    
    Sends an email to one or more recipients with the specified content.
    """
    email_service = EmailService(db)
    
    success, message, log_uuid = await email_service.send_email(
        to=request.to,
        subject=request.subject,
        text_body=request.text_body,
        html_body=request.html_body,
        cc=request.cc,
        bcc=request.bcc,
        from_email=request.from_email,
        from_name=request.from_name,
        payload=request.payload,
        triggered_by=request.triggered_by,
        trigger_type=request.trigger_type,
        trigger_id=request.trigger_id,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return EmailSendResponse(
        success=success,
        message=message,
        log_uuid=log_uuid,
        recipients_count=len(request.to) + len(request.cc or []) + len(request.bcc or [])
    )


@router.post("/send/template", response_model=EmailSendResponse)
async def send_email_with_template(
    request: EmailTemplateRequest,
    db: Session = Depends(get_db)
):
    """
    Send an email using a template.
    
    Sends an email using a predefined template with variable substitution.
    """
    email_service = EmailService(db)
    
    success, message, log_uuid = await email_service.send_email_with_template(
        to=request.to,
        template_name=request.template_name,
        variables=request.variables,
        cc=request.cc,
        bcc=request.bcc,
        triggered_by=request.triggered_by,
        trigger_type=request.trigger_type,
        trigger_id=request.trigger_id,
    )
    
    if not success:
        raise HTTPException(status_code=404 if "not found" in message.lower() else 500, detail=message)
    
    return EmailSendResponse(
        success=success,
        message=message,
        log_uuid=log_uuid,
        recipients_count=len(request.to) + len(request.cc or []) + len(request.bcc or [])
    )


@router.post("/templates", response_model=EmailTemplateResponse)
async def create_email_template(
    template: EmailTemplateCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new email template.
    """
    email_service = EmailService(db)
    
    try:
        created_template = email_service.create_template(template.dict())
        return EmailTemplateResponse.from_orm(created_template)
    except Exception as e:
        logger.error(f"Failed to create email template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_name}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_name: str,
    db: Session = Depends(get_db)
):
    """
    Get an email template by name.
    """
    email_service = EmailService(db)
    
    template = email_service.get_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
    
    return EmailTemplateResponse.from_orm(template)


@router.get("/templates", response_model=list[EmailTemplateResponse])
async def list_email_templates(
    category: str = None,
    db: Session = Depends(get_db)
):
    """
    List all email templates, optionally filtered by category.
    """
    email_service = EmailService(db)
    
    templates = email_service.list_templates(category=category)
    return [EmailTemplateResponse.from_orm(t) for t in templates]
