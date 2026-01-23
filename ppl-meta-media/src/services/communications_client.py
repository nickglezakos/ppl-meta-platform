"""Communications Service Client for Media Service.

This client provides methods to interact with the Communications Service
via REST API for sending emails, webhooks, and logging audit events.
"""

import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CommunicationsClient:
    """Client for interacting with Communications Service via REST API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the Communications Client.
        
        Args:
            base_url: Base URL of the Communications Service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send an email via Communications Service.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            text_body: Plain text email body
            html_body: Optional HTML email body
            cc: Optional list of CC email addresses
            triggered_by: Optional identifier of what triggered this email
            trigger_type: Optional type of trigger (e.g., "trigger_action")
            trigger_id: Optional UUID of the trigger
            payload: Optional additional structured data (e.g., demographics)
            
        Returns:
            Dict with success status and log UUID or error message
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request_body = {
                    "to": to,
                    "subject": subject,
                    "text_body": text_body,
                    "html_body": html_body,
                    "triggered_by": triggered_by,
                    "trigger_type": trigger_type,
                    "trigger_id": trigger_id,
                }
                if cc:
                    request_body["cc"] = cc
                if payload:
                    request_body["payload"] = payload
                    
                response = await client.post(
                    f"{self.base_url}/api/v1/email/send",
                    json=request_body
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending email via Communications Service: {e.response.status_code} - {e.response.text}")
            return {"success": False, "message": f"HTTP {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            logger.error(f"Request error sending email via Communications Service: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error sending email via Communications Service: {e}")
            return {"success": False, "message": str(e)}
    
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a webhook via Communications Service.
        
        Args:
            url: Target webhook URL
            payload: Data to send in webhook payload
            method: HTTP method (POST, PUT, etc.)
            headers: Optional HTTP headers to include
            triggered_by: Optional identifier of what triggered this webhook
            trigger_type: Optional type of trigger
            trigger_id: Optional UUID of the trigger
            
        Returns:
            Dict with success status, status code, and log UUID or error message
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/webhook/send",
                    json={
                        "url": url,
                        "method": method,
                        "payload": payload,
                        "headers": headers,
                        "triggered_by": triggered_by,
                        "trigger_type": trigger_type,
                        "trigger_id": trigger_id,
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending webhook via Communications Service: {e.response.status_code} - {e.response.text}")
            return {"success": False, "message": f"HTTP {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            logger.error(f"Request error sending webhook via Communications Service: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error sending webhook via Communications Service: {e}")
            return {"success": False, "message": str(e)}
    
    async def send_webhook_from_config(
        self,
        config_name: str,
        payload: Dict[str, Any],
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a webhook using a saved configuration.
        
        Args:
            config_name: Name of the saved webhook configuration
            payload: Data to send in webhook payload
            triggered_by: Optional identifier of what triggered this webhook
            trigger_type: Optional type of trigger
            trigger_id: Optional UUID of the trigger
            
        Returns:
            Dict with success status, status code, and log UUID or error message
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/webhook/send/config/{config_name}",
                    json=payload,
                    params={
                        "triggered_by": triggered_by,
                        "trigger_type": trigger_type,
                        "trigger_id": trigger_id,
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending webhook from config via Communications Service: {e.response.status_code} - {e.response.text}")
            return {"success": False, "message": f"HTTP {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            logger.error(f"Request error sending webhook from config via Communications Service: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error sending webhook from config via Communications Service: {e}")
            return {"success": False, "message": str(e)}
    
    async def log_audit_event(
        self,
        event_type: str,
        event_source: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "info",
    ) -> Dict[str, Any]:
        """Create an audit log entry.
        
        Args:
            event_type: Type of event (e.g., "trigger_fired")
            event_source: Source service (e.g., "media_service")
            event_data: Dictionary containing event details
            user_id: Optional user identifier
            ip_address: Optional IP address
            severity: Log severity level (info, warning, error, critical)
            
        Returns:
            Dict with success status and log UUID or error message
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/audit/log",
                    json={
                        "event_type": event_type,
                        "event_source": event_source,
                        "event_data": event_data,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "severity": severity,
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error logging audit event via Communications Service: {e.response.status_code} - {e.response.text}")
            return {"success": False, "message": f"HTTP {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            logger.error(f"Request error logging audit event via Communications Service: {e}")
            return {"success": False, "message": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error logging audit event via Communications Service: {e}")
            return {"success": False, "message": str(e)}
