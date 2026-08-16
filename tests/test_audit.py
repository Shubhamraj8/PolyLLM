import json
import pytest
from app.audit.logger import AuditLogger, _mask_key
from app.config.loader import AuditConfig
from app.models.request import ChatRequest, Message
from app.models.response import ChatResponse, GatewayMeta, UsageInfo, Choice, MessageOutput


def _make_response(provider="groq", fallback=False, providers_tried=None):
    return ChatResponse(
        id="chatcmpl-test",
        created=1728000000,
        model="mixtral-8x7b-32768",
        choices=[Choice(index=0, message=MessageOutput(role="assistant", content="Hi"), finish_reason="stop")],
        usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        x_gateway=GatewayMeta(
            provider_used=provider,
            model_used="mixtral-8x7b-32768",
            latency_ms=100,
            request_id="req-test",
            fallback_triggered=fallback,
            providers_tried=providers_tried or [provider],
            estimated_cost_usd=0.0,
        ),
    )


def _make_body():
    return ChatRequest(model="mixtral-8x7b-32768", messages=[Message(role="user", content="hello")])


@pytest.mark.asyncio
async def test_log_success_redis_entry(fake_redis):
    config = AuditConfig(enabled=True, max_entries=10000, ttl_days=7)
    audit = AuditLogger(redis=fake_redis, config=config)

    await audit.log(
        request_id="req-1",
        ip="1.2.3.4",
        api_key="dev-key",
        body=_make_body(),
        response=_make_response(),
        latency_ms=200,
    )

    llen = await fake_redis.llen("audit:requests")
    assert llen == 1

    raw = await fake_redis.lindex("audit:requests", 0)
    entry = json.loads(raw)

    required_fields = [
        "request_id", "timestamp", "ip", "api_key_prefix", "model_requested",
        "provider_used", "model_used", "fallback_triggered", "providers_tried",
        "status", "http_status", "latency_ms", "prompt_tokens", "completion_tokens",
        "total_tokens", "estimated_cost_usd", "error",
    ]
    for field in required_fields:
        assert field in entry, f"Missing field: {field}"

    assert entry["status"] == "success"
    assert entry["http_status"] == 200


@pytest.mark.asyncio
async def test_api_key_masking(fake_redis):
    config = AuditConfig(enabled=True, max_entries=10000, ttl_days=7)
    audit = AuditLogger(redis=fake_redis, config=config)

    await audit.log(
        request_id="req-2",
        ip="1.2.3.4",
        api_key="dev-key-full",
        body=_make_body(),
        response=_make_response(),
        latency_ms=100,
    )

    raw = await fake_redis.lindex("audit:requests", 0)
    entry = json.loads(raw)
    assert entry["api_key_prefix"] == "dev-key-..."
    assert "dev-key-full" not in raw


@pytest.mark.asyncio
async def test_mask_key_function():
    assert _mask_key("dev-key") == "dev-key..."
    assert _mask_key("sk-abcdefghijklmn") == "sk-abcde..."
    assert _mask_key("short") == "short..."


@pytest.mark.asyncio
async def test_ltrim_keeps_max_entries(fake_redis):
    config = AuditConfig(enabled=True, max_entries=5, ttl_days=7)
    audit = AuditLogger(redis=fake_redis, config=config)

    for i in range(7):
        await audit.log(
            request_id=f"req-{i}",
            ip="1.2.3.4",
            api_key="dev-key",
            body=_make_body(),
            response=_make_response(),
            latency_ms=100,
        )

    llen = await fake_redis.llen("audit:requests")
    assert llen == 5


@pytest.mark.asyncio
async def test_log_error_creates_failed_entry(fake_redis):
    config = AuditConfig(enabled=True, max_entries=10000, ttl_days=7)
    audit = AuditLogger(redis=fake_redis, config=config)

    await audit.log_error(
        request_id="req-err",
        ip="1.2.3.4",
        api_key="dev-key",
        body=_make_body(),
        error_msg="All providers failed",
        latency_ms=500,
        providers_tried=["groq", "gemini"],
    )

    raw = await fake_redis.lindex("audit:requests", 0)
    entry = json.loads(raw)
    assert entry["status"] == "failed"
    assert entry["http_status"] == 503
    assert entry["error"] == "All providers failed"
    assert entry["providers_tried"] == ["groq", "gemini"]


@pytest.mark.asyncio
async def test_audit_disabled_skips_redis(fake_redis):
    config = AuditConfig(enabled=False, max_entries=10000, ttl_days=7)
    audit = AuditLogger(redis=fake_redis, config=config)

    await audit.log(
        request_id="req-skip",
        ip="1.2.3.4",
        api_key="dev-key",
        body=_make_body(),
        response=_make_response(),
        latency_ms=100,
    )

    llen = await fake_redis.llen("audit:requests")
    assert llen == 0
