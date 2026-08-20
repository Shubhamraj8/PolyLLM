import pytest

from app.config.loader import RetryConfig
from app.models.errors import NonRetryableProviderError, RetryableProviderError
from app.resilience.retry import build_retry_decorator


@pytest.fixture
def retry_config():
    return RetryConfig(
        max_attempts=3,
        base_delay_seconds=0.01,
        max_delay_seconds=0.05,
        multiplier=2.0,
        jitter=False,
    )


@pytest.mark.asyncio
async def test_retryable_error_retries_and_reraises(retry_config):
    attempts = 0
    decorator = build_retry_decorator(retry_config)

    @decorator
    async def failing_func():
        nonlocal attempts
        attempts += 1
        raise RetryableProviderError("Temporary failure", provider="test")

    with pytest.raises(RetryableProviderError):
        await failing_func()

    assert attempts == 3


@pytest.mark.asyncio
async def test_non_retryable_error_fails_immediately(retry_config):
    attempts = 0
    decorator = build_retry_decorator(retry_config)

    @decorator
    async def failing_func():
        nonlocal attempts
        attempts += 1
        raise NonRetryableProviderError("Invalid API key", provider="test")

    with pytest.raises(NonRetryableProviderError):
        await failing_func()

    assert attempts == 1


@pytest.mark.asyncio
async def test_succeeds_on_retry(retry_config):
    attempts = 0
    decorator = build_retry_decorator(retry_config)

    @decorator
    async def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RetryableProviderError("Flaky failure", provider="test")
        return "success"

    result = await flaky_func()
    assert result == "success"
    assert attempts == 2
