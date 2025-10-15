from __future__ import annotations
from typing import Optional
from redis.asyncio import Redis

from app.config import get_settings

_settings = get_settings()

_redis: Optional[Redis] = None

async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(_settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis
