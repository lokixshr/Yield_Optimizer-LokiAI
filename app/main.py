from __future__ import annotations

import logging
import asyncio
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.config import get_settings
from app.utils.logging import setup_logging
from app.models import (
    ExecuteRequest,
    ExecuteResponse,
    OptimizeRequest,
    OptimizeResponse,
    ServiceStatus,
    YieldPool,
)
from app.services.cache import Cache
from app.services.optimizer import optimize_allocation
from app.background import BackgroundRefresher
from app.db import connect as db_connect, close as db_close
from app.http import HttpClient
from app.services.aggregator import Aggregator

app = FastAPI(title="LokiAI DeFi Yield Optimizer", version="1.0.0")

logger = logging.getLogger(__name__)

# Helper to retrieve aggregator whether background/redis is enabled or not
def _get_aggregator():
    ref = getattr(app.state, "refresher", None)
    if ref is not None:
        return ref.aggregator
    return getattr(app.state, "aggregator", None)

# Middleware: wallet requirement and rate limiting, plus Loki logging
from app.middleware.security import require_wallet
from app.middleware.rate_limit import rate_limiter
from app.utils.loki import loki_log

SETTINGS = get_settings()

@app.middleware("http")
async def _security(request, call_next):
    return await require_wallet(request, call_next)

if SETTINGS.ENABLE_REDIS:
    @app.middleware("http")
    async def _rate_limit(request, call_next):
        return await rate_limiter(request, call_next)
else:
    @app.middleware("http")
    async def _rate_limit(request, call_next):
        # No-op rate limiter when Redis is disabled
        return await call_next(request)

@app.middleware("http")
async def _loki_logger(request, call_next):
    response = await call_next(request)
    try:
        await loki_log(
            "INFO",
            "request",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "status": response.status_code,
                "wallet": request.headers.get("x-wallet-address"),
                "client_ip": request.client.host if request.client else None,
            },
        )
    except Exception:
        pass
    return response


@app.on_event("startup")
async def startup_event() -> None:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    # MongoDB (isolated collections)
    await db_connect()

    # Optional Redis/background refresher
    if settings.ENABLE_REDIS:
        app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
        app.state.cache = Cache(app.state.redis)
        app.state.refresher = BackgroundRefresher(app.state.redis)
        await app.state.refresher.start()
    else:
        # Fallback: direct aggregator + http client without cache/background tasks
        app.state.redis = None
        app.state.cache = None
        app.state.refresher = None
        app.state.http = HttpClient()
        app.state.aggregator = Aggregator(app.state.http)
        # Kick off a non-blocking warm-up so startup doesn't hang on external APIs
        async def _warmup():
            try:
                pools = await app.state.aggregator.refresh()
                logger.info(f"✅ Yield Optimizer ready – pools: {len(pools)}")
            except Exception as e:
                logger.warning(f"Initial warm-up failed: {e}")
        asyncio.create_task(_warmup())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if getattr(app.state, "refresher", None):
        await app.state.refresher.stop()
    if getattr(app.state, "redis", None):
        try:
            await app.state.redis.aclose()
        except Exception:
            pass
    # Close standalone HTTP client if using no-redis mode
    if getattr(app.state, "http", None):
        try:
            await app.state.http.aclose()
        except Exception:
            pass
    # MongoDB close
    await db_close()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/yield/top", response_model=List[YieldPool])
async def get_top_yields(
    limit: int = Query(20, ge=1, le=100),
    chain: Optional[str] = None,
    protocol: Optional[str] = None,
    min_tvl: float = Query(0.0, ge=0.0),
    sort_by: str = Query("net_yield", pattern="^(apy|net_yield)$"),
    allocation_usd: Optional[float] = Query(None, ge=1.0),
):
    aggregator = _get_aggregator()
    cache = getattr(app.state, "cache", None)
    # If user overrides allocation USD for gas adjustment, perform a fresh computation
    if allocation_usd is not None:
        pools = await aggregator.refresh(allocation_usd=allocation_usd)
        if cache:
            await cache.save_latest_pools(pools)
    else:
        pools = []
        if cache:
            pools = await cache.get_latest_pools()
        if not pools:
            pools = await aggregator.refresh()
            if cache:
                await cache.save_latest_pools(pools)

    # Filters
    if chain:
        pools = [p for p in pools if p.chain.lower() == chain.lower()]
    if protocol:
        pools = [p for p in pools if p.protocol.lower() == protocol.lower()]
    if min_tvl > 0:
        pools = [p for p in pools if p.tvl_usd >= min_tvl]

    pools.sort(key=lambda p: getattr(p, sort_by), reverse=True)
    return pools[:limit]


