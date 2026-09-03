import time
from collections.abc import AsyncGenerator

import httpx

from app.config.loader import RetryConfig
from app.models.errors import NonRetryableProviderError, RetryableProviderError
from app.models.request import ChatRequest
from app.models.response import ChatResponse, Choice, GatewayMeta, MessageOutput, UsageInfo
from app.providers.base import BaseProvider
from app.resilience.retry import build_retry_decorator
from app.resilience.timeout import get_timeout


class GroqAdapter(BaseProvider):
    def __init__(self, api_key: str, retry_config: RetryConfig | None = None):
        self.name = "groq"
        self.models = ["mixtral-8x7b-32768", "llama-3.1-8b-instant"]
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout_config = get_timeout("groq")

        _config = retry_config or RetryConfig()
        self._retry = build_retry_decorator(_config)

    def get_timeout(self) -> float:
        return 10.0

    async def complete(self, request: ChatRequest) -> ChatResponse:
        return await self._retry(self._do_complete)(request)

    async def complete_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        response = await self._retry(self._do_start_stream)(request)

        async def _generator() -> AsyncGenerator[str, None]:
            try:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        yield f"{line}\n\n"
            finally:
                await response.aclose()

        return _generator()

    async def _do_start_stream(self, request: ChatRequest) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True

        client = httpx.AsyncClient(timeout=self.timeout_config)
        try:
            req = client.build_request(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response = await client.send(req, stream=True)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            await client.aclose()
            raise RetryableProviderError(f"Groq network error: {str(e)}")
        except Exception:
            await client.aclose()
            raise

        if response.status_code in (429, 500, 502, 503, 504):
            await response.aclose()
            raise RetryableProviderError(f"Groq retryable error: {response.text}")

        if response.status_code in (400, 401, 403, 404):
            await response.aclose()
            raise NonRetryableProviderError(f"Groq non-retryable error: {response.text}")

        if response.is_error:
            await response.aclose()
            response.raise_for_status()

        return response

    async def _do_complete(self, request: ChatRequest) -> ChatResponse:

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Dump payload, excluding null values like missing optional fields
        payload = request.model_dump(exclude_none=True)

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_config) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise RetryableProviderError(f"Groq network error: {str(e)}")

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code in (429, 500, 502, 503, 504):
            raise RetryableProviderError(f"Groq retryable error: {response.text}")

        if response.status_code in (400, 401, 403, 404):
            raise NonRetryableProviderError(f"Groq non-retryable error: {response.text}")

        response.raise_for_status()

        data = response.json()
        usage = data.get("usage", {})

        return ChatResponse(
            id=data.get("id", ""),
            created=data.get("created", 0),
            model=data.get("model", request.model),
            choices=[
                Choice(
                    index=c.get("index", 0),
                    message=MessageOutput(
                        role=c.get("message", {}).get("role", "assistant"),
                        content=c.get("message", {}).get("content", ""),
                    ),
                    finish_reason=c.get("finish_reason", "stop"),
                )
                for c in data.get("choices", [])
            ],
            usage=UsageInfo(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
            x_gateway=GatewayMeta(
                provider_used=self.name,
                model_used=data.get("model", request.model),
                latency_ms=latency_ms,
                request_id="",  # Filled later by the router or middleware
            ),
        )
