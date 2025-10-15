from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.config import get_settings
from app.http import HttpClient

logger = logging.getLogger(__name__)


async def fetch_curve_pools(http: HttpClient) -> List[Dict[str, Any]]:
    # Use explicit mainnet endpoint to avoid redirects
    url = "https://api.curve.finance/api/getPools/ethereum/main"
    out: List[Dict[str, Any]] = []
    try:
        resp = await http.get(url)
        data = resp.json()
        pools = data.get("data", {}).get("poolData", []) or data.get("data", [])
        for p in pools:
            chain = "ethereum"
            name = p.get("name") or p.get("symbol") or "Curve Pool"
            tvl = float(p.get("usdTotal") or p.get("tvl_usd") or 0.0)
            apy = 0.0
            # Curve returns multiple APY fields depending on endpoint version
            if isinstance(p.get("apy"), (int, float)):
                apy = float(p.get("apy")) * 100 if p.get("apy") < 1 else float(p.get("apy"))
            elif isinstance(p.get("apys"), dict):
                day = p["apys"].get("day")
                if isinstance(day, (int, float)):
                    apy = float(day) * 100 if day < 1 else float(day)
            elif isinstance(p.get("gauge_apr"), (int, float)):
                apy = float(p.get("gauge_apr"))

            pool_id = str(p.get("address") or p.get("id") or f"curve:{chain}:{name}")
            out.append(
                {
                    "id": f"curve:{chain}:{pool_id}",
                    "protocol": "Curve",
                    "pool": name,
                    "chain": chain,
                    "apy": apy,
                    "tvl_usd": tvl,
                    "metadata": {
                        "address": p.get("address"),
                    },
                }
            )
    except Exception as e:
        logger.warning(f"Curve API fetch failed: {e}")
    return out
