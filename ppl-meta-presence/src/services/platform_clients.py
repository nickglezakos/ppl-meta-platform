from __future__ import annotations

import os
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from jose import jwt

from config import config

workspace_root = Path(__file__).resolve().parents[3]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

try:
    from shared.service_discovery import deregister_service, register_service

    SERVICE_DISCOVERY_AVAILABLE = True
except ImportError:
    SERVICE_DISCOVERY_AVAILABLE = False

    async def register_service(*_args, **_kwargs) -> bool:
        return False

    async def deregister_service(*_args, **_kwargs) -> bool:
        return False


class PlatformClients:
    def __init__(self) -> None:
        self.gateway_url = os.getenv("GATEWAY_SERVICE_URL", "http://localhost:8080").rstrip("/")
        self.communications_url = config.COMMUNICATIONS_SERVICE_URL
        self.service_name = "ppl-meta-presence"
        self.service_port = int(os.getenv("PRESENCE_SERVICE_PORT", "8011"))
        self.service_version = os.getenv("PRESENCE_SERVICE_VERSION", "0.1.0")
        self._registered = False
        self.trigger_lookup: dict[str, dict[str, Any]] = {}
        self.action_lookup: dict[str, dict[str, Any]] = {}
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=True)

    async def startup(self) -> None:
        if SERVICE_DISCOVERY_AVAILABLE:
            host = self._detect_ip()
            self._registered = await register_service(
                name=self.service_name,
                service_type="backend",
                version=self.service_version,
                host=host,
                port=self.service_port,
                health_endpoint="/health",
                capabilities=["presence", "qr", "session-orchestration"],
                metadata={
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "gateway_url": self.gateway_url,
                },
            )

    async def shutdown(self) -> None:
        if self._registered:
            await deregister_service(self.service_name)
        await self._http_client.aclose()

    async def start_instant_detection(self, camera_id: str) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.gateway_url}/api/v1/instant-detection/start/{camera_id}"
        )
        response.raise_for_status()
        return response.json()

    async def get_instant_detection_status(self) -> Dict[str, Any]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/instant-detection/status"
        )
        response.raise_for_status()
        return response.json()

    async def get_instant_detection_results(self, camera_id: str) -> Dict[str, Any]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/instant-detection/results/{camera_id}"
        )
        if response.status_code == 404:
            return {"success": False, "detail": "No instant detection results yet"}
        response.raise_for_status()
        return response.json()

    async def stop_instant_detection(self, camera_id: str) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.gateway_url}/api/v1/instant-detection/stop/{camera_id}"
        )
        response.raise_for_status()
        return response.json()

    async def list_cameras(self, token: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            "http://localhost:8005/api/v1/cameras/",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    async def connect_camera(self, camera_id: str) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"http://localhost:8005/api/v1/cameras/{camera_id}/connect",
            headers=self._camera_service_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def disconnect_camera(self, camera_id: str) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"http://localhost:8005/api/v1/cameras/{camera_id}/disconnect",
            headers=self._camera_service_headers(),
        )
        response.raise_for_status()
        return response.json()

    def _camera_service_headers(self) -> Dict[str, str]:
        if not config.SERVICE_SECRET:
            raise RuntimeError("Presence service is missing SERVICE_SECRET for camera lifecycle calls")

        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": config.SERVICE_NAME,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=5)).timestamp()),
            },
            config.SERVICE_SECRET,
            algorithm="HS256",
        )
        return {"Authorization": f"Bearer {token}"}

    async def get_collection_by_camera_device_id(self, camera_device_id: str, token: str) -> Optional[Dict[str, Any]]:
        response = await self._http_client.get(
            f"http://localhost:8000/api/v1/media/collections/by-camera/{camera_device_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def list_collections(self, token: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            "http://localhost:8000/api/v1/media/collections",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    async def create_audit_log(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.communications_url}/audit/log",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_audit_log(self, token: str, log_uuid: str) -> Dict[str, Any]:
        response = await self._http_client.get(
            f"{self.communications_url}/audit/logs/{log_uuid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def list_triggers(self, token: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/triggers",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            triggers = payload.get("triggers")
            if isinstance(triggers, list):
                for trigger in triggers:
                    if isinstance(trigger, dict) and trigger.get("uuid"):
                        self.trigger_lookup[str(trigger["uuid"])] = trigger
                return triggers
        return []

    async def create_trigger(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.gateway_url}/api/v1/triggers",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_trigger(self, token: str, trigger_uuid: str) -> Dict[str, Any]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/triggers/{trigger_uuid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("uuid"):
            self.trigger_lookup[str(payload["uuid"])] = payload
        return payload

    async def list_user_actions(self, token: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/user-actions",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            actions = payload.get("actions")
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, dict) and action.get("uuid"):
                        self.action_lookup[str(action["uuid"])] = action
                return actions
        return []

    async def create_user_action(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.gateway_url}/api/v1/user-actions",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("uuid"):
            self.action_lookup[str(data["uuid"])] = data
        return data

    async def list_individual_groups(self, token: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/individual-groups",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            groups = payload.get("groups")
            if isinstance(groups, list):
                return groups
        return []

    async def create_individual_group(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.gateway_url}/api/v1/individual-groups",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_individual_group_members(self, token: str, group_id: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            f"{self.gateway_url}/api/v1/individual-groups/{group_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            members = payload.get("members")
            if isinstance(members, list):
                return members
        return []

    async def add_individual_group_members(self, token: str, group_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._http_client.post(
            f"{self.gateway_url}/api/v1/individual-groups/{group_id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _detect_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"