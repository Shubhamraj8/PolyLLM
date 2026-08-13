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

    # Initialize placeholders for components to be built in subsequent tickets
    app.state.providers = {}
    app.state.circuit_breakers = {}
    app.state.router = None
    app.state.rate_limiter = None
    app.state.audit_logger = None
    app.state.cost_tracker = None

    # Call init_metrics() once implemented (LG-013)

    yield

    # Cleanup
    if hasattr(app.state, "redis"):
        await app.state.redis.close()


def create_app() -> FastAPI:
    app = FastAPI(title="LLM Gateway", lifespan=lifespan)

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
