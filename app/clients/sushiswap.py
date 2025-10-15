from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from app.config import get_settings
from app.clients.graphql import graphql_query
from app.http import HttpClient

logger = logging.getLogger(__name__)


SUSHI_SUBGRAPHS = {
    "ethereum": lambda s: s.SUSHISWAP_ETH_SUBGRAPH,
    "polygon": lambda s: s.SUSHISWAP_POLYGON_SUBGRAPH,
}


def _sushi_gateway_url() -> str | None:
    s = get_settings()
    if not (s.THEGRAPH_API_KEY and s.SUSHI_SUBGRAPH_ID):
        return None
    return f"https://gateway.thegraph.com/api/{s.THEGRAPH_API_KEY}/subgraphs/id/{s.SUSHI_SUBGRAPH_ID}"


async def fetch_top_pools_24h(http: HttpClient, chains: List[str] | None = None, first: int = 30) -> List[Dict[str, Any]]:
    """Fetch top SushiSwap pools by 24h volume and compute APY from fee APR approximation.
    APY ≈ (dailyVolumeUSD * 0.0025 / reserveUSD) * 365 * 100
    """
    settings = get_settings()
    day_id = int(time.time() // 86400) - 1  # yesterday UTC day start

    query = """
    query($dayId: Int!, $first: Int!) {
      pairDayDatas(first: $first, orderBy: dailyVolumeUSD, orderDirection: desc, where: { date: $dayId }) {
        pairAddress
        token0 { symbol }
        token1 { symbol }
        reserveUSD
        dailyVolumeUSD
      }
    }
    """

    results: List[Dict[str, Any]] = []
    target_chains = chains or list(SUSHI_SUBGRAPHS.keys())

    # Prefer The Graph gateway if configured (works across chains via same subgraph id)
    gw = _sushi_gateway_url()
    if gw:
        try:
            data = await graphql_query(http, gw, query, {"dayId": day_id * 86400, "first": first})
            daydatas = data.get("pairDayDatas", [])
            for d in daydatas:
                reserve = float(d.get("reserveUSD") or 0.0)
                vol = float(d.get("dailyVolumeUSD") or 0.0)
                apy = 0.0
                if reserve > 0:
                    apy = (vol * 0.0025 / reserve) * 365.0 * 100.0
                pool_name = f"{d['token0']['symbol']}-{d['token1']['symbol']}"
                results.append(
                    {
                        "id": f"sushiswap:ethereum:{d['pairAddress']}",
                        "protocol": "SushiSwap",
                        "pool": pool_name,
                        "chain": "ethereum",
                        "apy": apy,
                        "tvl_usd": reserve,
                        "metadata": {
                            "pairAddress": d.get("pairAddress"),
                            "dailyVolumeUSD": vol,
                        },
                    }
                )
        except Exception as e:
            logger.warning(f"SushiSwap fetch via gateway failed: {e}")
            # fall through to legacy per-chain fetch

    if results:
        return results

    for chain in target_chains:
        try:
            url = SUSHI_SUBGRAPHS[chain](settings)
        except KeyError:
            continue
        try:
            data = await graphql_query(http, url, query, {"dayId": day_id * 86400, "first": first})
            daydatas = data.get("pairDayDatas", [])
            for d in daydatas:
                reserve = float(d.get("reserveUSD") or 0.0)
                vol = float(d.get("dailyVolumeUSD") or 0.0)
                apy = 0.0
                if reserve > 0:
                    apy = (vol * 0.0025 / reserve) * 365.0 * 100.0
                pool_name = f"{d['token0']['symbol']}-{d['token1']['symbol']}"
                results.append(
                    {
                        "id": f"sushiswap:{chain}:{d['pairAddress']}",
                        "protocol": "SushiSwap",
                        "pool": pool_name,
                        "chain": chain,
                        "apy": apy,
                        "tvl_usd": reserve,
                        "metadata": {
                            "pairAddress": d.get("pairAddress"),
                            "dailyVolumeUSD": vol,
                        },
                    }
                )
        except Exception as e:
            logger.warning(f"SushiSwap fetch failed for {chain}: {e}")
    return results
