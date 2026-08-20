import httpx
import pytest
import respx

from app.config.loader import RetryConfig
from app.models.errors import NonRetryableProviderError, RetryableProviderError
from app.models.request import ChatRequest, Message
from app.providers.groq_adapter import GroqAdapter
from tests.conftest import GROQ_SUCCESS_RESPONSE


@pytest.fixture
def groq_adapter():
    # max_attempts=1 to isolate single HTTP call error handling without retries
    retry_config = RetryConfig(max_attempts=1)
    return GroqAdapter(api_key="test-key", retry_config=retry_config)


@pytest.fixture
def sample_request():
    return ChatRequest(
        model="mixtral-8x7b-32768",
        messages=[Message(role="user", content="hello")],
    )


@pytest.mark.asyncio
async def test_groq_success_parsing(groq_adapter, sample_request):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=GROQ_SUCCESS_RESPONSE)
        )
        response = await groq_adapter.complete(sample_request)

        assert response.id == "chatcmpl-test123"
        assert response.model == "mixtral-8x7b-32768"
        assert len(response.choices) == 1
        assert response.choices[0].message.content == "Hello!"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15
        assert response.x_gateway.provider_used == "groq"


@pytest.mark.asyncio
async def test_groq_429_raises_retryable(groq_adapter, sample_request):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(429, text="Rate limit reached")
        )
        with pytest.raises(RetryableProviderError):
            await groq_adapter.complete(sample_request)


@pytest.mark.asyncio
async def test_groq_500_raises_retryable(groq_adapter, sample_request):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(RetryableProviderError):
            await groq_adapter.complete(sample_request)


@pytest.mark.asyncio
async def test_groq_401_raises_non_retryable(groq_adapter, sample_request):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        with pytest.raises(NonRetryableProviderError):
            await groq_adapter.complete(sample_request)


@pytest.mark.asyncio
async def test_groq_timeout_raises_retryable(groq_adapter, sample_request):
    with respx.mock:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        with pytest.raises(RetryableProviderError):
            await groq_adapter.complete(sample_request)
