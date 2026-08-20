import httpx
import pytest
import respx

from app.config.loader import RateLimitBucketConfig, RateLimitConfig
from app.rate_limit.limiter import RateLimiter


@pytest.mark.asyncio
async def test_limiter_unit_happy_path(fake_redis):
    config = RateLimitConfig(
        per_api_key=RateLimitBucketConfig(requests=5, window_seconds=60),
        per_ip=RateLimitBucketConfig(requests=3, window_seconds=60),
    )
    limiter = RateLimiter(redis=fake_redis, config=config)

    # First 3 requests should succeed
    for _ in range(3):
        res = await limiter.check(api_key="key1", ip="ip1")
        assert res.allowed is True


@pytest.mark.asyncio
async def test_limiter_unit_ip_limit_exceeded(fake_redis):
    config = RateLimitConfig(
        per_api_key=RateLimitBucketConfig(requests=5, window_seconds=60),
        per_ip=RateLimitBucketConfig(requests=2, window_seconds=60),
    )
    limiter = RateLimiter(redis=fake_redis, config=config)

    # First 2 requests should be allowed
    res1 = await limiter.check(api_key="key1", ip="ip1")
    assert res1.allowed is True
    res2 = await limiter.check(api_key="key2", ip="ip1")  # Different key, same IP
    assert res2.allowed is True

    # Third request should fail on IP
    res3 = await limiter.check(api_key="key3", ip="ip1")
    assert res3.allowed is False
    assert res3.reason == "ip"
    assert res3.retry_after == 60


@pytest.mark.asyncio
async def test_limiter_unit_key_limit_exceeded(fake_redis):
    config = RateLimitConfig(
        per_api_key=RateLimitBucketConfig(requests=2, window_seconds=60),
        per_ip=RateLimitBucketConfig(requests=5, window_seconds=60),
    )
    limiter = RateLimiter(redis=fake_redis, config=config)

    # First 2 requests allowed
    res1 = await limiter.check(api_key="key1", ip="ip1")
    assert res1.allowed is True
    res2 = await limiter.check(api_key="key1", ip="ip2")  # Same key, different IP
    assert res2.allowed is True

    # Third request fails on key
    res3 = await limiter.check(api_key="key1", ip="ip3")
    assert res3.allowed is False
    assert res3.reason == "api_key"
    assert res3.retry_after == 60


@pytest.mark.asyncio
async def test_limiter_unit_reset_after_ttl(fake_redis):
    config = RateLimitConfig(
        per_api_key=RateLimitBucketConfig(requests=1, window_seconds=60),
        per_ip=RateLimitBucketConfig(requests=5, window_seconds=60),
    )
    limiter = RateLimiter(redis=fake_redis, config=config)

    res1 = await limiter.check(api_key="key1", ip="ip1")
    assert res1.allowed is True

    res2 = await limiter.check(api_key="key1", ip="ip1")
    assert res2.allowed is False

    # Simulate TTL expiration by deleting key from fake_redis
    await fake_redis.delete("rl:key:key1")

    res3 = await limiter.check(api_key="key1", ip="ip1")
    assert res3.allowed is True


@pytest.mark.asyncio
async def test_limiter_api_endpoint(async_client):
    from tests.conftest import GROQ_SUCCESS_RESPONSE

    # Mock Groq completion response
    with respx.mock as mock:
        mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )

        headers = {"X-API-Key": "dev-key"}
        payload = {"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}]}

        # Override rate limiter config inside app to low values for easy testing
        limiter = async_client.app.state.rate_limiter
        limiter.config = RateLimitConfig(
            per_api_key=RateLimitBucketConfig(requests=2, window_seconds=60),
            per_ip=RateLimitBucketConfig(requests=5, window_seconds=60),
        )

        # First request: 200
        r1 = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r1.status_code == 200

        # Second request: 200
        r2 = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r2.status_code == 200

        # Third request: 429
        r3 = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r3.status_code == 429
        data = r3.json()
        assert data["error"]["code"] == "rate_limit_exceeded"
        assert data["error"]["type"] == "rate_limit_error"
        assert data["error"]["retry_after"] == 60
