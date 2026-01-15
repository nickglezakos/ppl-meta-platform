"""
Webhook service for sending HTTP requests to external endpoints.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from ..config import get_config
from ..models.communication_log import (
    CommunicationLog,
    CommunicationStatus,
    CommunicationType,
)
from ..models.webhook_config import WebhookConfig

logger = logging.getLogger(__name__)
config = get_config()


class WebhookService:
    """Service for sending webhooks."""

    def __init__(self, db: Session):
        self.db = db
        self.config = config

    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> tuple[bool, str, UUID, Optional[int], Optional[str]]:
        """
        Send a webhook request.
        
        Returns:
            tuple: (success, message, log_uuid, status_code, response_body)
        """
        if not self.config.WEBHOOK_ENABLED:
            logger.warning("Webhooks are disabled in configuration")
            return False, "Webhooks are disabled", None, None, None

        # Create communication log
        log = CommunicationLog(
            type=CommunicationType.WEBHOOK,
            status=CommunicationStatus.PENDING,
            recipient=str(url),
            content=method,
            payload=payload,
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            attempts=0,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        # Prepare headers
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        # Retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                log.attempts += 1
                log.last_attempt_at = datetime.now(timezone.utc)
                self.db.commit()

                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(
                        method=method.upper(),
                        url=str(url),
                        json=payload,
                        headers=request_headers,
                    )

                # Update log with response
                log.response_status_code = response.status_code
                log.response_body = response.text[:5000]  # Limit response body size

                if 200 <= response.status_code < 300:
                    # Success
                    log.status = CommunicationStatus.DELIVERED
                    log.delivered_at = datetime.now(timezone.utc)
                    self.db.commit()

                    logger.info(f"✅ Webhook sent successfully to {url}. Status: {response.status_code}. Log UUID: {log.uuid}")
                    return True, "Webhook sent successfully", log.uuid, response.status_code, response.text

                else:
                    # Non-2xx response
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    if attempt < max_retries - 1:
                        log.status = CommunicationStatus.RETRYING
                        logger.warning(f"Webhook attempt {attempt + 1} failed with status {response.status_code}. Retrying...")
                        self.db.commit()
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # Final attempt failed
                        log.status = CommunicationStatus.FAILED
                        log.failed_at = datetime.now(timezone.utc)
                        log.error_message = last_error
                        self.db.commit()
                        logger.error(f"❌ Webhook failed after {max_retries} attempts: {last_error}")
                        return False, last_error, log.uuid, response.status_code, response.text

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    log.status = CommunicationStatus.RETRYING
                    logger.warning(f"Webhook attempt {attempt + 1} failed: {e}. Retrying...")
                    self.db.commit()
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Final attempt failed
                    log.status = CommunicationStatus.FAILED
                    log.failed_at = datetime.now(timezone.utc)
                    log.error_message = last_error
                    self.db.commit()
                    logger.error(f"❌ Webhook failed after {max_retries} attempts: {e}")
                    return False, f"Failed to send webhook: {str(e)}", log.uuid, None, None

        return False, "Webhook failed", log.uuid, None, None

    async def send_webhook_from_config(
        self,
        config_name: str,
        payload: Dict[str, Any],
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> tuple[bool, str, Optional[UUID], Optional[int], Optional[str]]:
        """
        Send a webhook using a saved configuration.
        
        Returns:
            tuple: (success, message, log_uuid, status_code, response_body)
        """
        # Get webhook config
        webhook_config = self.db.query(WebhookConfig).filter(
            WebhookConfig.name == config_name,
            WebhookConfig.is_active == True
        ).first()

        if not webhook_config:
            logger.error(f"Webhook config not found: {config_name}")
            return False, f"Webhook config '{config_name}' not found", None, None, None

        # Prepare headers with auth
        headers = dict(webhook_config.headers) if webhook_config.headers else {}
        
        if webhook_config.auth_type == "bearer" and webhook_config.auth_token:
            headers["Authorization"] = f"Bearer {webhook_config.auth_token}"
        elif webhook_config.auth_type == "api_key" and webhook_config.auth_token:
            headers["X-API-Key"] = webhook_config.auth_token

        # Send webhook
        success, message, log_uuid, status_code, response_body = await self.send_webhook(
            url=webhook_config.url,
            payload=payload,
            method=webhook_config.method,
            headers=headers,
            timeout=webhook_config.timeout_seconds,
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            max_retries=webhook_config.max_retries,
            retry_delay=webhook_config.retry_delay_seconds,
        )

        # Update webhook config statistics
        webhook_config.total_calls += 1
        webhook_config.last_called_at = datetime.now(timezone.utc)
        
        if success:
            webhook_config.successful_calls += 1
            webhook_config.last_success_at = datetime.now(timezone.utc)
        else:
            webhook_config.failed_calls += 1
            webhook_config.last_failure_at = datetime.now(timezone.utc)
        
        self.db.commit()

        return success, message, log_uuid, status_code, response_body

    def create_webhook_config(self, config_data: dict) -> WebhookConfig:
        """Create a new webhook configuration."""
        webhook_config = WebhookConfig(**config_data)
        self.db.add(webhook_config)
        self.db.commit()
        self.db.refresh(webhook_config)
        logger.info(f"Created webhook config: {webhook_config.name}")
        return webhook_config

    def get_webhook_config(self, config_name: str) -> Optional[WebhookConfig]:
        """Get a webhook configuration by name."""
        return self.db.query(WebhookConfig).filter(
            WebhookConfig.name == config_name
        ).first()

    def list_webhook_configs(self, is_active: Optional[bool] = None):
        """List all webhook configurations."""
        query = self.db.query(WebhookConfig)
        if is_active is not None:
            query = query.filter(WebhookConfig.is_active == is_active)
        return query.all()
