# PolyLLM Gateway — API Documentation & Postman Collection

This directory contains official API documentation and pre-configured Postman Collections for testing the PolyLLM Gateway.

## Postman Collection (`PolyLLM.postman_collection.json`)

The `PolyLLM.postman_collection.json` file is a pre-configured [Postman Collection v2.1.0](https://schema.getpostman.com/json/collection/v2.1.0/collection.json) that allows developers, QA engineers, and interviewers to test all gateway endpoints instantly.

### How to Import

#### In Postman:
1. Open Postman.
2. Click **Import** in the top-left corner.
3. Select or drop `docs/PolyLLM.postman_collection.json`.
4. The collection **"PolyLLM Gateway API"** will appear in your sidebar.

#### In Bruno or Hoppscotch:
1. Open your API client (Bruno / Hoppscotch / Insomnia).
2. Choose **Import Collection** -> **Postman Collection v2.1**.
3. Select `docs/PolyLLM.postman_collection.json`.

---

### Collection Variables

The collection includes pre-defined variables:

| Variable | Default Value | Description |
|---|---|---|
| `{{base_url}}` | `http://localhost:8000` | Gateway base server URL |
| `{{api_key}}` | `dev-key` | Gateway authentication API Key (`X-API-Key`) |

You can override these variables in Postman Environment Settings or within the collection variables tab.

---

### Included Endpoints

- **Chat Completions**:
  - `POST /v1/chat/completions` — Standard OpenAI-compatible non-streaming chat completion (`model: gpt-4`)
  - `POST /v1/chat/completions` (Streaming) — Token-by-token Server-Sent Events (SSE) stream (`stream: true`)
  - `POST /v1/chat/completions` (Gemini) — Direct request to `gemini-1.5-flash` model alias
- **Models**:
  - `GET /v1/models` — List all supported LLM models
- **Health & Monitoring**:
  - `GET /health` — Operational state, Redis connection, and circuit breaker status
  - `GET /metrics` — Prometheus metrics feed
- **Admin**:
  - `POST /admin/reload` — Runtime configuration hot-reload (`config.yaml`)
