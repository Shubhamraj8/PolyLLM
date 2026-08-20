from dataclasses import dataclass
from typing import Any

from app.config.loader import RateLimitConfig


@dataclass
class RateLimitResult:
    allowed: bool
    reason: str = ""
    retry_after: int = 0


class RateLimiter:
    def __init__(self, redis: Any, config: RateLimitConfig) -> None:
        self.redis = redis
        self.config = config

    async def check(self, api_key: str, ip: str) -> RateLimitResult:
        """
        Validates rate limits for the given API Key and IP address.
        Returns RateLimitResult indicating whether the request is allowed.
        """
        # 1. Check API Key Bucket
        key_limit = self.config.per_api_key.requests
        key_window = self.config.per_api_key.window_seconds
        key_redis_key = f"rl:key:{api_key}"

        if not await self._check_bucket(key_redis_key, key_limit, key_window):
            return RateLimitResult(
                allowed=False,
                reason="api_key",
                retry_after=key_window,
            )

        # 2. Check IP Bucket
        ip_limit = self.config.per_ip.requests
        ip_window = self.config.per_ip.window_seconds
        ip_redis_key = f"rl:ip:{ip}"

        if not await self._check_bucket(ip_redis_key, ip_limit, ip_window):
            return RateLimitResult(
                allowed=False,
                reason="ip",
                retry_after=ip_window,
            )

        return RateLimitResult(allowed=True)

    async def _check_bucket(self, key: str, limit: int, window: int) -> bool:
        """
        Implements a simple token bucket/counter rate limiter in Redis.
        """
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, window)
        return count <= limit
