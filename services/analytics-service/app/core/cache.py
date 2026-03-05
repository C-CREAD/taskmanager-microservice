"""
Simple async Redis cache wrapper.
Used to avoid hammering the Task Service on every dashboard load.

Usage:
    value = await cache.get("my_key")
    if value is None:
        value = await compute_expensive_thing()
        await cache.set("my_key", value, ttl=300)
"""
from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


class Cache:
    async def get(self, key: str) -> dict | list | None:
        try:
            r = await get_redis()
            raw = await r.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("Cache GET failed for key=%s: %s", key, exc)
            return None

    async def set(self, key: str, value: dict | list, ttl: int | None = None) -> None:
        try:
            r = await get_redis()
            ttl = ttl or settings.CACHE_TTL_SECONDS
            await r.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.warning("Cache SET failed for key=%s: %s", key, exc)

    async def delete(self, key: str) -> None:
        try:
            r = await get_redis()
            await r.delete(key)
        except Exception as exc:
            logger.warning("Cache DELETE failed for key=%s: %s", key, exc)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a glob pattern (e.g. 'analytics:user_id:*')."""
        try:
            r = await get_redis()
            async for key in r.scan_iter(match=pattern):
                await r.delete(key)
        except Exception as exc:
            logger.warning("Cache DELETE PATTERN failed for pattern=%s: %s", pattern, exc)


cache = Cache()
