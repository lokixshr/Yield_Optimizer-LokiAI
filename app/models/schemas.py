from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

Protocol = Literal["sushiswap", "curve", "aave"]

class Pool(BaseModel):
    protocol: Protocol
    chain: str
    pool_id: str
    symbol: Optional[str] = None
    apy: float = Field(ge=0)
    tvl_usd: float = Field(ge=0)
    volume_24h_usd: Optional[float] = 0.0
    gas_cost_usd: Optional[float] = 0.0
    volatility: Optional[float] = 0.0
    protocol_score: Optional[float] = 0.8
    net_yield: Optional[float] = None
    predicted_apy: Optional[float] = None

class YieldSnapshot(BaseModel):
    pool: Pool
    timestamp: datetime

class TopPoolsResponse(BaseModel):
    pools: List[Pool]
    as_of: datetime
