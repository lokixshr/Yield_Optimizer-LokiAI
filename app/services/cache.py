from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from app.models import YieldPool, HistoryEntry

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, redis: Redis):
        self.r = redis

    async def save_latest_pools(self, pools: List[YieldPool]) -> None:
        key = "pools:latest"
        payload = json.dumps([p.model_dump() for p in pools])
        await self.r.set(key, payload, ex=600)

    async def get_latest_pools(self) -> List[YieldPool]:
        key = "pools:latest"
        data = await self.r.get(key)
        if not data:
            return []
        arr = json.loads(data)
        return [YieldPool(**x) for x in arr]

    async def append_history(self, pools: List[YieldPool], max_entries: int) -> None:
        entry = HistoryEntry(timestamp=int(time.time()), pools=pools).model_dump()
        await self.r.lpush("history:pools", json.dumps(entry))
        await self.r.ltrim("history:pools", 0, max_entries - 1)

    async def get_history(self, since_ts: Optional[int] = None) -> List[HistoryEntry]:
        items = await self.r.lrange("history:pools", 0, -1)
        out: List[HistoryEntry] = []
        for raw in items:
            try:
                obj = json.loads(raw)
                if since_ts and obj.get("timestamp", 0) < since_ts:
                    continue
                out.append(HistoryEntry(**obj))
            except Exception:
                continue
        return list(reversed(out))  # oldest first
