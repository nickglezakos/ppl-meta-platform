"""
Email service for sending emails via SMTP.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..config import get_config
from ..models.communication_log import (
    CommunicationLog,
    CommunicationStatus,
    CommunicationType,
)
from ..models.email_template import EmailTemplate

logger = logging.getLogger(__name__)
config = get_config()


class EmailService:
    """Service for sending emails."""

    def __init__(self, db: Session):
        self.db = db
        self.config = config

    async def send_email(
        self,
        to: List[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        payload: Optional[Dict] = None,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> tuple[bool, str, UUID]:
        """
        Send an email.
        
        Returns:
            tuple: (success, message, log_uuid)
        """
        # Try to get settings from database first
        from ..models.email_settings import EmailSettings
        db_settings = self.db.query(EmailSettings).first()
        
        # Use database settings if available and enabled, otherwise fallback to config
        if db_settings and db_settings.mail_enabled:
            mail_config = {
                'server': db_settings.mail_server,
                'port': db_settings.mail_port,
                'username': db_settings.mail_username,
                'password': db_settings.mail_password,
                'from': db_settings.mail_from,
                'from_name': db_settings.mail_from_name,
                'starttls': db_settings.mail_starttls,
                'ssl_tls': db_settings.mail_ssl_tls,
                'use_credentials': db_settings.use_credentials,
            }
            logger.info("Using database email settings")
        elif self.config.is_mail_configured():
            mail_config = {
                'server': self.config.MAIL_SERVER,
                'port': self.config.MAIL_PORT,
                'username': self.config.MAIL_USERNAME,
                'password': self.config.MAIL_PASSWORD,
                'from': self.config.MAIL_FROM,
                'from_name': self.config.MAIL_FROM_NAME,
                'starttls': self.config.MAIL_STARTTLS,
                'ssl_tls': self.config.MAIL_SSL_TLS,
                'use_credentials': self.config.USE_CREDENTIALS,
            }
            logger.info("Using environment email settings")
        else:
            logger.error("Email is not configured. Check database settings or MAIL_* environment variables.")
            return False, "Email service not configured", None

        # Use configured defaults if not provided
        sender_email = from_email or mail_config['from']
        sender_name = from_name or mail_config['from_name']

        # Create communication log
        # Merge provided payload with email metadata
        email_payload = payload.copy() if payload else {}
        email_payload.update({"cc": cc, "bcc": bcc, "html_body": html_body})
        
        log = CommunicationLog(
            type=CommunicationType.EMAIL,
            status=CommunicationStatus.PENDING,
            recipient=", ".join(to),
            subject=subject,
            content=text_body,
            payload=email_payload,
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            attempts=0,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = ", ".join(to)
            if cc:
                msg["Cc"] = ", ".join(cc)
            if bcc:
                msg["Bcc"] = ", ".join(bcc)

            # Attach plain text and HTML parts
            part1 = MIMEText(text_body, "plain")
            msg.attach(part1)
            
            if html_body:
                part2 = MIMEText(html_body, "html")
                msg.attach(part2)

            # Combine all recipients
            all_recipients = to + (cc or []) + (bcc or [])

            # Send email
            log.attempts += 1
            self.db.commit()

            if mail_config['ssl_tls']:
                # Use SSL/TLS (port 465)
                with smtplib.SMTP_SSL(mail_config['server'], mail_config['port']) as server:
                    if mail_config['use_credentials']:
                        server.login(mail_config['username'], mail_config['password'])
                    server.sendmail(sender_email, all_recipients, msg.as_string())
            else:
                # Use STARTTLS (port 587) or plain SMTP
                with smtplib.SMTP(mail_config['server'], mail_config['port']) as server:
                    if mail_config['starttls']:
                        server.starttls()
                    if mail_config['use_credentials']:
                        server.login(mail_config['username'], mail_config['password'])
                    server.sendmail(sender_email, all_recipients, msg.as_string())

            # Update log on success
            from datetime import datetime, timezone
            log.status = CommunicationStatus.SENT
            log.delivered_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.info(f"✅ Email sent successfully to {len(all_recipients)} recipients. Log UUID: {log.uuid}")
            return True, f"Email sent to {len(all_recipients)} recipients", log.uuid

        except Exception as e:
            # Update log on failure
            from datetime import datetime, timezone
            log.status = CommunicationStatus.FAILED
            log.failed_at = datetime.now(timezone.utc)
            log.error_message = str(e)
            self.db.commit()

            logger.error(f"❌ Failed to send email: {e}")
            return False, f"Failed to send email: {str(e)}", log.uuid

    async def send_email_with_template(
        self,
        to: List[str],
        template_name: str,
        variables: dict,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> tuple[bool, str, Optional[UUID]]:
        """
        Send an email using a template.
        
        Returns:
            tuple: (success, message, log_uuid)
        """
        # Get template
        template = self.db.query(EmailTemplate).filter(
            EmailTemplate.name == template_name,
            EmailTemplate.is_active == True
        ).first()

        if not template:
            logger.error(f"Email template not found: {template_name}")
            return False, f"Email template '{template_name}' not found", None

        # Substitute variables
        subject = template.subject
        text_body = template.text_body
        html_body = template.html_body

        for var_name, var_value in variables.items():
            placeholder = "{{" + var_name + "}}"
            subject = subject.replace(placeholder, str(var_value))
            text_body = text_body.replace(placeholder, str(var_value))
            if html_body:
                html_body = html_body.replace(placeholder, str(var_value))

        # Send email
        return await self.send_email(
            to=to,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            cc=cc,
            bcc=bcc,
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
        )

    def create_template(self, template_data: dict) -> EmailTemplate:
        """Create a new email template."""
        template = EmailTemplate(**template_data)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Created email template: {template.name}")
        return template

    def get_template(self, template_name: str) -> Optional[EmailTemplate]:
        """Get an email template by name."""
        return self.db.query(EmailTemplate).filter(
            EmailTemplate.name == template_name
        ).first()

    def list_templates(self, category: Optional[str] = None) -> List[EmailTemplate]:
        """List all email templates, optionally filtered by category."""
        query = self.db.query(EmailTemplate)
        if category:
            query = query.filter(EmailTemplate.category == category)
        return query.all()
