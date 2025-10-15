from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class YieldPool(BaseModel):
    id: str = Field(..., description="Unique identifier (protocol:chain:poolAddress or name)")
    protocol: str
    pool: str
    chain: str
    apy: float = Field(..., description="Nominal APY in %")
    tvl_usd: float
    risk_score: float = Field(..., ge=0.0, le=1.0)
    net_yield: float = Field(..., description="APY adjusted for gas costs and risk, in %")
    predicted_apy: float | None = Field(default=None, description="Optional 7-day forecasted APY in %")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizeRequest(BaseModel):
    assets: List[str] = Field(default_factory=list, description="Preferred asset symbols, e.g., ['USDC','DAI']")
    risk_profile: str = Field(default="balanced", description="conservative|balanced|aggressive")
    allocation_usd: float = Field(default=1000.0)
    chains: List[str] = Field(default_factory=list)


class Allocation(BaseModel):
    pool_id: str
    amount_usd: float
    expected_net_yield: float


class OptimizeResponse(BaseModel):
    total_allocation_usd: float
    expected_net_yield: float
    allocations: List[Allocation]


class ExecuteRequest(BaseModel):
    target_allocations: List[Allocation]
    simulate: bool = True


class ExecuteResponse(BaseModel):
    total_gas_usd: float
    expected_net_yield: float
    details: Dict[str, Any]


class HistoryEntry(BaseModel):
    timestamp: int
    pools: List[YieldPool]


class ServiceStatus(BaseModel):
    last_refresh_at: Optional[int]
    pools_tracked: int
    chains_tracked: List[str]
    avg_apy: float
    avg_risk_score: float
    aggregated_tvl_usd: float
    wallet: Optional[Dict[str, Any]] = None
