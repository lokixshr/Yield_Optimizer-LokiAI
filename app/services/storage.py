from __future__ import annotations
from datetime import datetime
from typing import List

from app.db import yields_collection
from app.models import YieldPool


async def store_yield_snapshots(pools: List[YieldPool]) -> None:
    """Persist snapshots into isolated collection yield_optimizer_yields (async)."""
    col = yields_collection()
    if not pools:
        return

    ts = datetime.utcnow()
    docs = []
    for p in pools:
        docs.append(
            {
                "pool_id": p.id,
                "protocol": p.protocol,
                "chain": p.chain,
                "pool": p.pool,
                "apy": p.apy,
                "tvl_usd": p.tvl_usd,
                "risk_score": p.risk_score,
                "net_yield": p.net_yield,
                "predicted_apy": p.predicted_apy,
                "timestamp": ts,
            }
        )
    try:
        await col.insert_many(docs, ordered=False)
    except Exception:
        # Best-effort; ignore bulk insertion race conditions
        pass
