from __future__ import annotations

import logging
from typing import Any, Dict

from app.config import get_settings
from app.http import HttpClient

logger = logging.getLogger(__name__)


async def get_gas_oracle_gwei(http: HttpClient) -> Dict[str, float]:
    key = get_settings().ETHERSCAN_API_KEY
    if not key:
        return {}
    url = "https://api.etherscan.io/api"
    params = {"module": "gastracker", "action": "gasoracle", "apikey": key}
    try:
        resp = await http.get(url, params=params)
        data = resp.json()
        if data.get("status") == "1":
            result = data.get("result", {})
            return {
                "SafeGasPrice": float(result.get("SafeGasPrice", 0.0)),
                "ProposeGasPrice": float(result.get("ProposeGasPrice", 0.0)),
                "FastGasPrice": float(result.get("FastGasPrice", 0.0)),
            }
    except Exception as e:
        logger.warning(f"Etherscan gas oracle failed: {e}")
    return {}
