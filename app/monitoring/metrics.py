"""
Prometheus metrics for the LLM Gateway.

All metric objects are module-level singletons — import and use directly.
Call init_metrics() once at app startup to ensure they're registered.
"""

from prometheus_client import Counter, Gauge, Histogram

# ── 1. Total requests ────────────────────────────────────────────────────────
request_count = Counter(
    "gateway_requests_total",
    "Total requests processed by the gateway",
    ["provider", "model", "status"],  # status: success | failed | rate_limited
)

# ── 2. End-to-end latency histogram ─────────────────────────────────────────
request_latency = Histogram(
    "gateway_request_duration_seconds",
    "End-to-end request latency in seconds",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

# ── 3. Per-provider outcomes ─────────────────────────────────────────────────
provider_requests = Counter(
    "gateway_provider_requests_total",
    "Requests sent to each provider",
    ["provider", "outcome"],  # outcome: success | failure | skipped
)

# ── 4. Circuit breaker state gauge ───────────────────────────────────────────
circuit_breaker_state = Gauge(
    "gateway_circuit_breaker_state",
    "Circuit breaker state per provider (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
    ["provider"],
)

# ── 5. Token usage counter ───────────────────────────────────────────────────
tokens_used = Counter(
    "gateway_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "type"],  # type: prompt | completion
)


def init_metrics() -> None:
    """
    Called once during app lifespan startup to ensure all metric objects
    are instantiated and registered with the Prometheus default registry.
    Already done by module-level definitions above — this is a no-op hook
    kept for clarity and forward-compatibility.
    """
    pass
