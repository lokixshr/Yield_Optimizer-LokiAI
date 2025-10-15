from __future__ import annotations

from typing import List

from app.models import YieldPool
from app.db import yields_collection

PROTOCOL_BASE_RISK = {
    "Aave": 0.2,
    "Curve": 0.3,
    "SushiSwap": 0.5,
}

# Protocol trust score in [0,1] for risk_penalty calculation
PROTOCOL_SCORE = {
    "Aave": 0.95,
    "Curve": 0.90,
    "SushiSwap": 0.80,
}


def score_pool(pool: YieldPool) -> float:
    base = PROTOCOL_BASE_RISK.get(pool.protocol, 0.6)
    tvl = max(pool.tvl_usd, 1.0)

    # TVL factor: higher TVL reduces risk
    if tvl >= 1_000_000_000:
        tvl_factor = -0.15
    elif tvl >= 100_000_000:
        tvl_factor = -0.1
    elif tvl >= 10_000_000:
        tvl_factor = -0.05
    elif tvl >= 1_000_000:
        tvl_factor = -0.02
    else:
        tvl_factor = 0.05

    # APY factor: very high APY increases risk (possible incentive/impermanent loss)
    apy = pool.apy
    if apy >= 100:
        apy_factor = 0.2
    elif apy >= 50:
        apy_factor = 0.1
    elif apy >= 20:
        apy_factor = 0.05
    else:
        apy_factor = 0.0

    score = max(0.0, min(1.0, base + tvl_factor + apy_factor))
    return score


async def compute_volatility_percent(pool: YieldPool, lookback: int = 30) -> float:
    """Compute std-dev of APY (in %) over recent snapshots from isolated Mongo collection."""
    col = yields_collection()
    cursor = col.find({"pool_id": pool.id}, {"apy": 1, "_id": 0}).sort("timestamp", -1).limit(lookback)
    apys: List[float] = [float(d.get("apy", 0.0)) async for d in cursor]
    if len(apys) < 2:
        return 0.0
    m = sum(apys) / len(apys)
    var = sum((a - m) ** 2 for a in apys) / (len(apys) - 1)
    return float(var ** 0.5)


def protocol_score(protocol: str) -> float:
    return PROTOCOL_SCORE.get(protocol, 0.8)
