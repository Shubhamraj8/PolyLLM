import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.config.loader import AuditConfig
from app.models.request import ChatRequest
from app.models.response import ChatResponse

_REDIS_KEY = "audit:requests"


class AuditLogger:
    def __init__(self, redis: Any, config: AuditConfig) -> None:
        self.redis = redis
        self.config = config

    async def log(
        self,
        request_id: str,
        ip: str,
        api_key: str,
        body: ChatRequest,
        response: ChatResponse,
        latency_ms: int,
    ) -> None:
        if not self.config.enabled:
            return

        meta = response.x_gateway
        usage = response.usage

        entry = {
            "request_id": request_id,
            "timestamp": _utcnow(),
            "ip": ip,
            "api_key_prefix": _mask_key(api_key),
            "model_requested": body.model,
            "provider_used": meta.provider_used,
            "model_used": meta.model_used,
            "fallback_triggered": meta.fallback_triggered,
            "providers_tried": meta.providers_tried,
            "status": "success",
            "http_status": 200,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": meta.estimated_cost_usd,
            "error": None,
        }

        await self._write(entry)
        logger.info("audit_success", **entry)

    async def log_error(
        self,
        request_id: str,
        ip: str,
        api_key: str,
        body: ChatRequest,
        error_msg: str,
        latency_ms: int,
        providers_tried: list[str],
    ) -> None:
        if not self.config.enabled:
            return

        entry = {
            "request_id": request_id,
            "timestamp": _utcnow(),
            "ip": ip,
            "api_key_prefix": _mask_key(api_key),
            "model_requested": body.model,
            "provider_used": None,
            "model_used": None,
            "fallback_triggered": len(providers_tried) > 1,
            "providers_tried": providers_tried,
            "status": "failed",
            "http_status": 503,
            "latency_ms": latency_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "error": error_msg,
        }

        await self._write(entry)
        logger.error("audit_error", **entry)

    async def _write(self, entry: dict) -> None:
        payload = json.dumps(entry)
        pipe = self.redis.pipeline()
        pipe.lpush(_REDIS_KEY, payload)
        pipe.ltrim(_REDIS_KEY, 0, self.config.max_entries - 1)
        await pipe.execute()


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _mask_key(api_key: str) -> str:
    return api_key[:8] + "..."
