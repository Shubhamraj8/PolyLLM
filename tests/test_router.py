import json

import httpx
import pytest
import respx

from app.models.errors import AllProvidersFailedError
from app.models.request import ChatRequest, Message
from app.resilience.circuit_breaker import CBState


@pytest.mark.asyncio
async def test_model_mapping(async_client):
    from tests.conftest import GROQ_SUCCESS_RESPONSE

    router = async_client.app.state.router

    with respx.mock as mock:
        route_mock = mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )

        req = ChatRequest(model="gpt-4", messages=[Message(role="user", content="hello")])
        res = await router.route(req, request_id="test-id")
        assert res.x_gateway.provider_used == "groq"

        # Verify model mapping sent the correct model to Groq (gpt-4 -> mixtral-8x7b-32768)
        assert route_mock.called
        sent_payload = json.loads(route_mock.calls.last.request.content)
        assert sent_payload["model"] == "mixtral-8x7b-32768"


@pytest.mark.asyncio
async def test_fallback_triggered(async_client):
    from tests.conftest import GEMINI_SUCCESS_RESPONSE

    router = async_client.app.state.router

    with respx.mock as mock:
        # Mock Groq to fail with 500, Gemini to succeed
        groq_mock = mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        gemini_mock = mock.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(200, json=GEMINI_SUCCESS_RESPONSE)
        )

        req = ChatRequest(model="gpt-4", messages=[Message(role="user", content="hello")])
        res = await router.route(req, request_id="test-id")

        assert res.x_gateway.provider_used == "gemini"
        assert res.x_gateway.fallback_triggered is True
        assert res.x_gateway.providers_tried == ["groq", "gemini"]
        assert groq_mock.called
        assert gemini_mock.called


@pytest.mark.asyncio
async def test_groq_cb_open_routes_to_gemini(async_client):
    from tests.conftest import GEMINI_SUCCESS_RESPONSE

    router = async_client.app.state.router

    with respx.mock as mock:
        # Mock both to return 200 (if Groq was called, it would succeed)
        groq_mock = mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200)
        )
        gemini_mock = mock.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(200, json=GEMINI_SUCCESS_RESPONSE)
        )

        # Set Groq's Circuit Breaker to OPEN
        groq_cb = router.circuit_breakers["groq"]
        await groq_cb._set_state(CBState.OPEN)

        req = ChatRequest(model="gpt-4", messages=[Message(role="user", content="hello")])
        res = await router.route(req, request_id="test-id")

        # Groq should be skipped entirely, routing directly to Gemini
        assert res.x_gateway.provider_used == "gemini"
        assert res.x_gateway.providers_tried == ["gemini"]
        assert not groq_mock.called
        assert gemini_mock.called

        # Reset circuit breaker state for subsequent tests
        await groq_cb._set_state(CBState.CLOSED)


@pytest.mark.asyncio
async def test_all_providers_failed(async_client):
    router = async_client.app.state.router

    with respx.mock as mock:
        groq_mock = mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        gemini_mock = mock.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*").mock(
            return_value=httpx.Response(500)
        )

        req = ChatRequest(model="gpt-4", messages=[Message(role="user", content="hello")])

        with pytest.raises(AllProvidersFailedError) as exc_info:
            await router.route(req, request_id="test-id")

        assert exc_info.value.extra.get("providers_tried") == ["groq", "gemini"]
        assert groq_mock.called
        assert gemini_mock.called
