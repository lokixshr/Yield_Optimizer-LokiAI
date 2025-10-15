from __future__ import annotations

import asyncio
import logging
from redis.asyncio import Redis

from app.config import get_settings
from app.http import HttpClient
from app.services.aggregator import Aggregator
from app.services.cache import Cache
from app.services.history import HistoryService

logger = logging.getLogger(__name__)


class BackgroundRefresher:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.http = HttpClient()
        self.aggregator = Aggregator(self.http)
        self.cache = Cache(redis)
        self.history = HistoryService(self.cache, max_entries=get_settings().HISTORY_MAX_ENTRIES)
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        # Do an immediate refresh on start to warm cache and DB, then start loop
        pools = await self.aggregator.refresh()
        await self.cache.save_latest_pools(pools)
        await self.history.record(pools)
        logger.info(f"✅ Yield Optimizer ready – pools: {len(pools)}")
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            await self._task
        await self.http.aclose()

    async def _run_loop(self) -> None:
        settings = get_settings()
        interval = settings.REFRESH_INTERVAL_SECONDS
        logger.info(f"Background refresher started (interval={interval}s)")
        while not self._stopping.is_set():
            try:
                pools = await self.aggregator.refresh()
                await self.cache.save_latest_pools(pools)
                await self.history.record(pools)
                logger.info(f"Refreshed pools: {len(pools)}")
            except Exception as e:
                logger.exception(f"Refresh iteration failed: {e}")
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
