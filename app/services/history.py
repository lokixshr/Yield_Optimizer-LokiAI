from __future__ import annotations

import time
from typing import List

from app.models import HistoryEntry, YieldPool
from app.services.cache import Cache


class HistoryService:
    def __init__(self, cache: Cache, max_entries: int):
        self.cache = cache
        self.max_entries = max_entries

    async def record(self, pools: List[YieldPool]) -> None:
        await self.cache.append_history(pools, self.max_entries)

    async def get_30d(self) -> List[HistoryEntry]:
        since = int(time.time()) - 30 * 24 * 3600
        return await self.cache.get_history(since_ts=since)
