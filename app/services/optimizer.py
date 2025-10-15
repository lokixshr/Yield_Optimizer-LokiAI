from __future__ import annotations

from typing import List

from app.models import Allocation, OptimizeRequest, OptimizeResponse, YieldPool


RISK_THRESHOLDS = {
    "conservative": 0.4,
    "balanced": 0.7,
    "aggressive": 0.95,
}


def _asset_matches(pool: YieldPool, assets: List[str]) -> bool:
    if not assets:
        return True
    # Simple match: pool name contains any asset symbol
    name = pool.pool.upper()
    return any(asset.upper() in name for asset in assets)


def optimize_allocation(req: OptimizeRequest, pools: List[YieldPool]) -> OptimizeResponse:
    max_risk = RISK_THRESHOLDS.get(req.risk_profile, 0.7)

    candidates = [p for p in pools if p.risk_score <= max_risk and _asset_matches(p, req.assets)]
    candidates.sort(key=lambda p: p.net_yield, reverse=True)

    if not candidates:
        return OptimizeResponse(total_allocation_usd=0, expected_net_yield=0, allocations=[])

    # Allocate proportionally to net_yield among top N
    top = candidates[: min(5, len(candidates))]
    total_score = sum(max(p.net_yield, 0.0) for p in top) or 1.0

    allocations: List[Allocation] = []
    expected_net_yield = 0.0

    for p in top:
        weight = max(p.net_yield, 0.0) / total_score
        amount = req.allocation_usd * weight
        allocations.append(Allocation(pool_id=p.id, amount_usd=amount, expected_net_yield=p.net_yield))
        expected_net_yield += p.net_yield * weight

    return OptimizeResponse(
        total_allocation_usd=req.allocation_usd,
        expected_net_yield=expected_net_yield,
        allocations=allocations,
    )
