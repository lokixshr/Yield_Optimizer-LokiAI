from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from app.config import get_settings
from app.http import HttpClient
from app.models import YieldPool
from app.clients.coingecko import get_eth_price_usd
from app.clients.alchemy import get_gas_price_gwei
from app.clients.etherscan import get_gas_oracle_gwei
from app.clients.sushiswap import fetch_top_pools_24h
from app.clients.curve import fetch_curve_pools
from app.clients.aave import fetch_aave_reserves
from app.clients.defillama import fetch_llama_pools
from app.services.risk import score_pool, compute_volatility_percent, protocol_score
from app.services.storage import store_yield_snapshots
from app.services.ml import forecast_7d

logger = logging.getLogger(__name__)


GAS_UNITS = {
    "Aave": 160_000,
    "Curve": 250_000,
    "SushiSwap": 220_000,
}


class Aggregator:
    def __init__(self, http: HttpClient):
        self.http = http
        self._last_refresh_at: int | None = None
        self._last_pools: List[YieldPool] = []

    @property
    def last_refresh_at(self) -> int | None:
        return self._last_refresh_at

    async def _get_public_gas_gwei(self) -> float:
        """Fallback to public Cloudflare Ethereum RPC for gas price if Alchemy/Etherscan unavailable."""
        try:
            resp = await self.http.post(
                "https://cloudflare-eth.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "eth_gasPrice", "params": []},
            )
            wei_hex = resp.json().get("result", "0x0")
            wei = int(wei_hex, 16)
            return float(wei / 1e9)
        except Exception:
            return 0.0

    async def _get_gas_gwei(self) -> float:
        gwei = await get_gas_price_gwei(self.http)
        if gwei <= 0:
            oracle = await get_gas_oracle_gwei(self.http)
            gwei = float(oracle.get("ProposeGasPrice", 0.0)) if oracle else 0.0
        if gwei <= 0:
            gwei = await self._get_public_gas_gwei()
        return gwei

    async def _gas_cost_usd(self, protocol: str) -> float:
        gwei = await self._get_gas_gwei()
        eth_price = await get_eth_price_usd(self.http)
        units = GAS_UNITS.get(protocol, 200_000)
        # cost (ETH) = gas_units * gas_price(gwei) * 1e-9
        cost_eth = units * gwei * 1e-9
        return float(cost_eth * eth_price)

    async def _fetch_raw(self) -> List[Dict[str, Any]]:
        sush = await fetch_top_pools_24h(self.http)
        curve = await fetch_curve_pools(self.http)
        aave = await fetch_aave_reserves(self.http)
        # Restrict Llama to core protocols to reduce volume
        llama = await fetch_llama_pools(self.http, protocols=["aave", "curve", "sushiswap"])
        # If Sushi/Aave empty due to subgraph issues, Llama will supply data
        # Deduplicate by id to avoid double counting
        seen: set[str] = set()
        out: List[Dict[str, Any]] = []
        for src in (sush + curve + aave + llama):
            pid = str(src.get("id"))
            if pid in seen:
                continue
            seen.add(pid)
            out.append(src)
        return out

    async def refresh(self, allocation_usd: float | None = None) -> List[YieldPool]:
        settings = get_settings()
        raw = await self._fetch_raw()
        pools: List[YieldPool] = []
        # Pre-fetch gas costs per protocol once using shared ETH price and gas gwei
        gas_costs: Dict[str, float] = {}
        try:
            gwei = await self._get_gas_gwei()
            eth_price = await get_eth_price_usd(self.http)
        except Exception:
            gwei, eth_price = 0.0, 0.0
        for protocol_name in {r["protocol"] for r in raw}:
            units = GAS_UNITS.get(protocol_name, 200_000)
            cost_eth = units * gwei * 1e-9
            gas_costs[protocol_name] = float(cost_eth * eth_price)

        # Build pool objects
        for r in raw:
            try:
                protocol = r["protocol"]
                apy = float(r.get("apy") or 0.0)
                tvl = float(r.get("tvl_usd") or 0.0)
                pool = YieldPool(
                    id=str(r["id"]),
                    protocol=protocol,
                    pool=str(r.get("pool") or r.get("name") or "Pool"),
                    chain=str(r.get("chain") or "ethereum").lower(),
                    apy=apy,
                    tvl_usd=tvl,
                    risk_score=0.0,  # provisional
                    net_yield=0.0,   # provisional
                    metadata=r.get("metadata") or {},
                )
                # Risk scoring first (0..1 for other features)
                pool.risk_score = score_pool(pool)
                # Compute volatility (in %) from Mongo history and protocol_score
                vol = await compute_volatility_percent(pool)
                pscore = protocol_score(protocol)
                # risk_penalty = volatility * (1 - protocol_score)
                risk_penalty = vol * (1.0 - pscore)
                # gas component in % = (gas_cost_usd / tvl_usd) * 100
                gas_usd = gas_costs.get(protocol, 0.0)
                gas_percent = (gas_usd / tvl) * 100.0 if tvl > 0 else 0.0
                # net_yield = apy - (gas_cost / tvl) - (risk_penalty)
                net = apy - gas_percent - risk_penalty
                pool.net_yield = float(max(0.0, net))
                pools.append(pool)
            except Exception as e:
                logger.debug(f"Skipping malformed pool: {e}")
                continue

        # Optional ML forecast: use recent APY series from Mongo if desired (left as None if not available)
        try:
            if get_settings().ENABLE_ML:
                await forecast_7d(pools, history=None)
        except Exception:
            pass

        # Sort by net_yield desc as default internal ordering
        pools.sort(key=lambda p: p.net_yield, reverse=True)
        self._last_pools = pools
        self._last_refresh_at = int(time.time())

        # Persist snapshots to MongoDB
        try:
            await store_yield_snapshots(pools)
        except Exception as e:
            logger.debug(f"Failed to store snapshots: {e}")

        return pools

    def current(self) -> List[YieldPool]:
        return list(self._last_pools)
