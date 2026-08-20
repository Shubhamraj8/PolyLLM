# PolyLLM Gateway

![Build Status](https://github.com/Shubhamraj8/PolyLLM/workflows/Test%20%26%20Lint/badge.svg)

> High-performance, resilient OpenAI-compatible LLM Gateway featuring automatic fallback routing, circuit breakers, rate limiting, cost tracking, and full Prometheus/Grafana observability.

---

## Architecture

```text
 Client (OpenAI SDK / HTTP)
            │
            ▼
┌─────────────────────────┐
│     FastAPI Gateway     │
│                         │
│  [ Rate Limiter ]       │ ◄─── Redis (Sliding Window Log)
│                         │
│  [ Router ]             │ ◄─── config.yaml (Fallback Chains)
│    ├─ Circuit Breaker   │ ◄─── Redis (Shared CB State)
│    ├─ Retry Engine      │ (Exponential Backoff + Jitter)
│    ├─ Groq Adapter      │ ───► Groq API (Primary)
│    └─ Gemini Adapter    │ ───► Gemini API (Fallback)
│                         │
│  [ Cost Tracker ]       │ ───► Redis (Usage & USD tracking)
│  [ Audit Logger ]       │ ───► Redis (Circular Audit Log)
│  [ Metrics Exporter ]   │ ───► Prometheus (/metrics)
└─────────────────────────┘
```

---

## Features

- 🔄 **Fallback Routing**: Automatically redirects failed upstream calls down a configured chain (e.g. Groq ──► Gemini).
- ⚡ **Circuit Breaker**: Distributed state machine (CLOSED, OPEN, HALF_OPEN) backed by Redis to prevent hammering failing providers.
- ⏱️ **Tenacity Retry Engine**: Automatic exponential backoff retries for transient errors (429, 500s, timeouts).
- 🛡️ **Rate Limiting**: Dual-layer sliding window rate limiter (per API key + per IP).
- 📊 **Cost & Usage Tracker**: Tracks token usage and calculates estimated USD cost per request.
- 📜 **Audit Logger**: Asynchronous Redis-backed audit logging with automatic API key masking and bounded storage.
- 📈 **Observability**: Exposes Prometheus metrics and includes pre-built Grafana dashboards.
- 🔄 **Config Hot-Reload**: Runtime configuration reloading via `POST /admin/reload` without restarting the gateway.

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | Python 3.12, FastAPI, Uvicorn |
| Storage & State | Redis 7.4 |
| Resilience | Tenacity, Asyncio Locks |
| Metrics & Dashboards | Prometheus, Grafana |
| Provider Integration | HTTPX AsyncClient (Groq & Gemini APIs) |
| Testing | Pytest, Fakeredis, RESPX |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Shubhamraj8/PolyLLM.git
   cd PolyLLM
   ```

2. **Set up Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and insert your `GROQ_API_KEY` and `GEMINI_API_KEY`.

3. **Start Supporting Services (Redis + Prometheus + Grafana):**
   ```bash
   docker-compose up -d
   ```

4. **Run Gateway Service Locally:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   uvicorn app.main:app --reload --port 8000
   ```

---

## Running Full Stack in Docker

To spin up the gateway alongside all supporting services in Docker:

```bash
docker-compose -f docker-compose.full.yml up --build -d
```

- Gateway API: `http://localhost:8000`
- Prometheus UI: `http://localhost:9090`
- Grafana Dashboards: `http://localhost:3000` (Login: `admin` / `admin`)

---

## Example Usage

### Send Chat Completion Request

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain circuit breakers in 2 sentences."}
    ]
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Hot-Reload Configuration

```bash
curl -X POST http://localhost:8000/admin/reload
```

---

## Running Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## License

MIT License
