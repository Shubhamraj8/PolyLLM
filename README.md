# PolyLLM Gateway

<div align="center">

![Build Status](https://github.com/Shubhamraj8/PolyLLM/workflows/Test%20%26%20Lint/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.4-DC382D?logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**A production-grade, OpenAI-compatible LLM gateway with multi-provider fallback routing, distributed circuit breakers, rate limiting, cost tracking, and full observability.**

</div>

---

## 📖 Overview

PolyLLM Gateway is a self-hosted reverse proxy that sits between your application and LLM providers (Groq, Gemini). It exposes an OpenAI-compatible REST API, so existing clients like the OpenAI SDK work without modification.

The gateway handles **provider-level resilience** automatically: if a provider is down, rate-limited, or slow, the gateway fails over to the next provider in the configured chain — transparently and without the calling application needing to know.

```
Your App (OpenAI SDK / curl)
       │  POST /v1/chat/completions
       │  X-API-Key: <your-key>
       ▼
┌──────────────────────────────────────────────┐
│              PolyLLM Gateway                 │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Middleware Layer                        │ │
│  │  ├─ Request ID injection               │ │
│  │  ├─ Structured JSON logging (loguru)   │ │
│  │  └─ Payload size enforcement (10 MB)   │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Rate Limiter                            │ │
│  │  ├─ Per API Key (sliding window log)   │ │
│  │  └─ Per Client IP (proxy-aware)        │ │  ← Redis
│  └─────────────────────────────────────────┘ │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Router                                  │ │  ← config.yaml
│  │  ├─ Model mapping (gpt-4 → mixtral)    │ │
│  │  ├─ Fallback chain selection           │ │
│  │  │                                     │ │
│  │  │  Provider 1: Groq                   │ │
│  │  │   ├─ Circuit Breaker (CB)           │ │  ← Redis
│  │  │   └─ Retry Engine (3× + backoff)   │ │
│  │  │                                     │ │
│  │  │  Provider 2: Gemini (fallback)      │ │
│  │  │   ├─ Circuit Breaker (CB)           │ │  ← Redis
│  │  │   └─ Retry Engine                  │ │
│  │  └─────────────────────────────────── ┘ │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Post-Processing                         │ │
│  │  ├─ Cost Tracker (USD estimation)      │ │  ← Redis
│  │  └─ Audit Logger (anonymized, LTRIM)   │ │  ← Redis
│  └─────────────────────────────────────────┘ │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Observability                           │ │
│  │  ├─ GET /metrics (Prometheus)          │ │
│  │  ├─ GET /health  (Redis + CB states)   │ │
│  │  └─ Grafana dashboards (provisioned)   │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

---

## ✨ Feature Highlights

| Feature | Detail |
|---|---|
| **OpenAI-Compatible API** | Drop-in replacement. Works with `openai` Python SDK, LangChain, LlamaIndex without code changes. |
| **Automatic Fallback Routing** | Configurable chains (e.g. Groq → Gemini). If Groq fails, requests seamlessly move to Gemini. |
| **Distributed Circuit Breaker** | Three-state machine (CLOSED → OPEN → HALF\_OPEN) backed by Redis. Multiple gateway instances share the same CB state. |
| **Retry with Exponential Backoff** | Tenacity-powered retry logic with jitter. Only retries transient errors (429, 500, timeouts). 401/400 fail immediately. |
| **Dual-Layer Rate Limiting** | Sliding window rate limiter enforced separately per API key AND per client IP. Proxy-aware — reads `X-Forwarded-For` / `CF-Connecting-IP`. |
| **Cost & Token Tracking** | Tracks prompt + completion tokens and estimated USD cost per request by provider and model, with daily breakdowns in Redis. |
| **Secure Audit Logging** | Circular audit log stored in Redis. API keys masked (`sk-abcd...`). Client IPs anonymised with SHA-256 before storage. |
| **Config Hot-Reload** | `POST /admin/reload` re-reads `config.yaml` at runtime under an asyncio lock. No restart required to change fallback chains or thresholds. |
| **Request Size Enforcement** | Payloads over 10 MB are rejected at the middleware layer with HTTP `413` before any routing logic runs. |
| **Prometheus + Grafana** | Pre-provisioned Grafana dashboard exposing latency histograms, request counts, token usage, and per-provider circuit breaker states. |
| **95% Test Coverage** | 64 tests across unit, integration, and end-to-end layers using fakeredis and respx — no real network calls in tests. |

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.12, FastAPI, Uvicorn (ASGI) |
| **State & Storage** | Redis 7.4 (circuit breaker, rate limiter, audit, cost tracking) |
| **Resilience** | Tenacity (retry + backoff), asyncio.Lock (hot-reload safety) |
| **HTTP Client** | HTTPX AsyncClient (provider calls) |
| **Validation** | Pydantic v2 (request schemas, config models) |
| **Configuration** | YAML (config.yaml) + pydantic-settings (.env) |
| **Observability** | Prometheus Client, Grafana 11.2 |
| **Testing** | Pytest, pytest-asyncio, Fakeredis, RESPX |
| **Code Quality** | Ruff, Black, pre-commit |
| **Containerisation** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions (test + lint + audit on every push) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- A [Groq API key](https://console.groq.com/) and/or a [Gemini API key](https://aistudio.google.com/)

### 1. Clone & Configure

```bash
git clone https://github.com/Shubhamraj8/PolyLLM.git
cd PolyLLM
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
GATEWAY_API_KEY=your-secret-gateway-key   # clients send this in X-API-Key header
```

### 2. Start Supporting Services

Starts Redis, Prometheus, and Grafana in the background:

```bash
docker-compose up -d
```

| Service | URL |
|---|---|
| Redis | `localhost:6379` |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

### 3. Run the Gateway (Development)

```bash
python -m venv venv
source venv/bin/activate    # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The gateway is now live at **http://localhost:8000**.

---

## 🐳 Full Stack Docker Deployment

Spin up all four services (gateway + Redis + Prometheus + Grafana) together:

```bash
docker-compose -f docker-compose.full.yml up --build -d
```

| Service | URL |
|---|---|
| **Gateway API** | http://localhost:8000 |
| **Prometheus** | http://localhost:9090 |
| **Grafana** | http://localhost:3000 |

---

## 🔌 API Reference

All routes follow the OpenAI specification. Requests require the `X-API-Key` header.

### POST `/v1/chat/completions`

Send a chat completion request. Supports model aliases that map to upstream providers.

**Request:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-gateway-key" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user",   "content": "What is a circuit breaker pattern?"}
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }'
```

**Streaming Request (`"stream": true`):**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-gateway-key" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Tell me a joke."}],
    "stream": true
  }'
```

