import pytest
from app.cost.tracker import CostTracker, calculate_cost


# -- Unit: pricing logic --------------------------------------------------------

def test_groq_cost_is_zero():
    cost = calculate_cost("groq", "mixtral-8x7b-32768", 100, 50)
    assert cost == 0.0


def test_groq_llama_cost_is_zero():
    cost = calculate_cost("groq", "llama-3.1-8b-instant", 200, 100)
    assert cost == 0.0


def test_gemini_flash_cost():
    cost = calculate_cost("gemini", "gemini-1.5-flash", 100, 50)
    expected = (100 * 0.075 / 1_000_000) + (50 * 0.30 / 1_000_000)
    assert abs(cost - expected) < 1e-12


def test_gemini_flash_8b_cost():
    cost = calculate_cost("gemini", "gemini-1.5-flash-8b", 100, 50)
    expected = (100 * 0.0375 / 1_000_000) + (50 * 0.15 / 1_000_000)
    assert abs(cost - expected) < 1e-12


def test_unknown_provider_defaults_to_zero():
    cost = calculate_cost("openai", "gpt-4", 500, 200)
    assert cost == 0.0


# -- Integration: Redis key writes ----------------------------------------------

@pytest.mark.asyncio
async def test_record_increments_cost_total(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    cost = await tracker.record("gemini", "gemini-1.5-flash", 100, 50)
    assert cost > 0.0

    total = float(await fake_redis.get("cost:total"))
    assert abs(total - cost) < 1e-10


@pytest.mark.asyncio
async def test_record_increments_provider_key(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    cost = await tracker.record("gemini", "gemini-1.5-flash", 100, 50)

    val = float(await fake_redis.get("cost:by_provider:gemini"))
    assert abs(val - cost) < 1e-10


@pytest.mark.asyncio
async def test_record_increments_model_key(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    cost = await tracker.record("gemini", "gemini-1.5-flash", 100, 50)

    val = float(await fake_redis.get("cost:by_model:gemini-1.5-flash"))
    assert abs(val - cost) < 1e-10


@pytest.mark.asyncio
async def test_record_increments_token_total(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    await tracker.record("groq", "mixtral-8x7b-32768", 100, 50)

    total_tokens = int(await fake_redis.get("cost:tokens:total"))
    assert total_tokens == 150


@pytest.mark.asyncio
async def test_record_daily_key_has_ttl(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    await tracker.record("groq", "mixtral-8x7b-32768", 100, 50)

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ttl = await fake_redis.ttl(f"cost:daily:{today}")
    # TTL should be set (30 days = 2592000s); fakeredis should return > 0
    assert ttl > 0


@pytest.mark.asyncio
async def test_record_accumulates_multiple_calls(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    c1 = await tracker.record("gemini", "gemini-1.5-flash", 100, 50)
    c2 = await tracker.record("gemini", "gemini-1.5-flash", 200, 100)

    total = float(await fake_redis.get("cost:total"))
    assert abs(total - (c1 + c2)) < 1e-10

    tokens = int(await fake_redis.get("cost:tokens:total"))
    assert tokens == 450  # (100+50) + (200+100)


@pytest.mark.asyncio
async def test_groq_zero_cost_still_writes_tokens(fake_redis):
    tracker = CostTracker(redis=fake_redis)
    cost = await tracker.record("groq", "mixtral-8x7b-32768", 80, 40)
    assert cost == 0.0

    tokens = int(await fake_redis.get("cost:tokens:total"))
    assert tokens == 120
