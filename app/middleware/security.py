from __future__ import annotations
from typing import Callable
from fastapi import Request, HTTPException

async def require_wallet(request: Request, call_next: Callable):
    if request.url.path == "/health":
        return await call_next(request)
    wallet = request.headers.get("x-wallet-address")
    if not wallet:
        raise HTTPException(status_code=401, detail="Missing x-wallet-address header")
    response = await call_next(request)
    return response
