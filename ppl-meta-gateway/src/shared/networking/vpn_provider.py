from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class VPNDevice:
    id: str
    name: str
    user: Optional[str] = None
    online: Optional[bool] = None
    addresses: Optional[List[str]] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class VPNHealth:
    enabled: bool
    provider: str
    ok: bool
    details: Dict[str, Any]


@dataclass(frozen=True)
class VPNEnrollment:
    auth_key: str
    device_id: Optional[str] = None
    instructions: Optional[Dict[str, Any]] = None


class VPNProvider(ABC):
    """Abstract VPN provider interface.

    This is intentionally small and focused on device enrollment + status.
    """

    @abstractmethod
    async def health(self) -> VPNHealth:
        raise NotImplementedError

    @abstractmethod
    async def enroll_device(
        self,
        *,
        device_type: str,
        device_name: str,
        tags: List[str],
    ) -> VPNEnrollment:
        raise NotImplementedError

    @abstractmethod
    async def list_devices(self) -> List[VPNDevice]:
        raise NotImplementedError

    @abstractmethod
    async def revoke_device(self, device_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def device_status(self, device_id: str) -> VPNDevice:
        raise NotImplementedError


class NullVPNProvider(VPNProvider):
    async def health(self) -> VPNHealth:
        return VPNHealth(
            enabled=False,
            provider="none",
            ok=True,
            details={"message": "VPN provider disabled"},
        )

    async def enroll_device(
        self, *, device_type: str, device_name: str, tags: List[str]
    ) -> VPNEnrollment:
        raise NotImplementedError("VPN provider is disabled")

    async def list_devices(self) -> List[VPNDevice]:
        return []

    async def revoke_device(self, device_id: str) -> None:
        raise NotImplementedError("VPN provider is disabled")

    async def device_status(self, device_id: str) -> VPNDevice:
        raise NotImplementedError("VPN provider is disabled")