**Streaming Response (`Content-Type: text/event-stream`):**
```http
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1728000000,"model":"mixtral-8x7b-32768","choices":[{"index":0,"delta":{"role":"assistant","content":"Why"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1728000000,"model":"mixtral-8x7b-32768","choices":[{"index":0,"delta":{"content":" did..."},"finish_reason":"stop"}]}

data: {"id":"chatcmpl-req-7f3a2b","object":"chat.completion.chunk","created":1728000000,"model":"gpt-4","choices":[],"x_gateway":{"provider_used":"groq","model_used":"mixtral-8x7b-32768","latency_ms":210,"request_id":"req-7f3a2b","fallback_triggered":false,"providers_tried":["groq"],"estimated_cost_usd":0.0}}

data: [DONE]
```

**Response (200 OK - Non-Streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1728000000,
  "model": "mixtral-8x7b-32768",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "A circuit breaker ..."},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 52,
    "total_tokens": 80
  },
  "x_gateway": {
    "provider_used": "groq",
    "model_used": "mixtral-8x7b-32768",
    "latency_ms": 312,
    "request_id": "req-7f3a2b",
    "fallback_triggered": false,
    "providers_tried": ["groq"],
    "estimated_cost_usd": 0.0
  }
}
```


### Model Aliases

| Gateway Model | Routes To | Provider |
|---|---|---|
| `gpt-4` | `mixtral-8x7b-32768` | Groq |
| `gpt-3.5-turbo` | `llama-3.1-8b-instant` | Groq |
| `gemini` | `gemini-1.5-flash` | Gemini |
| `gemini-flash-8b` | `gemini-1.5-flash-8b` | Gemini |

### GET `/v1/models`

Returns the list of all supported models.

```bash
curl http://localhost:8000/v1/models -H "X-API-Key: your-key"
```

### GET `/health`

Returns gateway health including Redis connectivity, circuit breaker states, and uptime.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "redis": "connected",
  "providers": {
    "groq":   {"circuit_breaker": "CLOSED"},
    "gemini": {"circuit_breaker": "CLOSED"}
  },
  "config": {
    "version": "1.0.0",
    "default_chain": "default",
    "chains": {"default": ["groq", "gemini"]}
  }
}
```

