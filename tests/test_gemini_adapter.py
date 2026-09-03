import httpx
import pytest
import respx

from app.config.loader import RetryConfig
from app.models.errors import NonRetryableProviderError, RetryableProviderError
from app.models.request import ChatRequest, Message
from app.providers.gemini_adapter import GeminiAdapter
from tests.conftest import GEMINI_SUCCESS_RESPONSE


@pytest.fixture
def gemini_adapter():
    retry_config = RetryConfig(max_attempts=1)
    return GeminiAdapter(api_key="test-key", retry_config=retry_config)


def test_gemini_request_transformation(gemini_adapter):
    req = ChatRequest(
        model="gemini-1.5-flash",
        messages=[
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ],
    )
    payload = gemini_adapter._transform_request(req)

    assert "systemInstruction" in payload
    assert payload["systemInstruction"]["parts"][0]["text"] == "You are helpful."
    assert len(payload["contents"]) == 2
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][1]["role"] == "model"  # assistant mapped to model


@pytest.mark.asyncio
async def test_gemini_success_parsing(gemini_adapter):
    req = ChatRequest(
        model="gemini-1.5-flash",
        messages=[Message(role="user", content="Hello")],
    )

    with respx.mock:
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(200, json=GEMINI_SUCCESS_RESPONSE)
        )
        response = await gemini_adapter.complete(req)

        assert response.model == "gemini-1.5-flash"
        assert response.choices[0].message.content == "Hello!"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.x_gateway.provider_used == "gemini"


@pytest.mark.asyncio
async def test_gemini_429_raises_retryable(gemini_adapter):
    req = ChatRequest(model="gemini-1.5-flash", messages=[Message(role="user", content="hi")])
    with respx.mock:
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(429, text="Quota exceeded")
        )
        with pytest.raises(RetryableProviderError):
            await gemini_adapter.complete(req)


@pytest.mark.asyncio
async def test_gemini_400_raises_non_retryable(gemini_adapter):
    req = ChatRequest(model="gemini-1.5-flash", messages=[Message(role="user", content="hi")])
    with respx.mock:
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )
        with pytest.raises(NonRetryableProviderError):
            await gemini_adapter.complete(req)


@pytest.mark.asyncio
async def test_gemini_complete_stream(gemini_adapter):
    req = ChatRequest(model="gemini-1.5-flash", messages=[Message(role="user", content="hi")])
    gemini_sse = (
        'data: {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}\n\n'
        'data: {"candidates": [{"content": {"parts": [{"text": " World!"}]}, "finishReason": "STOP"}]}\n\n'
    )
    with respx.mock:
        respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                text=gemini_sse,
            )
        )
        stream_gen = await gemini_adapter.complete_stream(req)
        chunks = [chunk async for chunk in stream_gen]

        assert len(chunks) == 2
        assert "Hello" in chunks[0]
        assert "World!" in chunks[1]