@app.post("/api/yield/optimize", response_model=OptimizeResponse)
async def post_optimize(req: OptimizeRequest):
    aggregator = _get_aggregator()
    cache = getattr(app.state, "cache", None)
    pools = []
    if cache:
        pools = await cache.get_latest_pools()
    if not pools:
        pools = await aggregator.refresh(allocation_usd=req.allocation_usd)
        if cache:
            await cache.save_latest_pools(pools)
    res = optimize_allocation(req, pools)
    return res


@app.get("/api/yield/history")
async def get_history():
    # History is available only with Redis + background refresher
    if not getattr(app.state, "refresher", None):
        return JSONResponse(content=[])
    history = await app.state.refresher.history.get_30d()
    # Avoid returning huge payload; include only aggregate fields
    out = []
    for h in history:
        out.append(
            {
                "timestamp": h.timestamp,
                "count": len(h.pools),
                "avg_apy": (sum(p.apy for p in h.pools) / len(h.pools)) if h.pools else 0,
                "avg_net": (sum(p.net_yield for p in h.pools) / len(h.pools)) if h.pools else 0,
                "total_tvl": sum(p.tvl_usd for p in h.pools),
            }
        )
    return JSONResponse(content=out)


@app.get("/api/yield/status", response_model=ServiceStatus)
async def get_status(wallet: Optional[str] = None):
    settings = get_settings()
    aggregator = _get_aggregator()
    cache = getattr(app.state, "cache", None)
    pools = []
    if cache:
        pools = await cache.get_latest_pools()
    if not pools:
        pools = await aggregator.refresh()
        if cache:
            await cache.save_latest_pools(pools)

    chains = sorted({p.chain for p in pools})
    avg_apy = (sum(p.apy for p in pools) / len(pools)) if pools else 0.0
    avg_risk = (sum(p.risk_score for p in pools) / len(pools)) if pools else 0.0
    total_tvl = sum(p.tvl_usd for p in pools)

    wallet_info = None
    if wallet:
        # Lightweight wallet info: try Alchemy then public RPC
        try:
            rpc_url = settings.alchemy_rpc_url() or "https://cloudflare-eth.com"
            payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [wallet, "latest"]}
            http = getattr(app.state, "refresher", None).http if getattr(app.state, "refresher", None) else getattr(app.state, "http", None)
            resp = await http.post(rpc_url, json=payload)
            wei = int(resp.json().get("result", "0x0"), 16)
            wallet_info = {"address": wallet, "eth_balance": wei / 1e18}
        except Exception:
            wallet_info = {"address": wallet}

    return ServiceStatus(
        last_refresh_at=_get_aggregator().last_refresh_at,
        pools_tracked=len(pools),
        chains_tracked=chains,
        avg_apy=avg_apy,
        avg_risk_score=avg_risk,
        aggregated_tvl_usd=total_tvl,
        wallet=wallet_info,
    )


@app.post("/api/yield/execute", response_model=ExecuteResponse)
async def post_execute(req: ExecuteRequest):
    # Simulate only: sum gas costs based on protocol-level defaults and compute net yield
    aggregator = _get_aggregator()
    cache = getattr(app.state, "cache", None)
    pools = []
    if cache:
        pools = await cache.get_latest_pools()
    if not pools:
        pools = await aggregator.refresh()
    pool_map = {p.id: p for p in pools}

    total_gas_usd = 0.0
    expected_net_yield = 0.0
    details = []

    for alloc in req.target_allocations:
        p = pool_map.get(alloc.pool_id)
        if not p:
            continue
        # Approximate one-time gas cost already amortized in pool.net_yield; here show explicit cost
        protocol = p.protocol
        # Reuse background's gas computation indirectly by recomputing via refresher's aggregator
        gas_usd = await _get_aggregator()._gas_cost_usd(protocol)
        total_gas_usd += gas_usd
        expected_net_yield += p.net_yield * (alloc.amount_usd / max(1.0, sum(a.amount_usd for a in req.target_allocations)))
        details.append({"pool_id": p.id, "protocol": protocol, "gas_usd": gas_usd, "net_yield": p.net_yield})

    return ExecuteResponse(total_gas_usd=total_gas_usd, expected_net_yield=expected_net_yield, details={"legs": details})


@app.post("/api/yield/refresh")
async def post_refresh():
    aggregator = _get_aggregator()
    cache = getattr(app.state, "cache", None)
    pools = await aggregator.refresh()
    if cache:
        await cache.save_latest_pools(pools)
    return {"refreshed": len(pools), "last_refresh_at": aggregator.last_refresh_at}
