"""
Redis-backed Circuit Breaker state machine.

States
------
CLOSED   (0) — healthy; requests flow through normally.
OPEN     (1) — unhealthy; requests are blocked immediately.
HALF_OPEN (2) — cooldown expired; one probe request is allowed through.

Transitions
-----------
CLOSED  + N failures in window  → OPEN
OPEN    + cooldown elapsed      → HALF_OPEN  (automatic, on next get_state() call)
HALF_OPEN + success             → CLOSED
HALF_OPEN + failure             → OPEN

All state lives in Redis so multiple gateway instances share the same view.

Redis keys (all prefixed with ``cb:{provider}:``)
-------------------------------------------------
state      → "CLOSED" | "OPEN" | "HALF_OPEN"   (no TTL)
failures   → int (failure counter)              (TTL = window_seconds)
opened_at  → float (unix timestamp)             (no TTL)
"""

import time
from enum import StrEnum

from loguru import logger

from app.config.loader import CircuitBreakerConfig
from app.monitoring.metrics import circuit_breaker_state


class CBState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    @property
    def numeric(self) -> int:
        return {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}[self.value]


class CircuitBreaker:
    def __init__(self, provider: str, config: CircuitBreakerConfig, redis) -> None:
        self.provider = provider
        self.config = config
        self.redis = redis

        # Redis key names
        self._key_state = f"cb:{provider}:state"
        self._key_failures = f"cb:{provider}:failures"
        self._key_opened_at = f"cb:{provider}:opened_at"

    # ── Public interface ─────────────────────────────────────────────────────

    async def get_state(self) -> CBState:
        """
        Return the current circuit breaker state.

        If the state is OPEN and the cooldown has elapsed, automatically
        transition to HALF_OPEN so the next call can probe the provider.
        """
        raw = await self.redis.get(self._key_state)
        state = CBState(raw) if raw else CBState.CLOSED

        if state is CBState.OPEN:
            opened_at = await self.redis.get(self._key_opened_at)
            if opened_at is not None:
                elapsed = time.time() - float(opened_at)
                if elapsed >= self.config.cooldown_seconds:
                    await self._set_state(CBState.HALF_OPEN)
                    logger.info(
                        "circuit_breaker_half_open",
                        provider=self.provider,
                        elapsed_s=round(elapsed, 1),
                    )
                    return CBState.HALF_OPEN

        return state

    async def is_open(self) -> bool:
        """Return True only when the circuit is fully OPEN (not HALF_OPEN)."""
        return await self.get_state() is CBState.OPEN

    async def record_success(self) -> None:
        """
        A provider call succeeded.

        HALF_OPEN + success → CLOSED  (delete failure counter)
        CLOSED    + success → no-op   (already healthy)
        """
        state = await self.get_state()
        if state is CBState.HALF_OPEN:
            await self.redis.delete(self._key_failures)
            await self._set_state(CBState.CLOSED)
            logger.info("circuit_breaker_closed", provider=self.provider, reason="probe_success")

    async def record_failure(self) -> None:
        """
        A provider call failed (retryable or otherwise).

        HALF_OPEN + failure → OPEN               (immediately re-open)
        CLOSED    + failure → INCR failure counter
                              if count >= threshold → OPEN
        OPEN      + failure → no-op (already open)
        """
        state = await self.get_state()

        if state is CBState.HALF_OPEN:
            await self._set_state(CBState.OPEN)
            logger.warning(
                "circuit_breaker_reopened",
                provider=self.provider,
                reason="probe_failure",
            )
            return

        if state is CBState.OPEN:
            return  # already open — nothing to do

        # CLOSED: increment the rolling failure counter
        failures = await self.redis.incr(self._key_failures)
        if failures == 1:
            # First failure in a fresh window — set the TTL
            await self.redis.expire(self._key_failures, self.config.window_seconds)

        logger.debug(
            "circuit_breaker_failure_recorded",
            provider=self.provider,
            failures=failures,
            threshold=self.config.failure_threshold,
        )

        if failures >= self.config.failure_threshold:
            await self._set_state(CBState.OPEN)
            logger.warning(
                "circuit_breaker_opened",
                provider=self.provider,
                failures=failures,
                threshold=self.config.failure_threshold,
            )

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _set_state(self, state: CBState) -> None:
        """Persist state to Redis and update the Prometheus gauge."""
        await self.redis.set(self._key_state, state.value)

        if state is CBState.OPEN:
            await self.redis.set(self._key_opened_at, str(time.time()))

        # Update Prometheus gauge
        circuit_breaker_state.labels(provider=self.provider).set(state.numeric)
