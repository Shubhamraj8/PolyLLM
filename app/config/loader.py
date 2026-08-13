import asyncio
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    timeout_seconds: float
    models: list[str]
    default_model: str
    base_url: str


class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    window_seconds: int = 60
    cooldown_seconds: int = 30


class RateLimitBucketConfig(BaseModel):
    requests: int
    window_seconds: int


class RateLimitConfig(BaseModel):
    per_api_key: RateLimitBucketConfig
    per_ip: RateLimitBucketConfig


class RetryConfig(BaseModel):
    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 5.0
    multiplier: float = 2.0
    jitter: bool = True


class AuditConfig(BaseModel):
    enabled: bool = True
    max_entries: int = 10000
    ttl_days: int = 7


class RoutingConfig(BaseModel):
    default_chain: str = "default"
    chains: dict[str, list[str]]


class GatewayConfig(BaseModel):
    version: str
    routing: RoutingConfig
    providers: dict[str, ProviderConfig]
    circuit_breaker: CircuitBreakerConfig
    rate_limit: RateLimitConfig
    retry: RetryConfig
    audit: AuditConfig
    cost_tracking: dict


class ConfigLoader:
    def __init__(self, config_path: str):
        self._path = Path(config_path)
        self._lock = asyncio.Lock()
        self.config: GatewayConfig | None = None

    async def load(self):
        async with self._lock:
            raw = yaml.safe_load(self._path.read_text())
            self.config = GatewayConfig(**raw)
            logger.info("config_loaded", path=str(self._path))

    async def reload(self):
        """Hot-reload config from disk. Called by POST /admin/reload."""
        await self.load()
        logger.info("config_reloaded")

    def get_chain(self, chain_name: str | None = None) -> list[str]:
        name = chain_name or self.config.routing.default_chain
        return self.config.routing.chains[name]
