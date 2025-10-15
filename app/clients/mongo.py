from __future__ import annotations
from typing import Any, Dict, Optional
from starlette.concurrency import run_in_threadpool
from pymongo import MongoClient, ASCENDING

from app.config import get_settings

_settings = get_settings()

_client: Optional[MongoClient] = None
_db = None

async def get_db():
    global _client, _db
    if _client is None:
        # Initialize in thread to avoid blocking event loop
        def _init():
            client = MongoClient(_settings.MONGO_URI, serverSelectionTimeoutMS=3000)
            db = client[_settings.MONGO_DB]
            # Ensure indexes
            db["yields"].create_index([("pool_id", ASCENDING), ("protocol", ASCENDING), ("timestamp", ASCENDING)])
            db["users"].create_index("wallet")
            db["strategies"].create_index([("user", ASCENDING)])
            return client, db
        _client, _db = await run_in_threadpool(_init)
    return _db
