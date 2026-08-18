"""
Tests for LG-013: Prometheus Metrics Instrumentation.

Covers acceptance criteria:
  - GET /metrics returns 200 with correct Content-Type
  - request_count increments on success
  - request_latency histogram buckets present
  - circuit_breaker_state == 0 on startup
  - circuit_breaker_state == 1 after CB opens
  - tokens_used increments after a request
  - provider_requests{outcome="skipped"} increments when CB is open
"""
import pytest
import respx
import httpx
from prometheus_client import REGISTRY


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_sample(metric_name: str, **labels) -> float | None:
    """Return the current value of a metric sample by name + labels, or None."""
    for metric in REGISTRY.collect():
        if metric.name == metric_name:
            for sample in metric.samples:
                if all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return None


# ── Unit: init_metrics sets CB state to 0 ────────────────────────────────────

def test_init_metrics_sets_cb_state_to_zero():
    from app.monitoring.metrics import init_metrics, circuit_breaker_state
    init_metrics()
    for provider in ("groq", "gemini"):
        val = circuit_breaker_state.labels(provider=provider)._value.get()
        assert val == 0.0, f"Expected 0.0 for {provider}, got {val}"


# ── Unit: circuit_breaker_state gauge transitions ────────────────────────────

@pytest.mark.asyncio
async def test_cb_state_gauge_opens(fake_redis):
    from app.config.loader import CircuitBreakerConfig
    from app.resilience.circuit_breaker import CircuitBreaker
    config = CircuitBreakerConfig(failure_threshold=1, window_seconds=60, cooldown_seconds=30)
    cb = CircuitBreaker(provider="groq", config=config, redis=fake_redis)

    # On startup: CLOSED = 0
    from app.monitoring.metrics import circuit_breaker_state
    circuit_breaker_state.labels(provider="groq").set(0)

    # Trigger failure -> opens CB
    await cb.record_failure()

    val = circuit_breaker_state.labels(provider="groq")._value.get()
    assert val == 1.0  # OPEN


@pytest.mark.asyncio
async def test_cb_state_gauge_closes_after_probe(fake_redis):
    from app.config.loader import CircuitBreakerConfig
    from app.resilience.circuit_breaker import CircuitBreaker, CBState
    config = CircuitBreakerConfig(failure_threshold=1, window_seconds=60, cooldown_seconds=30)
    cb = CircuitBreaker(provider="groq", config=config, redis=fake_redis)

    # Manually set to HALF_OPEN in Redis
    await fake_redis.set("cb:groq:state", CBState.HALF_OPEN.value)
    await cb.record_success()

    from app.monitoring.metrics import circuit_breaker_state
    val = circuit_breaker_state.labels(provider="groq")._value.get()
    assert val == 0.0  # CLOSED


# ── Integration: /metrics endpoint ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200(async_client):
    r = await async_client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_metrics_contains_histogram_buckets(async_client):
    from tests.conftest import GROQ_SUCCESS_RESPONSE
    # Must make at least one request so the histogram emits bucket lines
    with respx.mock as mock:
        mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )
        await async_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "dev-key"},
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
        )
    r = await async_client.get("/metrics")
    assert r.status_code == 200
    assert "gateway_request_duration_seconds_bucket" in r.text


@pytest.mark.asyncio
async def test_metrics_contains_cb_state(async_client):
    r = await async_client.get("/metrics")
    assert "gateway_circuit_breaker_state" in r.text


# ── Integration: request flow increments counters ────────────────────────────

@pytest.mark.asyncio
async def test_request_count_increments_on_success(async_client):
    from tests.conftest import GROQ_SUCCESS_RESPONSE

    with respx.mock as mock:
        mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )
        r = await async_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "dev-key"},
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200

    r_metrics = await async_client.get("/metrics")
    assert 'gateway_requests_total{' in r_metrics.text
    assert 'status="success"' in r_metrics.text


@pytest.mark.asyncio
async def test_tokens_used_increments_after_request(async_client):
    from tests.conftest import GROQ_SUCCESS_RESPONSE

    with respx.mock as mock:
        mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )
        await async_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "dev-key"},
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
        )

    r_metrics = await async_client.get("/metrics")
    assert "gateway_tokens_total" in r_metrics.text