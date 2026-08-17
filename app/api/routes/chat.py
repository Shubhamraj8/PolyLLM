import time
from fastapi import APIRouter, Depends, Request, Security
from app.models.request import ChatRequest
from app.models.response import ChatResponse
from app.dependencies import get_api_key, get_rate_limiter, get_router, get_audit_logger, get_cost_tracker
from app.models.errors import RateLimitError, AllProvidersFailedError
from app.monitoring.metrics import request_count, request_latency

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
    ip = request.client.host
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

    # Route request through LLM Router
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
