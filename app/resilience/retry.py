"""
Retry decorator factory using tenacity.

Only RetryableProviderError triggers retries.
NonRetryableProviderError bypasses retry entirely (fails immediately).

Config comes from config.yaml via RetryConfig pydantic model:
  max_attempts:       3      (1 initial + 2 retries)
  base_delay_seconds: 0.1
  multiplier:         2.0    (exponential backoff)
  max_delay_seconds:  5.0
  jitter:             true
"""

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config.loader import RetryConfig
from app.models.errors import RetryableProviderError


def build_retry_decorator(config: RetryConfig):
    """
    Return a tenacity retry decorator configured from the gateway's RetryConfig.

    Usage inside an adapter:
        _retry = build_retry_decorator(config.retry)

        @_retry
        async def complete(self, request):
            ...
    """
    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential_jitter(
            initial=config.base_delay_seconds,
            exp_base=config.multiplier,
            max=config.max_delay_seconds,
        ),
        retry=retry_if_exception_type(RetryableProviderError),
        reraise=True,  # re-raise the original error after all attempts exhausted
    )
