"""Optional Redis persistence for the discovery service registry."""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional

from models import ServiceInfo

logger = logging.getLogger(__name__)

REDIS_HASH_KEY = "eyenet:discovery:services"


class RegistryRedisStore:
    """Persist ServiceInfo entries in a Redis hash. Best-effort; never blocks registration."""

    def __init__(self, redis_url: str, ttl_seconds: int = 300):
        self._url = (redis_url or "").strip()
        self._ttl = max(60, int(ttl_seconds))
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self._url)

    async def connect(self) -> bool:
        if not self._url:
            return False
        try:
            import redis.asyncio as redis

            self._client = redis.from_url(self._url, decode_responses=True)
            await self._client.ping()
            logger.info("Discovery registry Redis connected (%s)", self._url.split("@")[-1])
            return True
        except Exception as exc:
            logger.warning("Discovery registry Redis unavailable: %s", exc)
            self._client = None
            return False

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    async def load_all(self) -> Dict[str, ServiceInfo]:
        if self._client is None:
            return {}
        try:
            raw = await self._client.hgetall(REDIS_HASH_KEY)
            loaded: Dict[str, ServiceInfo] = {}
            for service_id, payload in (raw or {}).items():
                try:
                    data = json.loads(payload)
                    loaded[service_id] = ServiceInfo.model_validate(data)
                except Exception as exc:
                    logger.warning("Skip corrupt Redis service %s: %s", service_id, exc)
            if loaded:
                logger.info("Loaded %d services from Redis registry", len(loaded))
            return loaded
        except Exception as exc:
            logger.warning("Failed to load discovery registry from Redis: %s", exc)
            return {}

    async def save_service(self, service: ServiceInfo) -> None:
        if self._client is None:
            return
        try:
            payload = service.model_dump(mode="json")
            await self._client.hset(REDIS_HASH_KEY, service.service_id, json.dumps(payload))
            await self._client.expire(REDIS_HASH_KEY, self._ttl)
        except Exception as exc:
            logger.warning("Failed to persist service %s to Redis: %s", service.name, exc)

    async def delete_service(self, service_id: str) -> None:
        if self._client is None:
            return
        try:
            await self._client.hdel(REDIS_HASH_KEY, service_id)
        except Exception as exc:
            logger.warning("Failed to delete service %s from Redis: %s", service_id, exc)

    async def touch_ttl(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.expire(REDIS_HASH_KEY, self._ttl)
        except Exception:
            pass
