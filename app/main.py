import sys
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_client import make_asgi_app

from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.request_id import RequestIDMiddleware
from app.api.routes import admin, chat, health, models
from app.config.loader import ConfigLoader
from app.config.settings import Settings
from fastapi.responses import JSONResponse
from app.providers.groq_adapter import GroqAdapter
from app.providers.gemini_adapter import GeminiAdapter
from app.resilience.circuit_breaker import CircuitBreaker
from app.routing.router import Router
from app.monitoring.metrics import init_metrics
from app.models.errors import GatewayError
from app.rate_limit.limiter import RateLimiter


async def gateway_error_handler(request, exc: GatewayError) -> JSONResponse:
    content = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "type": exc.error_type,
            **exc.extra,
        }
    }
    return JSONResponse(status_code=exc.http_status, content=content)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Track start time for health check uptime
    app.state.start_time = time.time()

    # Load env settings
    settings = Settings()
    app.state.settings = settings

    # Setup loguru
    logger.remove()
    logger.add(sys.stdout, serialize=True, level=settings.log_level)

    # Load config.yaml
    config_loader = ConfigLoader(settings.config_path)
    await config_loader.load()
    app.state.config_loader = config_loader

    # Init Redis
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        app.state.redis = redis
        logger.info("redis_connected", url=settings.redis_url)
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    # Initialize actual components
    providers = {
        "groq": GroqAdapter(
            api_key=settings.groq_api_key,
            retry_config=config_loader.config.retry,
        ),
        "gemini": GeminiAdapter(
            api_key=settings.gemini_api_key,
            retry_config=config_loader.config.retry,
        ),
    }
    app.state.providers = providers

    circuit_breakers = {
        name: CircuitBreaker(
            provider=name,
            config=config_loader.config.circuit_breaker,
            redis=redis,
        )
        for name in providers
    }
    app.state.circuit_breakers = circuit_breakers

    router = Router(
        providers=providers,
        circuit_breakers=circuit_breakers,
        config_loader=config_loader,
    )
    app.state.router = router

    app.state.rate_limiter = RateLimiter(
        redis=redis,
        config=config_loader.config.rate_limit,
    )
    app.state.audit_logger = None
    app.state.cost_tracker = None

    # Call init_metrics() (LG-013)
    init_metrics()

    yield

    # Cleanup
    if hasattr(app.state, "redis"):
        await app.state.redis.close()


def create_app() -> FastAPI:
    app = FastAPI(title="LLM Gateway", lifespan=lifespan)

    # Register Exception Handlers
    app.add_exception_handler(GatewayError, gateway_error_handler)

    # Middleware (order matters - last added runs first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Routers
    app.include_router(chat.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(health.router)
    app.include_router(admin.router, prefix="/admin")

    # Metrics
    settings = Settings()
    if settings.prometheus_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


app = create_app()
