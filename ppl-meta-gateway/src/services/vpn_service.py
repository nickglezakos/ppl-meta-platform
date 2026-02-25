from __future__ import annotations

from typing import List

from config import settings
from services.headscale_provider import HeadscaleProvider
from shared.networking.vpn_provider import NullVPNProvider, VPNDevice, VPNEnrollment, VPNHealth, VPNProvider


def _normalize_provider_name(name: str) -> str:
    return (name or "").strip().lower()


def load_vpn_provider() -> VPNProvider:
    provider_name = _normalize_provider_name(getattr(settings, "vpn_provider", "none"))
    if provider_name in ("", "none", "disabled", "off"):
        return NullVPNProvider()

    if provider_name in ("headscale", "headscale_http"):
        return HeadscaleProvider(
            base_url=getattr(settings, "headscale_url", "http://localhost:8081"),
            api_key=getattr(settings, "headscale_api_key", ""),
            verify_tls=bool(getattr(settings, "headscale_verify_tls", True)),
            user_name=getattr(settings, "headscale_user_name", "ppl-meta"),
            preauth_expire_minutes=int(
                getattr(settings, "headscale_preauth_expire_minutes", 60 * 24)
            ),
        )

    # Unknown provider => treat as disabled (non-breaking default)
    return NullVPNProvider()


class VPNService:
    def __init__(self) -> None:
        self._provider: VPNProvider | None = None

    @property
    def provider(self) -> VPNProvider:
        if self._provider is None:
            self._provider = load_vpn_provider()
        return self._provider

    async def health(self) -> VPNHealth:
        return await self.provider.health()

    async def enroll_device(self, *, device_type: str, device_name: str, tags: List[str]) -> VPNEnrollment:
        return await self.provider.enroll_device(
            device_type=device_type, device_name=device_name, tags=tags
        )

    async def list_devices(self) -> List[VPNDevice]:
        return await self.provider.list_devices()

    async def revoke_device(self, device_id: str) -> None:
        return await self.provider.revoke_device(device_id)

    async def device_status(self, device_id: str) -> VPNDevice:
        return await self.provider.device_status(device_id)


vpn_service = VPNService()
