import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config.loader import RetryConfig
from app.models.errors import NonRetryableProviderError, RetryableProviderError
from app.models.request import ChatRequest
from app.models.response import (
    ChatCompletionChunk,
    ChatResponse,
    Choice,
    ChunkChoice,
    DeltaMessage,
    GatewayMeta,
    MessageOutput,
    UsageInfo,
)
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

    async def complete_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        response = await self._retry(self._do_start_stream)(request)
        start_time = int(time.time())

        async def _generator() -> AsyncGenerator[str, None]:
            first_chunk = True
            try:
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    json_str = line[6:].strip()
                    if not json_str:
                        continue
                    try:
                        data = json.loads(json_str)
                    except Exception:
                        continue

                    candidates = data.get("candidates", [])
                    text = ""
                    finish_reason = None
                    if candidates:
                        cand = candidates[0]
                        parts = cand.get("content", {}).get("parts", [])
                        text = "".join([p.get("text", "") for p in parts])
                        raw_finish = cand.get("finishReason")
                        if raw_finish:
                            finish_reason = raw_finish.lower()

                    delta_role = "assistant" if first_chunk else None
                    first_chunk = False

                    chunk = ChatCompletionChunk(
                        id=f"gemini-{start_time}",
                        created=start_time,
                        model=request.model,
                        choices=[
                            ChunkChoice(
                                index=0,
                                delta=DeltaMessage(
                                    role=delta_role,
                                    content=text if text else None,
                                ),
                                finish_reason=finish_reason,
                            )
                        ],
                    )
                    yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
            finally:
                await response.aclose()

        return _generator()

    async def _do_start_stream(self, request: ChatRequest) -> httpx.Response:
        payload = self._transform_request(request)
        headers = {"Content-Type": "application/json"}
        url = f"{self.base_url}/models/{request.model}:streamGenerateContent?key={self.api_key}&alt=sse"

        client = httpx.AsyncClient(timeout=self.timeout_config)
        try:
            req = client.build_request(
                "POST",
                url,
                headers=headers,
                json=payload,
            )
            response = await client.send(req, stream=True)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            await client.aclose()
            raise RetryableProviderError(f"Gemini network error: {str(e)}")
        except Exception:
            await client.aclose()
            raise

        if response.status_code in (429, 500, 502, 503, 504):
            await response.aclose()
            raise RetryableProviderError(f"Gemini retryable error: {response.text}")

        if response.status_code in (400, 401, 403, 404):
            await response.aclose()
            raise NonRetryableProviderError(f"Gemini non-retryable error: {response.text}")

        if response.is_error:
            await response.aclose()
            response.raise_for_status()

        return response

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
