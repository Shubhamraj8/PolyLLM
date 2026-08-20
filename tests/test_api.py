import httpx
import pytest
import respx

from app.config.loader import RateLimitBucketConfig, RateLimitConfig
from tests.conftest import GEMINI_SUCCESS_RESPONSE, GROQ_SUCCESS_RESPONSE


@pytest.mark.asyncio
async def test_api_chat_completions_happy_path(async_client):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )

        headers = {"X-API-Key": "dev-key"}
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        r = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r.status_code == 200
        data = r.json()

        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert "choices" in data
        assert "usage" in data
        assert "x_gateway" in data
        assert data["x_gateway"]["provider_used"] == "groq"
        assert data["x_gateway"]["fallback_triggered"] is False
        assert "X-Request-ID" in r.headers


@pytest.mark.asyncio
async def test_api_chat_completions_fallback_path(async_client):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(200, json=GEMINI_SUCCESS_RESPONSE)
        )

        headers = {"X-API-Key": "dev-key"}
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        r = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r.status_code == 200
        data = r.json()

        assert data["x_gateway"]["provider_used"] == "gemini"
        assert data["x_gateway"]["fallback_triggered"] is True
        assert data["x_gateway"]["providers_tried"] == ["groq", "gemini"]


@pytest.mark.asyncio
async def test_api_chat_completions_all_fail_returns_503(async_client):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(500)
        )

        headers = {"X-API-Key": "dev-key"}
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        r = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r.status_code == 503
        data = r.json()
        assert data["error"]["code"] == "all_providers_failed"
        assert "groq" in data["error"]["providers_tried"]
        assert "gemini" in data["error"]["providers_tried"]


@pytest.mark.asyncio
async def test_api_chat_completions_rate_limit_exceeded(async_client):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )

        limiter = async_client.app.state.rate_limiter
        limiter.config = RateLimitConfig(
            per_api_key=RateLimitBucketConfig(requests=1, window_seconds=60),
            per_ip=RateLimitBucketConfig(requests=10, window_seconds=60),
        )

        headers = {"X-API-Key": "dev-key"}
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        r1 = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r1.status_code == 200

        r2 = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
        assert r2.status_code == 429
        data = r2.json()
        assert data["error"]["code"] == "rate_limit_exceeded"
        assert "retry_after" in data["error"]


@pytest.mark.asyncio
async def test_api_chat_completions_no_api_key_returns_401(async_client):
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    r = await async_client.post("/v1/chat/completions", json=payload)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_api_chat_completions_invalid_body_returns_400(async_client):
    headers = {"X-API-Key": "dev-key"}
    payload = {
        "model": "gpt-4",
        "messages": [],  # empty messages violates min_length=1 constraint
    }
    r = await async_client.post("/v1/chat/completions", headers=headers, json=payload)
    assert r.status_code == 422 or r.status_code == 400


@pytest.mark.asyncio
async def test_api_health_endpoint(async_client):
    r = await async_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "redis" in data
    assert "providers" in data
    assert "config" in data


@pytest.mark.asyncio
async def test_api_admin_reload_requires_auth(async_client):
    # Unauthenticated should return 401
    r_unauth = await async_client.post("/admin/reload")
    assert r_unauth.status_code == 401

    # Authenticated should return 200
    headers = {"X-API-Key": "dev-key"}
    r_auth = await async_client.post("/admin/reload", headers=headers)
    assert r_auth.status_code == 200
    data = r_auth.json()
    assert data["status"] == "reloaded"


@pytest.mark.asyncio
async def test_api_models_endpoint(async_client):
    r = await async_client.get("/v1/models")
    assert r.status_code == 200
    data = r.json()
    assert data["object"] == "list"
    assert len(data["data"]) >= 4


@pytest.mark.asyncio
async def test_api_payload_too_large_returns_413(async_client):
    headers = {
        "X-API-Key": "dev-key",
        "Content-Length": str(15 * 1024 * 1024),  # 15 MB header
    }
    r = await async_client.post(
        "/v1/chat/completions", headers=headers, json={"model": "gpt-4", "messages": []}
    )
    assert r.status_code == 413