### POST `/admin/reload` *(Auth required)*

Reload `config.yaml` at runtime without restarting the gateway.

```bash
curl -X POST http://localhost:8000/admin/reload \
  -H "X-API-Key: your-secret-gateway-key"
```

```json
{"status": "reloaded", "timestamp": "2026-08-20T18:00:00.000000+00:00"}
```

---

## ⚙️ Configuration Reference

The gateway behaviour is controlled by `config.yaml`. Hot-reload is supported.

```yaml
version: "1.0.0"

routing:
  default_chain: default            # which chain to use if none specified
  chains:
    default: [groq, gemini]         # try Groq first, fallback to Gemini
    gemini_first: [gemini, groq]    # reverse priority chain

providers:
  groq:
    timeout_seconds: 10
    models: [mixtral-8x7b-32768, llama-3.1-8b-instant]
    default_model: mixtral-8x7b-32768
    base_url: https://api.groq.com/openai/v1
  gemini:
    timeout_seconds: 15
    models: [gemini-1.5-flash, gemini-1.5-flash-8b]
    default_model: gemini-1.5-flash
    base_url: https://generativelanguage.googleapis.com/v1beta

circuit_breaker:
  failure_threshold: 5    # failures before OPEN
  window_seconds: 60      # rolling window
  cooldown_seconds: 30    # OPEN → HALF_OPEN wait time

rate_limit:
  per_api_key:
    requests: 100
    window_seconds: 60
  per_ip:
    requests: 200
    window_seconds: 60

retry:
  max_attempts: 3
  base_delay_seconds: 0.1
  max_delay_seconds: 5.0
  multiplier: 2.0
  jitter: true

audit:
  enabled: true
  max_entries: 10000
  ttl_days: 7
```

---

## 🔒 Security Model

| Concern | Implementation |
|---|---|
| **API Authentication** | All routes (including `/admin/reload`) require `X-API-Key` header validated against `GATEWAY_API_KEY` env var. |
| **Payload Size Limit** | `ContentSizeLimitMiddleware` rejects requests with `Content-Length > 10 MB` before routing. |
| **IP Anonymisation** | Client IP addresses are SHA-256 hashed before being written to the Redis audit log. Raw IPs are never persisted. |
| **API Key Masking** | Gateway API keys stored in audit entries are truncated to 8 characters + `...`. |
| **Proxy IP Resolution** | Rate limiting reads `CF-Connecting-IP` → `X-Forwarded-For` → `request.client.host` to correctly attribute requests behind proxies. |
| **Required Env Vars** | `GROQ_API_KEY` and `GEMINI_API_KEY` have no hardcoded fallback defaults. The server refuses to start if they are missing. |
| **Input Validation** | Pydantic schemas enforce `max_length` on all text fields and numeric bounds on `temperature` / `max_tokens`. |
| **Dependency Scanning** | `pip-audit` runs in CI on every push to detect known CVEs in dependencies. |

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run full suite with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

### ⚡ OpenAI SDK Smoke Test

Verify full OpenAI SDK compatibility (streaming + non-streaming) against a running server:

```bash
# Start local gateway
uvicorn app.main:app --reload --port 8000

# Run smoke test script
python scripts/smoke_test.py
```

**Current test results:**


```
64 passed in 17s
95% overall code coverage on app/
```

Test suite structure:

