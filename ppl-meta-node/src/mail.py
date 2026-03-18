"""Mail service - sends emails via the Communications Service."""

import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


async def send_email(subject: str, email_to: str, body: str) -> bool:
    """Send email via the Communications Service (port 8009)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.COMMUNICATIONS_SERVICE_URL}/api/v1/email/send",
                json={
                    "to": [email_to],
                    "subject": subject,
                    "text_body": body,
                    "html_body": body,
                    "triggered_by": "node-service",
                    "trigger_type": "system",
                },
            )
            if response.status_code == 200:
                logger.info("Email sent to %s via Communications Service", email_to)
                return True
            else:
                logger.error(
                    "Communications Service returned %s: %s",
                    response.status_code,
                    response.text,
                )
                return False
    except Exception as e:
        logger.error("Failed to send email via Communications Service: %s", e)
        return False
