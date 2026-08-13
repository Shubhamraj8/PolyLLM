import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        request_id = getattr(request.state, "request_id", None)

        try:
            response = await call_next(request)
            process_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "request_handled",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=process_time_ms,
                request_id=request_id,
            )
            return response
        except Exception as exc:
            process_time_ms = int((time.time() - start_time) * 1000)
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                latency_ms=process_time_ms,
                request_id=request_id,
                error=str(exc),
            )
            raise