| File | Coverage |
|---|---|
| `test_circuit_breaker.py` | All 7 CB state transitions (CLOSED→OPEN, OPEN→HALF_OPEN, HALF_OPEN→CLOSED, etc.) |
| `test_retry.py` | Retryable vs non-retryable error classification, backoff, exhaustion |
| `test_groq_adapter.py` | Response parsing, 429/500 vs 401 error mapping, timeout handling |
| `test_gemini_adapter.py` | System message extraction, role mapping, response parsing |
| `test_rate_limiter.py` | Per-key and per-IP limits, independent enforcement, TTL reset |
| `test_audit.py` | Required fields, key masking, LTRIM enforcement, disabled mode |
| `test_cost_tracker.py` | Pricing math, Redis key writes, daily TTL, accumulation |
| `test_router.py` | Model mapping, CB skip, fallback triggering, all-fail scenario |
| `test_api.py` | End-to-end: happy path, fallback, 503, 429, 401, 413, /health, /admin/reload, /v1/models |

---

## 📊 Observability

Prometheus metrics are exposed at `GET /metrics` (auto-redirects to `/metrics/`).

| Metric | Type | Description |
|---|---|---|
| `gateway_request_total` | Counter | Total requests by provider and outcome |
| `gateway_request_latency_seconds` | Histogram | End-to-end latency per provider |
| `gateway_tokens_used_total` | Counter | Prompt + completion tokens by provider |
| `circuit_breaker_state` | Gauge | CB state per provider (0=CLOSED, 1=OPEN, 2=HALF_OPEN) |

Grafana dashboards are auto-provisioned from `monitoring/grafana/`. No manual datasource setup required.

---

## 📁 Project Structure

```
PolyLLM/
├── app/
│   ├── api/
│   │   ├── middleware/
│   │   │   ├── content_size.py     # Payload size limit (10 MB)
│   │   │   ├── logging.py          # Structured request/response logging
│   │   │   └── request_id.py       # X-Request-ID injection
│   │   └── routes/
│   │       ├── admin.py            # POST /admin/reload (auth required)
│   │       ├── chat.py             # POST /v1/chat/completions
│   │       ├── health.py           # GET /health
│   │       └── models.py           # GET /v1/models
│   ├── audit/logger.py             # Redis-backed audit logger (IP anonymised)
│   ├── config/
│   │   ├── loader.py               # ConfigLoader with async hot-reload lock
│   │   └── settings.py             # pydantic-settings (.env binding)
│   ├── cost/tracker.py             # Token & USD cost tracking
│   ├── models/
│   │   ├── errors.py               # GatewayError hierarchy
│   │   ├── request.py              # ChatRequest / Message (Pydantic v2)
│   │   └── response.py             # ChatResponse / GatewayMeta
│   ├── monitoring/metrics.py       # Prometheus metrics definitions
│   ├── providers/
│   │   ├── groq_adapter.py         # Groq HTTP adapter
│   │   └── gemini_adapter.py       # Gemini HTTP adapter (role mapping)
│   ├── rate_limit/limiter.py       # Dual sliding-window rate limiter
│   ├── resilience/
│   │   ├── circuit_breaker.py      # Redis-backed CB state machine
│   │   ├── retry.py                # Tenacity retry decorator factory
│   │   └── timeout.py              # Per-provider timeout config
│   ├── routing/router.py           # Fallback routing orchestrator
│   ├── utils/network.py            # get_client_ip() proxy resolver
│   ├── dependencies.py             # FastAPI dependency injectors
│   └── main.py                     # App factory + lifespan
├── tests/                          # 64-test suite (unit + integration + e2e)
├── monitoring/
│   ├── prometheus.yml              # Scrape config
│   └── grafana/                    # Dashboard provisioning
├── config.yaml                     # Runtime gateway config (hot-reloadable)
├── .env.example                    # Required environment variables template
├── Dockerfile                      # python:3.12-slim production image
├── docker-compose.yml              # Dev: Redis + Prometheus + Grafana
└── docker-compose.full.yml         # Full stack including gateway container
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Install pre-commit hooks: `pre-commit install`
4. Make changes and run tests: `pytest tests/ -v`
5. Open a pull request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
