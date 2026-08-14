import time
from typing import Any

import httpx

from app.config.loader import RetryConfig
from app.models.errors import NonRetryableProviderError, RetryableProviderError
from app.models.request import ChatRequest
from app.models.response import ChatResponse, Choice, GatewayMeta, MessageOutput, UsageInfo
from app.providers.base import BaseProvider
from app.resilience.retry import build_retry_decorator
from app.resilience.timeout import get_timeout


class GeminiAdapter(BaseProvider):
    def __init__(self, api_key: str, retry_config: RetryConfig | None = None):
        self.name = "gemini"
        self.models = ["gemini-1.5-flash", "gemini-1.5-flash-8b"]
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.timeout_config = get_timeout("gemini")

        _config = retry_config or RetryConfig()
        self._retry = build_retry_decorator(_config)

    def get_timeout(self) -> float:
        return 15.0

    def _transform_request(self, request: ChatRequest) -> dict[str, Any]:
        contents = []
        system_instruction = None

        for msg in request.messages:
            role = msg.role
            content = msg.content

            if role == "system":
                # Gemini handles system instructions separately
                if system_instruction is None:
                    system_instruction = {"parts": [{"text": content}]}
                else:
                    system_instruction["parts"].append({"text": content})
            else:
                # Map assistant to model
                mapped_role = "model" if role == "assistant" else "user"
                contents.append({"role": mapped_role, "parts": [{"text": content}]})

        payload: dict[str, Any] = {"contents": contents, "generationConfig": {}}

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if request.temperature is not None:
            payload["generationConfig"]["temperature"] = request.temperature

        if request.max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = request.max_tokens

        return payload

    async def complete(self, request: ChatRequest) -> ChatResponse:
        return await self._retry(self._do_complete)(request)

    async def _do_complete(self, request: ChatRequest) -> ChatResponse:
        payload = self._transform_request(request)

        headers = {
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/models/{request.model}:generateContent?key={self.api_key}"

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_config) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise RetryableProviderError(f"Gemini network error: {str(e)}")

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code in (429, 500, 502, 503, 504):
            raise RetryableProviderError(f"Gemini retryable error: {response.text}")

        if response.status_code in (400, 401, 403, 404):
            raise NonRetryableProviderError(f"Gemini non-retryable error: {response.text}")

        response.raise_for_status()

        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            # Sometimes Gemini returns empty response or blocked content
            raise NonRetryableProviderError("Gemini returned no candidates.")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join([p.get("text", "") for p in parts])

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)

        return ChatResponse(
            id=f"gemini-{int(start_time)}",  # Gemini doesn't always provide an ID in chat completion response
            created=int(start_time),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=MessageOutput(
                        role="assistant",
                        content=text,
                    ),
                    finish_reason=candidate.get("finishReason", "stop").lower(),
                )
            ],
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            x_gateway=GatewayMeta(
                provider_used=self.name,
                model_used=request.model,
                latency_ms=latency_ms,
                request_id="",  # Filled later
            ),
        )
