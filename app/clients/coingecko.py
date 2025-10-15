from __future__ import annotations

import logging
from typing import Dict, List

from app.config import get_settings
from app.http import HttpClient

logger = logging.getLogger(__name__)


async def get_prices_usd(http: HttpClient, coin_ids: List[str]) -> Dict[str, float]:
    """Fetch USD prices for given Coingecko coin ids."""
    if not coin_ids:
        return {}
    base = get_settings().COINGECKO_BASE_URL
    url = f"{base}/simple/price"
    params = {"ids": ",".join(coin_ids), "vs_currencies": "usd"}
    resp = await http.get(url, params=params)
    data = resp.json()
    out: Dict[str, float] = {}
    for cid, obj in data.items():
        usd = obj.get("usd")
        if isinstance(usd, (int, float)):
            out[cid] = float(usd)
    return out


async def get_eth_price_usd(http: HttpClient) -> float:
    prices = await get_prices_usd(http, ["ethereum"])
    return float(prices.get("ethereum", 0.0))
