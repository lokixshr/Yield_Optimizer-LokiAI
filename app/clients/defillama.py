from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.http import HttpClient

logger = logging.getLogger(__name__)


async def fetch_llama_pools(http: HttpClient, chains: List[str] | None = None, protocols: List[str] | None = None) -> List[Dict[str, Any]]:
    """Fetch pools from DefiLlama Yields API and normalize.

    Docs: https://yields.llama.fi/pools
    """
    url = "https://yields.llama.fi/pools"
    out: List[Dict[str, Any]] = []
    try:
        resp = await http.get(url)
        data = resp.json()
        pools = data.get("data", []) or data.get("pools", []) or []
        # Default to only Aave/Curve/Sushi to control request volume and align with protocols of interest
        allowed = [x.lower() for x in (protocols or ["aave", "curve", "sushiswap"])]
        for p in pools:
            project = str(p.get("project") or p.get("projectName") or "unknown")
            if project.lower() not in allowed:
                continue
            chain = str(p.get("chain") or "ethereum").lower()
            if chains and chain not in [c.lower() for c in chains]:
                continue
            apy = float(p.get("apy") or 0.0)
            tvl = float(p.get("tvlUsd") or p.get("tvl") or 0.0)
            pool_id = str(p.get("pool") or p.get("symbol") or p.get("address") or "pool")
            symbol = p.get("symbol") or p.get("symbolName")
            out.append(
                {
                    "id": f"llama:{chain}:{project}:{pool_id}",
                    "protocol": project.capitalize() if project else "DefiLlama",
                    "pool": symbol or pool_id,
                    "chain": chain,
                    "apy": apy,
                    "tvl_usd": tvl,
                    "metadata": {
                        "llama": {
                            "apyStd30d": p.get("apyStd30d"),
                            "apyMean30d": p.get("apyMean30d"),
                            "url": p.get("url"),
                        }
                    },
                }
            )
    except Exception as e:
        logger.warning(f"DefiLlama fetch failed: {e}")
    return out
