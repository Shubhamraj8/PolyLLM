import pytest
import pytest_asyncio
import fakeredis.aioredis
import respx
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import create_app

GROQ_SUCCESS_RESPONSE = {
    "id": "chatcmpl-test123",
    "object": "chat.completion",
    "created": 1728000000,
    "model": "mixtral-8x7b-32768",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}

GEMINI_SUCCESS_RESPONSE = {
    "candidates": [{"content": {"parts": [{"text": "Hello!"}], "role": "model"}, "finishReason": "STOP"}],
    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
}


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


from unittest.mock import patch


@pytest_asyncio.fixture
async def async_client(fake_redis):
    app = create_app()
    with patch("redis.asyncio.from_url", return_value=fake_redis):
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
                client.app = app
                yield client


@pytest.fixture
def mock_groq_success():
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )
        yield


@pytest.fixture
def mock_groq_500():
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        yield


@pytest.fixture
def mock_gemini_success():
    with respx.mock:
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(200, json=GEMINI_SUCCESS_RESPONSE)
        )
        yield


@pytest.fixture
def mock_both_fail():
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(500)
        )
        yield
