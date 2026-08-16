from fastapi import APIRouter, Depends, Request, Security
from app.models.request import ChatRequest
from app.models.response import ChatResponse
from app.dependencies import get_api_key, get_rate_limiter, get_router
from app.models.errors import RateLimitError
from app.monitoring.metrics import request_count

router = APIRouter()


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(
    request: Request,
    body: ChatRequest,
    api_key: str = Security(get_api_key),
    rate_limiter = Depends(get_rate_limiter),
    llm_router = Depends(get_router),
):
    ip = request.client.host
    request_id = request.state.request_id

    # Check Rate Limits
    res = await rate_limiter.check(api_key, ip)
    if not res.allowed:
        # Increment Prometheus request count for rate limited status
        request_count.labels(provider="none", model=body.model, status="rate_limited").inc()
        raise RateLimitError(
            message=f"Rate limit exceeded. Try again in {res.retry_after}s.",
            retry_after=res.retry_after,
        )

    # Route request through LLM Router
    response = await llm_router.route(body, request_id)
    return response
