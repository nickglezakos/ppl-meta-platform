"""
Email Settings API routes for managing SMTP configuration.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.email_settings import EmailSettings
from ..schemas.email_settings import (
    EmailSettingsCreate,
    EmailSettingsUpdate,
    EmailSettingsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings/email", tags=["email-settings"])


@router.get("", response_model=EmailSettingsResponse)
async def get_email_settings(db: Session = Depends(get_db)):
    """
    Get current email settings.
    
    Returns the first (and only) email settings record.
    Creates default settings if none exist.
    """
    settings = db.query(EmailSettings).first()
    
    if not settings:
        # Create default settings
        settings = EmailSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
        logger.info("Created default email settings")
    
    # Mask password in response
    response_dict = {
        "id": settings.id,
        "mail_enabled": settings.mail_enabled,
        "mail_server": settings.mail_server,
        "mail_port": settings.mail_port,
        "mail_username": settings.mail_username,
        "mail_password": "********" if settings.mail_password else "",
        "mail_from": settings.mail_from,
        "mail_from_name": settings.mail_from_name,
        "mail_starttls": settings.mail_starttls,
        "mail_ssl_tls": settings.mail_ssl_tls,
        "use_credentials": settings.use_credentials,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at,
    }
    
    return EmailSettingsResponse(**response_dict)


@router.put("", response_model=EmailSettingsResponse)
async def update_email_settings(
    settings_update: EmailSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Update email settings.
    
    Updates the email SMTP configuration. Only provided fields will be updated.
    """
    settings = db.query(EmailSettings).first()
    
    if not settings:
        # Create new settings if none exist
        settings = EmailSettings()
        db.add(settings)
    
    # Update only provided fields
    update_data = settings_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if value is not None:  # Only update if value is explicitly provided
            setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    logger.info(f"Updated email settings: mail_enabled={settings.mail_enabled}, server={settings.mail_server}")
    
    # Mask password in response
    response_dict = {
        "id": settings.id,
        "mail_enabled": settings.mail_enabled,
        "mail_server": settings.mail_server,
        "mail_port": settings.mail_port,
        "mail_username": settings.mail_username,
        "mail_password": "********" if settings.mail_password else "",
        "mail_from": settings.mail_from,
        "mail_from_name": settings.mail_from_name,
        "mail_starttls": settings.mail_starttls,
        "mail_ssl_tls": settings.mail_ssl_tls,
        "use_credentials": settings.use_credentials,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at,
    }
    
    return EmailSettingsResponse(**response_dict)


@router.post("/test", response_model=dict)
async def test_email_settings(
    test_email: str,
    db: Session = Depends(get_db)
):
    """
    Test email settings by sending a test email.
    
    Args:
        test_email: Email address to send test email to
        
    Returns:
        Success status and message
    """
    settings = db.query(EmailSettings).first()
    
    if not settings or not settings.mail_enabled:
        raise HTTPException(
            status_code=400,
            detail="Email is not enabled. Please enable and configure email settings first."
        )
    
    # Check if all required fields are configured
    if not settings.mail_server or not settings.mail_username or not settings.mail_from:
        raise HTTPException(
            status_code=400,
            detail="Email settings are incomplete. Please configure SMTP server, username, and from address."
        )
    
    # Import email service
    from ..services.email_service import EmailService
    
    try:
        email_service = EmailService(db)
        
        # Send test email
        success, message, log_uuid = await email_service.send_email(
            to=[test_email],
            subject="PPL Meta Email Test",
            text_body="This is a test email from PPL Meta Communications Service. If you received this, your email settings are configured correctly!",
        )
        
        if success:
            return {
                "success": True,
                "message": f"Test email sent successfully to {test_email}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send test email: {message}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing email settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test email: {str(e)}"
        )
