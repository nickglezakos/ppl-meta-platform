"""Mail service for sending emails."""

import logging

logger = logging.getLogger(__name__)


async def send_email(subject: str, email_to: str, body: str) -> bool:
    """Send email - currently disabled, returns False."""
    logger.warning("Email sending is currently disabled - configuration needed")
    logger.info("Would send email to %s with subject: %s", email_to, subject)
    return False
