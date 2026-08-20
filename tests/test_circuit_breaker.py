import time
from unittest.mock import patch

import pytest
from app.config.loader import CircuitBreakerConfig
from app.resilience.circuit_breaker import CBState, CircuitBreaker


@pytest.fixture
def cb_config():
    return CircuitBreakerConfig(
        failure_threshold=3,
        window_seconds=60,
        cooldown_seconds=30,
    )


@pytest.fixture
def cb(fake_redis, cb_config):
    return CircuitBreaker(provider="test_provider", config=cb_config, redis=fake_redis)


@pytest.mark.asyncio
async def test_closed_by_default(cb):
    state = await cb.get_state()
    assert state == CBState.CLOSED
    assert not await cb.is_open()


@pytest.mark.asyncio
async def test_closed_stays_closed_below_threshold(cb):
    await cb.record_failure()
    await cb.record_failure()
    state = await cb.get_state()
    assert state == CBState.CLOSED
    assert not await cb.is_open()


@pytest.mark.asyncio
async def test_closed_to_open_after_threshold_failures(cb):
    await cb.record_failure()
    await cb.record_failure()
    await cb.record_failure()
    state = await cb.get_state()
    assert state == CBState.OPEN
    assert await cb.is_open()


@pytest.mark.asyncio
async def test_open_to_half_open_after_cooldown(cb):
    now = 1000.0
    with patch("time.time", return_value=now):
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_failure()
        assert await cb.get_state() == CBState.OPEN

    # Advance time beyond cooldown (30s)
    with patch("time.time", return_value=now + 35.0):
        state = await cb.get_state()
        assert state == CBState.HALF_OPEN
        assert not await cb.is_open()  # is_open() returns False for HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_plus_success_becomes_closed(cb):
    now = 1000.0
    with patch("time.time", return_value=now):
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_failure()

    # Move to HALF_OPEN
    with patch("time.time", return_value=now + 35.0):
        await cb.get_state()  # triggers transition to HALF_OPEN
        await cb.record_success()
        assert await cb.get_state() == CBState.CLOSED


@pytest.mark.asyncio
async def test_half_open_plus_failure_reopens(cb):
    now = 1000.0
    with patch("time.time", return_value=now):
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_failure()

    # Move to HALF_OPEN then fail
    with patch("time.time", return_value=now + 35.0):
        await cb.get_state()  # HALF_OPEN
        await cb.record_failure()
        assert await cb.get_state() == CBState.OPEN


@pytest.mark.asyncio
async def test_failures_outside_window_do_not_accumulate(cb, fake_redis):
    await cb.record_failure()
    await cb.record_failure()
    
    # Manually delete key to simulate window TTL expiry
    await fake_redis.delete(cb._key_failures)

    await cb.record_failure()
    assert await cb.get_state() == CBState.CLOSED
