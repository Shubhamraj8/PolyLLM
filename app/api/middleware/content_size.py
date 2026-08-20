from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_content_size: int = 10 * 1024 * 1024):  # Default 10 MB limit
        super().__init__(app)
        self.max_content_size = max_content_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_content_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "message": "Payload Too Large. Maximum allowed size is 10 MB.",
                                "type": "payload_too_large",
                                "code": "payload_too_large",
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
