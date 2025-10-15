from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.clients.graphql import graphql_query
from app.http import HttpClient

logger = logging.getLogger(__name__)

AAVE_V2_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/aave/protocol-v2"


def _aave_gateway_url() -> str | None:
    # If AAVE_V2_SUBGRAPH_ID is provided, use gateway; else None
    from app.config import get_settings
    s = get_settings()
    sid = getattr(s, "AAVE_V2_SUBGRAPH_ID", None)
    if s.THEGRAPH_API_KEY and sid:
        return f"https://gateway.thegraph.com/api/{s.THEGRAPH_API_KEY}/subgraphs/id/{sid}"
    return None


async def fetch_aave_reserves(http: HttpClient) -> List[Dict[str, Any]]:
    query = """
    {
      reserves(first: 50) {
        id
        symbol
        name
        underlyingAsset
        liquidityRate
        totalLiquidityUSD
      }
    }
    """
    out: List[Dict[str, Any]] = []
    # Try The Graph gateway if configured
    gw = _aave_gateway_url()
    if gw:
        try:
            data = await graphql_query(http, gw, query)
            reserves = data.get("reserves", [])
            for r in reserves:
                lr = float(r.get("liquidityRate") or 0.0)
                apy = (lr / 1e27) * 100.0 if lr > 0 else 0.0
                tvl = float(r.get("totalLiquidityUSD") or 0.0)
                out.append(
                    {
                        "id": f"aave:ethereum:{r['id']}",
                        "protocol": "Aave",
                        "pool": r.get("symbol") or r.get("name") or "Aave Market",
                        "chain": "ethereum",
                        "apy": apy,
                        "tvl_usd": tvl,
                        "metadata": {
                            "underlyingAsset": r.get("underlyingAsset"),
                        },
                    }
                )
            return out
        except Exception as e:
            logger.warning(f"Aave fetch via gateway failed: {e}")

    # Fallback to legacy endpoint (may redirect/fail)
    try:
        data = await graphql_query(http, AAVE_V2_SUBGRAPH, query)
        reserves = data.get("reserves", [])
        for r in reserves:
            lr = float(r.get("liquidityRate") or 0.0)
            apy = (lr / 1e27) * 100.0 if lr > 0 else 0.0
            tvl = float(r.get("totalLiquidityUSD") or 0.0)
            out.append(
                {
                    "id": f"aave:ethereum:{r['id']}",
                    "protocol": "Aave",
                    "pool": r.get("symbol") or r.get("name") or "Aave Market",
                    "chain": "ethereum",
                    "apy": apy,
                    "tvl_usd": tvl,
                    "metadata": {
                        "underlyingAsset": r.get("underlyingAsset"),
                    },
                }
            )
    except Exception as e:
        logger.warning(f"Aave subgraph fetch failed: {e}")
    return out
