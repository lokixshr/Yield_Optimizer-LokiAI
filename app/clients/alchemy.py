from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.config import get_settings
from app.http import HttpClient

logger = logging.getLogger(__name__)


async def _rpc(http: HttpClient, method: str, params: Optional[list] = None) -> Any:
    url = get_settings().alchemy_rpc_url()
    if not url:
        raise RuntimeError("Alchemy API key not configured")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    resp = await http.post(url, json=payload)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Alchemy RPC error: {data['error']}")
    return data.get("result")


async def get_gas_price_gwei(http: HttpClient) -> float:
    try:
        wei_hex = await _rpc(http, "eth_gasPrice")
        wei = int(wei_hex, 16)
        gwei = wei / 1e9
        return float(gwei)
    except Exception as e:
        logger.warning(f"Alchemy gas price failed: {e}")
        return 0.0


async def get_eth_balance(http: HttpClient, address: str) -> float:
    try:
        wei_hex = await _rpc(http, "eth_getBalance", [address, "latest"])
        wei = int(wei_hex, 16)
        return wei / 1e18
    except Exception as e:
        logger.warning(f"Alchemy get balance failed: {e}")
        return 0.0
