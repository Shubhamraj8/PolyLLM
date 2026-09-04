import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse

from app.dependencies import (
    get_api_key,
    get_config_loader,
    get_redis,
    get_router,
)

router = APIRouter()


@router.post("/reload")
async def reload_config(
    api_key: str = Security(get_api_key),
    config_loader=Depends(get_config_loader),
):
    await config_loader.reload()
    timestamp = datetime.now(UTC).isoformat()
    return JSONResponse(content={"status": "reloaded", "timestamp": timestamp})


@router.get("/stats")
async def get_admin_stats(
    api_key: str = Security(get_api_key),
    redis=Depends(get_redis),
    config_loader=Depends(get_config_loader),
    llm_router=Depends(get_router),
):
    # 1. Circuit Breakers Status
    circuit_breakers_data = {}
    if llm_router and hasattr(llm_router, "circuit_breakers"):
        for provider_name, cb in llm_router.circuit_breakers.items():
            state = await cb.get_state()
            failures_bytes = await redis.get(f"cb:{provider_name}:failures")
            opened_at_bytes = await redis.get(f"cb:{provider_name}:opened_at")
            failures = int(failures_bytes.decode()) if failures_bytes else 0
            opened_at = float(opened_at_bytes.decode()) if opened_at_bytes else None

            circuit_breakers_data[provider_name] = {
                "state": state.value,
                "failure_count": failures,
                "failure_threshold": config_loader.config.circuit_breaker.failure_threshold,
                "cooldown_seconds": config_loader.config.circuit_breaker.cooldown_seconds,
                "opened_at": opened_at,
            }

    # 2. Costs & Tokens Data
    cost_total_bytes = await redis.get("cost:total")
    tokens_total_bytes = await redis.get("cost:tokens:total")
    cost_groq_bytes = await redis.get("cost:by_provider:groq")
    cost_gemini_bytes = await redis.get("cost:by_provider:gemini")

    total_cost = round(float(cost_total_bytes.decode()), 6) if cost_total_bytes else 0.0
    total_tokens = int(tokens_total_bytes.decode()) if tokens_total_bytes else 0
    cost_groq = round(float(cost_groq_bytes.decode()), 6) if cost_groq_bytes else 0.0
    cost_gemini = round(float(cost_gemini_bytes.decode()), 6) if cost_gemini_bytes else 0.0

    # 3. Recent Audit Logs (up to 50)
    audit_raw = await redis.lrange("audit:requests", 0, 49)
    audit_logs = []
    if audit_raw:
        for item in audit_raw:
            try:
                raw_str = item.decode() if isinstance(item, bytes) else item
                audit_logs.append(json.loads(raw_str))
            except Exception:
                pass

    # 4. Aggregated Summary
    total_requests = len(audit_logs)
    failed_requests = sum(1 for log in audit_logs if log.get("status") == "failed")
    error_rate = round((failed_requests / total_requests) * 100, 2) if total_requests > 0 else 0.0
    latencies = [log.get("latency_ms", 0) for log in audit_logs if "latency_ms" in log]
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

    return JSONResponse(
        content={
            "overview": {
                "total_requests_recorded": total_requests,
                "total_cost_usd": total_cost,
                "error_rate_percent": error_rate,
                "avg_latency_ms": avg_latency,
                "total_tokens": total_tokens,
            },
            "circuit_breakers": circuit_breakers_data,
            "cost_breakdown": {
                "total_usd": total_cost,
                "groq_usd": cost_groq,
                "gemini_usd": cost_gemini,
                "tokens_total": total_tokens,
            },
            "config": config_loader.config.model_dump(exclude_none=True),
            "recent_audits": audit_logs,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

