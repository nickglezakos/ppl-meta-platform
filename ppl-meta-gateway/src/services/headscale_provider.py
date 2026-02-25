from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

from shared.networking.vpn_provider import VPNDevice, VPNEnrollment, VPNHealth, VPNProvider


class HeadscaleProvider(VPNProvider):
    """Headscale-backed VPN provider.

    NOTE: Headscale's REST API is documented by the server itself at `/swagger`.
    We intentionally keep enroll/list/revoke minimal here until we verify the
    exact endpoint shapes from the running Headscale version in this stack.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        verify_tls: bool = True,
        timeout_s: float = 10.0,
        user_name: str = "ppl-meta",
        preauth_expire_minutes: int = 60 * 24,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._verify_tls = verify_tls
        self._timeout_s = timeout_s
        self._user_name = user_name
        self._preauth_expire_minutes = preauth_expire_minutes

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        json: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(
            timeout=self._timeout_s, verify=self._verify_tls
        ) as client:
            resp = await client.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json,
            )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Headscale API error {resp.status_code} for {method} {path}: {resp.text}"
            )
        if not resp.content:
            return {}
        return resp.json()

    async def _ensure_user_id(self) -> str:
        if not self._user_name:
            raise RuntimeError("HEADSCALE_USER_NAME is not set")

        data = await self._request("GET", "/api/v1/user", params={"name": self._user_name})
        users = data.get("users") or []
        if users:
            return str(users[0].get("id"))

        created = await self._request(
            "POST",
            "/api/v1/user",
            json={"name": self._user_name, "displayName": self._user_name},
        )
        user = (created or {}).get("user") or {}
        user_id = user.get("id")
        if not user_id:
            raise RuntimeError(f"Failed to create headscale user: {created}")
        return str(user_id)

    async def health(self) -> VPNHealth:
        details: Dict[str, Any] = {"base_url": self._base_url}
        if not self._api_key:
            return VPNHealth(
                enabled=True,
                provider="headscale",
                ok=False,
                details={**details, "error": "HEADSCALE_API_KEY not set"},
            )

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_s, verify=self._verify_tls
            ) as client:
                version_resp = await client.get(f"{self._base_url}/version")
                details["version_status"] = version_resp.status_code
                if version_resp.headers.get("content-type", "").startswith("application/json"):
                    details["version"] = version_resp.json()
                else:
                    details["version"] = version_resp.text.strip()

                user_resp = await client.get(
                    f"{self._base_url}/api/v1/user",
                    headers=self._headers(),
                    params={"name": self._user_name} if self._user_name else None,
                )
                details["user_status"] = user_resp.status_code
                ok = version_resp.status_code < 500 and user_resp.status_code < 500
                if user_resp.status_code >= 400:
                    details["auth_error"] = user_resp.text

            return VPNHealth(
                enabled=True,
                provider="headscale",
                ok=ok,
                details=details,
            )
        except Exception as exc:
            return VPNHealth(
                enabled=True,
                provider="headscale",
                ok=False,
                details={**details, "error": str(exc)},
            )

    async def enroll_device(
        self, *, device_type: str, device_name: str, tags: List[str]
    ) -> VPNEnrollment:
        user_id = await self._ensure_user_id()

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=max(1, int(self._preauth_expire_minutes))
        )
        payload: Dict[str, Any] = {
            "user": user_id,
            "reusable": False,
            "ephemeral": False,
            "expiration": expires_at.isoformat(),
            "aclTags": tags or [],
        }
        created = await self._request("POST", "/api/v1/preauthkey", json=payload)
        pre = (created or {}).get("preAuthKey") or {}
        key = pre.get("key")
        if not key:
            raise RuntimeError(f"Headscale did not return a preAuthKey.key: {created}")

        instructions = {
            "device_name": device_name,
            "device_type": device_type,
            "headscale_url": self._base_url,
            "steps": [
                "Install Tailscale client on the device",
                f"Set the control server URL to {self._base_url}",
                "Run enrollment using the auth key returned",
            ],
        }
        return VPNEnrollment(auth_key=str(key), device_id=None, instructions=instructions)

    async def list_devices(self) -> List[VPNDevice]:
        data = await self._request("GET", "/api/v1/node")
        nodes = data.get("nodes") or []
        devices: List[VPNDevice] = []
        for n in nodes:
            user = (n.get("user") or {}).get("name")
            devices.append(
                VPNDevice(
                    id=str(n.get("id")),
                    name=str(n.get("givenName") or n.get("name") or n.get("id")),
                    user=str(user) if user is not None else None,
                    online=bool(n.get("online")) if n.get("online") is not None else None,
                    addresses=list(n.get("ipAddresses") or []),
                    raw=n,
                )
            )
        return devices

    async def revoke_device(self, device_id: str) -> None:
        # Headscale supports deleting a node entirely.
        await self._request("DELETE", f"/api/v1/node/{device_id}")

    async def device_status(self, device_id: str) -> VPNDevice:
        data = await self._request("GET", f"/api/v1/node/{device_id}")
        node = (data or {}).get("node") or {}
        user = (node.get("user") or {}).get("name")
        return VPNDevice(
            id=str(node.get("id")),
            name=str(node.get("givenName") or node.get("name") or node.get("id")),
            user=str(user) if user is not None else None,
            online=bool(node.get("online")) if node.get("online") is not None else None,
            addresses=list(node.get("ipAddresses") or []),
            raw=node,
        )
