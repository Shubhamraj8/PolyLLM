# PolyLLM Gateway — Utility Scripts

This directory contains utility and verification scripts for the PolyLLM Gateway.

## `smoke_test.py`

A standalone Python script that uses the official `openai` Python SDK to verify that the PolyLLM Gateway server is operational and compatible with standard OpenAI SDK calls.

### Prerequisites

Install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

### Running the Smoke Test

Ensure the PolyLLM Gateway server is running locally:
```bash
uvicorn app.main:app --reload --port 8000
```

Then execute the smoke test script:
```bash
python scripts/smoke_test.py
```

### Custom Options

You can specify custom gateway URL and API key options:

```bash
python scripts/smoke_test.py --url http://localhost:8000/v1 --key your-secret-gateway-key
```

Or set environment variables:
```bash
export GATEWAY_URL=http://localhost:8000/v1
export GATEWAY_API_KEY=your-secret-gateway-key
python scripts/smoke_test.py
```

### What It Tests

1. **Non-streaming Chat Completion**: Sends a standard `client.chat.completions.create()` request, verifies response ID, choices, usage tokens, and gateway metadata (`x_gateway`).
2. **Streaming SSE Chat Completion**: Sends a `stream=True` completion request and prints tokens live as they arrive via Server-Sent Events (SSE).
3. **Error Diagnostics**: Gracefully catches `APIConnectionError` or `APIError` if the gateway is offline or misconfigured.
