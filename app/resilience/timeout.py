"""
Per-provider httpx timeout configuration.

Values match the design spec:
  groq:   connect=5s, read=10s, write=5s, pool=2s
  gemini: connect=5s, read=15s, write=5s, pool=2s
"""

import httpx

PROVIDER_TIMEOUTS: dict[str, httpx.Timeout] = {
    "groq": httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=2.0),
    "gemini": httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=2.0),
}


def get_timeout(provider_name: str) -> httpx.Timeout:
    """
    Return the httpx.Timeout for a given provider.
    Falls back to a safe 10s read timeout if the provider is unknown.
    """
    return PROVIDER_TIMEOUTS.get(
        provider_name,
        httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=2.0),
    )
