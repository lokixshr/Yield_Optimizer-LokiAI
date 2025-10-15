from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, timeout: float = 15.0):
        self._client = httpx.AsyncClient(timeout=timeout)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        logger.debug(f"HTTP GET {url} params={params}")
        resp = await self._client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        logger.debug(f"HTTP POST {url} json_keys={list(json.keys()) if json else None}")
        resp = await self._client.post(url, json=json, headers=headers)
        resp.raise_for_status()
        return resp

    async def aclose(self) -> None:
        await self._client.aclose()
