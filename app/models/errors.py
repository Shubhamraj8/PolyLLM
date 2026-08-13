class GatewayError(Exception):
    http_status: int = 500
    code: str = "internal_error"
    error_type: str = "gateway_error"

    def __init__(self, message: str, **kwargs):
        self.message = message
        self.extra = kwargs
        super().__init__(message)


class RateLimitError(GatewayError):
    http_status = 429
    code = "rate_limit_exceeded"
    error_type = "rate_limit_error"


class AllProvidersFailedError(GatewayError):
    http_status = 503
    code = "all_providers_failed"
    error_type = "service_unavailable"


class InvalidRequestError(GatewayError):
    http_status = 400
    code = "invalid_request"
    error_type = "invalid_request_error"


class RetryableProviderError(GatewayError):
    """Raised on transient provider failures (5xx, 429, timeouts). Triggers retry + fallback."""

    pass


class NonRetryableProviderError(GatewayError):
    """Raised on permanent provider failures (400, 401, 403). Skips retry, moves to next provider."""

    pass
