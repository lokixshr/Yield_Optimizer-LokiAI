# LokiAI DeFi Yield Optimizer (FastAPI)

Production-ready microservice that fetches real yields and liquidity data across DeFi protocols, ranks opportunities, applies risk scoring and gas adjustments, and exposes JSON APIs.

## Features
- FastAPI async backend
- Real integrations: SushiSwap Subgraph, Curve API, Aave Subgraph, Coingecko, Alchemy, Etherscan
- Redis caching and 30-day rolling history
- Background refresh task
- Risk scoring and gas-adjusted net yields
- JSON endpoints for top pools, optimization, history, status, and execution simulation

## Quickstart (Windows / PowerShell)
1. Create env file:
   Copy `.env.example` to `.env` and fill in your keys (Alchemy, Etherscan, Redis URL).

2. Create venv and install deps:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Run Redis locally (if you don't have one, use Docker Desktop or a managed instance). Example (Docker):
   ```powershell
   docker run -p 6379:6379 --name redis redis:7
   ```

4. Start the API:
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Test endpoints:
   - GET http://localhost:8000/api/yield/top
   - POST http://localhost:8000/api/yield/optimize
   - GET http://localhost:8000/api/yield/history
   - GET http://localhost:8000/api/yield/status
   - POST http://localhost:8000/api/yield/execute

## Notes
- By default, the background refresh runs every 10 minutes. Adjust `REFRESH_INTERVAL_SECONDS` in `.env`.
- For gas adjustment, the service uses Alchemy for eth_gasPrice and Coingecko for ETH price.
- SushiSwap APY is estimated via daily volume and LP fee share: APY ≈ (vol24h * 0.25% / TVL) * 365.
- Aave deposit APY uses liquidityRate from subgraph (converted from RAY to %).
- Curve APY is taken from Curve API if available.

## Data format (normalized)
Each pool:
```
{
  "protocol": "SushiSwap|Curve|Aave",
  "pool": "symbol pair or asset name",
  "chain": "ethereum|polygon|...",
  "apy": 12.34,
  "tvl_usd": 12345678.9,
  "risk_score": 0.37,
  "net_yield": 11.8,
  "metadata": { ... optional extra data ... }
}
```
