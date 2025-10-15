from __future__ import annotations
import asyncio
import time
from typing import Any, Dict, Optional
import httpx

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=10.0)

class HttpClient:
    def __init__(self) -> None:
        limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
        self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, limits=limits)

    async def get(self, url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        return await self._request("GET", url, params=params, headers=headers)

    async def post(self, url: str, *, json: Any | None = None, data: Any | None = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        return await self._request("POST", url, json=json, data=data, headers=headers)

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        # Simple retry with backoff for transient errors
        retries = 3
        backoff = 0.5
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                resp = await self._client.request(method, url, **kwargs)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                return resp
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                last_exc = e
                if attempt < retries - 1:
                    await asyncio.sleep(backoff * (2 ** attempt))
                else:
                    raise
        # Should not reach here
        if last_exc:
            raise last_exc
        raise RuntimeError("HTTP request failed without exception")

    async def aclose(self) -> None:
        await self._client.aclose()

http_client = HttpClient()
