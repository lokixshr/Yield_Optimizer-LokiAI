from __future__ import annotations

import logging
from typing import Optional, Set

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)

# Isolated collections for Yield Optimizer only
ALLOWED_COLLECTIONS: Set[str] = {
    "yield_optimizer_yields",
    "yield_optimizer_strategies",
    "yield_optimizer_users",
}

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _ensure_config() -> None:
    settings = get_settings()
    if not (settings.MONGODB_URI or settings.MONGO_URI):
        raise RuntimeError("MONGODB_URI is not configured in environment (.env)")
    if not (settings.MONGO_DB_NAME or settings.MONGO_DB):
        raise RuntimeError("MONGO_DB_NAME is not configured in environment (.env)")


async def connect() -> None:
    global _client, _db
    if _client and _db:
        return

    _ensure_config()
    settings = get_settings()

    # Create client with sane timeouts; motor is async and safe for FastAPI
    _client = AsyncIOMotorClient(
        settings.get_mongo_uri(),
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        retryWrites=True,
        appname="loki-yield-optimizer",
    )
    _db = _client[settings.get_mongo_db_name()]

    # Create isolated collections if missing
    existing = set(await _db.list_collection_names())
    for name in ALLOWED_COLLECTIONS:
        if name not in existing:
            try:
                await _db.create_collection(name)
            except Exception:
                # If created by a racing process, ignore
                pass

    # Log startup message
    logger.info(
        "Isolated DB connection established to %s/%s",
        settings.get_mongo_db_name(),
        "yield_optimizer_*",
    )


async def close() -> None:
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None


def get_collection(name: str) -> AsyncIOMotorCollection:
    """Return a handle to one of the isolated collections only.

    Safety: Raises PermissionError if attempting to access any other collection.
    """
    if name not in ALLOWED_COLLECTIONS:
        raise PermissionError(
            f"Access to collection '{name}' is not allowed. Use one of: {sorted(ALLOWED_COLLECTIONS)}"
        )
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect() on startup.")
    return _db[name]


# Convenience getters (optional)

def yields_collection() -> AsyncIOMotorCollection:
    return get_collection("yield_optimizer_yields")


def strategies_collection() -> AsyncIOMotorCollection:
    return get_collection("yield_optimizer_strategies")


def users_collection() -> AsyncIOMotorCollection:
    return get_collection("yield_optimizer_users")
