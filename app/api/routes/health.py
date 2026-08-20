import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> JSONResponse:
    app = request.app
    redis = app.state.redis
    config_loader = app.state.config_loader
    circuit_breakers = app.state.circuit_breakers
    start_time = getattr(app.state, "start_time", time.time())

    # Check Redis
    redis_status = "connected"
    redis_latency_ms = 0
    http_status = 200

    ping_start = time.time()
    try:
        await redis.ping()
        redis_latency_ms = int((time.time() - ping_start) * 1000)
    except Exception as e:
        logger.error("health_redis_ping_failed", error=str(e))
        redis_status = "disconnected"
        http_status = 503

    # Check Providers (Circuit Breakers)
    providers_state = {}
    for name, cb in circuit_breakers.items():
        state = await cb.get_state()
        failures = await redis.get(cb._key_failures) or 0
        providers_state[name] = {"circuit_breaker": state.value, "failure_count": int(failures)}

    # Uptime
    uptime_seconds = int(time.time() - start_time)

    # Active Config
    fallback_order = config_loader.get_chain()

    body = {
        "status": "healthy" if http_status == 200 else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
        "uptime_seconds": uptime_seconds,
        "redis": {"status": redis_status, "latency_ms": redis_latency_ms},
        "providers": providers_state,
        "config": {"fallback_order": fallback_order},
    }

    return JSONResponse(status_code=http_status, content=body)
