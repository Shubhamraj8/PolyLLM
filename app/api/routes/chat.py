import time

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import StreamingResponse

from app.dependencies import (
    get_api_key,
    get_audit_logger,
    get_cost_tracker,
    get_rate_limiter,
    get_router,
)
from app.models.errors import AllProvidersFailedError, RateLimitError
from app.models.request import ChatRequest
from app.models.response import ChatCompletionChunk, ChatResponse, GatewayMeta
from app.monitoring.metrics import request_count, request_latency
from app.utils.network import get_client_ip

router = APIRouter()


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(
    request: Request,
    body: ChatRequest,
    api_key: str = Security(get_api_key),
    rate_limiter=Depends(get_rate_limiter),
    llm_router=Depends(get_router),
    audit_logger=Depends(get_audit_logger),
    cost_tracker=Depends(get_cost_tracker),
):
    ip = get_client_ip(request)
    request_id = request.state.request_id
    start_time = time.time()

    # Check Rate Limits
    res = await rate_limiter.check(api_key, ip)
    if not res.allowed:
        request_count.labels(provider="none", model=body.model, status="rate_limited").inc()
        raise RateLimitError(
            message=f"Rate limit exceeded. Try again in {res.retry_after}s.",
            retry_after=res.retry_after,
        )

    # Route request through LLM Router (Streaming Path)
    if body.stream:
        try:
            stream_gen, meta = await llm_router.route_stream(body, request_id)
        except AllProvidersFailedError as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            providers_tried = exc.extra.get("providers_tried", [])
            request_count.labels(provider="none", model=body.model, status="failed").inc()
            if audit_logger:
                await audit_logger.log_error(
                    request_id=request_id,
                    ip=ip,
                    api_key=api_key,
                    body=body,
                    error_msg=exc.message,
                    latency_ms=latency_ms,
                    providers_tried=providers_tried,
                )
            raise

        async def event_generator():
            provider_used = meta["provider_used"]
            model_used = meta["model_used"]
            fallback_triggered = meta["fallback_triggered"]
            providers_tried = meta["providers_tried"]

            completion_tokens = 0
            async for chunk_str in stream_gen:
                completion_tokens += 1
                yield chunk_str

            latency_ms = int((time.time() - start_time) * 1000)
            latency_secs = latency_ms / 1000.0
            request_count.labels(provider=provider_used, model=body.model, status="success").inc()
            request_latency.labels(provider=provider_used, model=body.model).observe(latency_secs)

            estimated_cost = 0.0
            prompt_tokens = sum(len(m.content.split()) for m in body.messages)
            if cost_tracker:
                estimated_cost = await cost_tracker.record(
                    provider=provider_used,
                    model=model_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

            gateway_meta = GatewayMeta(
                provider_used=provider_used,
                model_used=model_used,
                latency_ms=latency_ms,
                request_id=request_id,
                fallback_triggered=fallback_triggered,
                providers_tried=providers_tried,
                estimated_cost_usd=estimated_cost,
            )

            meta_chunk = ChatCompletionChunk(
                id=f"chatcmpl-{request_id}",
                created=int(start_time),
                model=body.model,
                choices=[],
                x_gateway=gateway_meta,
            )
            yield f"data: {meta_chunk.model_dump_json(exclude_none=True)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Route request through LLM Router (Buffered Non-Streaming Path)

    try:
        response = await llm_router.route(body, request_id)
    except AllProvidersFailedError as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        providers_tried = exc.extra.get("providers_tried", [])
        request_count.labels(provider="none", model=body.model, status="failed").inc()
        if audit_logger:
            await audit_logger.log_error(
                request_id=request_id,
                ip=ip,
                api_key=api_key,
                body=body,
                error_msg=exc.message,
                latency_ms=latency_ms,
                providers_tried=providers_tried,
            )
        raise

    latency_ms = int((time.time() - start_time) * 1000)
    latency_secs = latency_ms / 1000.0
    provider_used = response.x_gateway.provider_used
    response.x_gateway.latency_ms = latency_ms
    request_count.labels(provider=provider_used, model=response.model, status="success").inc()
    request_latency.labels(provider=provider_used, model=response.model).observe(latency_secs)

    # Record cost and attach to response metadata
    if cost_tracker:
        cost = await cost_tracker.record(
            provider=provider_used,
            model=response.x_gateway.model_used,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
        response.x_gateway.estimated_cost_usd = cost

    if audit_logger:
        await audit_logger.log(
            request_id=request_id,
            ip=ip,
            api_key=api_key,
            body=body,
            response=response,
            latency_ms=latency_ms,
        )

    return response
