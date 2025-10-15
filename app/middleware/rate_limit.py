from __future__ import annotations
import time
from fastapi import Request, HTTPException

from app.clients.redis import get_redis

WINDOW_SECONDS = 60
MAX_REQUESTS = 60

async def rate_limiter(request: Request, call_next):
    # Key per wallet and IP
    wallet = request.headers.get("x-wallet-address", "anon")
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate:{wallet}:{client_ip}:{int(time.time() // WINDOW_SECONDS)}"

    redis = await get_redis()
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, WINDOW_SECONDS)
    if current > MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later")

    response = await call_next(request)
    return response
