from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Runtime
    ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Datastores
    MONGO_URI: str | None = None  # legacy var name support
    MONGO_DB: str | None = None   # legacy var name support
    MONGODB_URI: str | None = None  # preferred var name
    MONGO_DB_NAME: str | None = None  # preferred var name
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    ENABLE_REDIS: bool = Field(default=False)

    # Observability
    LOKI_URL: str = Field(default="http://localhost:3100")

    # External APIs
    COINGECKO_BASE_URL: str = Field(default="https://api.coingecko.com/api/v3")

    # SushiSwap subgraphs (multi-chain)
    SUSHISWAP_ETH_SUBGRAPH: str = Field(default="https://api.thegraph.com/subgraphs/name/sushiswap/exchange")
    SUSHISWAP_POLYGON_SUBGRAPH: str = Field(default="https://api.thegraph.com/subgraphs/name/sushiswap/matic-exchange")

    # Curve API
    CURVE_API_BASE: str = Field(default="https://api.curve.fi/api")

    # Alchemy / Etherscan
    ALCHEMY_NETWORK: str = Field(default="eth-mainnet")
    ALCHEMY_API_KEY: str | None = None
    ETHERSCAN_API_KEY: str | None = None

    # ML toggle
    ENABLE_ML: bool = Field(default=True)

    # The Graph gateway
    THEGRAPH_API_KEY: str | None = None
    SUSHI_SUBGRAPH_ID: str | None = None
    AAVE_V2_SUBGRAPH_ID: str | None = None

    # Refresh / history
    REFRESH_INTERVAL_SECONDS: int = Field(default=600)
    DEFAULT_ALLOCATION_USD: float = Field(default=1000.0)
    HISTORY_MAX_ENTRIES: int = Field(default=5000)

    def alchemy_rpc_url(self) -> str | None:
        if not self.ALCHEMY_API_KEY:
            return None
        return f"https://{self.ALCHEMY_NETWORK}.g.alchemy.com/v2/{self.ALCHEMY_API_KEY}"

    def get_mongo_uri(self) -> str:
        return (self.MONGODB_URI or self.MONGO_URI or "mongodb://localhost:27017")

    def get_mongo_db_name(self) -> str:
        return (self.MONGO_DB_NAME or self.MONGO_DB or "yield_optimizer")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
