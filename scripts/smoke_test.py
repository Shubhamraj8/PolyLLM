#!/usr/bin/env python3
"""
PolyLLM Gateway — OpenAI SDK Smoke Test Script

This script verifies end-to-end OpenAI SDK compatibility against a running
PolyLLM Gateway instance. It tests both non-streaming and streaming completions.

Usage:
    python scripts/smoke_test.py [--url URL] [--key KEY]
"""

import argparse
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="PolyLLM Gateway OpenAI SDK Smoke Test")
    parser.add_argument(
        "--url",
        default=os.getenv("GATEWAY_URL", "http://localhost:8000/v1"),
        help="Base URL of the PolyLLM Gateway (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--key",
        default=os.getenv("GATEWAY_API_KEY", "dev-key"),
        help="Gateway API Key (default: dev-key or GATEWAY_API_KEY env var)",
    )
    args = parser.parse_args()

    try:
        from openai import APIConnectionError, APIError, OpenAI
    except ImportError:
        print("[ERROR] The 'openai' package is not installed.")
        print("Please run: pip install -r requirements-dev.txt")
        return 1

    gateway_url = args.url.rstrip("/")
    api_key = args.key

    print(f"Connecting to PolyLLM Gateway at: {gateway_url}")
    print(f"Using API Key: {api_key[:8]}...\n")

    client = OpenAI(
        base_url=gateway_url,
        api_key=api_key,
        default_headers={"X-API-Key": api_key},
    )

    # ── Test 1: Non-Streaming Chat Completion ─────────────────────────────────
    print("=" * 60)
    print("1. Testing Non-Streaming Chat Completion")
    print("=" * 60)

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {
                    "role": "user",
                    "content": "What is the primary function of an LLM API Gateway?",
                },
            ],
            temperature=0.7,
            max_tokens=150,
        )

        content = response.choices[0].message.content if response.choices else "No choices returned"
        print(f"\nResponse ID:   {response.id}")
        print(f"Model Used:    {response.model}")
        print(f"Content:\n{content}\n")

        if response.usage:
            print(f"Prompt Tokens:     {response.usage.prompt_tokens}")
            print(f"Completion Tokens: {response.usage.completion_tokens}")
            print(f"Total Tokens:      {response.usage.total_tokens}")

        # Check for x_gateway metadata in response
        extra_fields = getattr(response, "__pydantic_extra__", {}) or getattr(
            response, "model_extra", {}
        )
        x_meta = extra_fields.get("x_gateway") if extra_fields else None
        if x_meta:
            print(f"x_gateway Metadata: {x_meta}")

        print("\n[SUCCESS] Non-streaming chat completion test passed!\n")

    except APIConnectionError as exc:
        print(f"\n[ERROR] Connection failed: Could not reach gateway at {gateway_url}")
        print(f"Details: {exc}")
        print("\nPlease ensure the gateway server is running:")
        print("    uvicorn app.main:app --reload --port 8000")
        return 1
    except APIError as exc:
        print(f"\n[ERROR] Gateway returned API error: {exc}")
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}")
        return 1

    # ── Test 2: Streaming Chat Completion ─────────────────────────────────────
    print("=" * 60)
    print("2. Testing Streaming SSE Chat Completion")
    print("=" * 60)
    print("\nStreaming response: ", end="", flush=True)

    try:
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Tell me a short one-line joke about computers."}
            ],
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

        print("\n\n[SUCCESS] Streaming SSE chat completion test passed!\n")

    except APIError as exc:
        print(f"\n[ERROR] Gateway returned API error during stream: {exc}")
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Streaming test error: {exc}")
        return 1

    print("=" * 60)
    print("ALL SMOKE TESTS PASSED SUCCESSFULLY! ✨")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
