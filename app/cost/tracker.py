from datetime import UTC, datetime
from typing import Any

from app.monitoring.metrics import tokens_used as tokens_used_counter

COST_PER_TOKEN = {
    "groq": {
        "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},
        "llama-3.1-8b-instant": {"input": 0.0, "output": 0.0},
    },
    "gemini": {
        "gemini-1.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        "gemini-1.5-flash-8b": {"input": 0.0375 / 1_000_000, "output": 0.15 / 1_000_000},
    },
}


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = COST_PER_TOKEN.get(provider, {}).get(model, {"input": 0.0, "output": 0.0})
    return (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])


class CostTracker:
    def __init__(self, redis: Any) -> None:
        self.redis = redis

    async def record(
        self, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        cost = round(calculate_cost(provider, model, prompt_tokens, completion_tokens), 8)
        total_tokens = prompt_tokens + completion_tokens
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_key = f"cost:daily:{today}"

        pipe = self.redis.pipeline()
        pipe.incrbyfloat("cost:total", cost)
        pipe.incrbyfloat(f"cost:by_provider:{provider}", cost)
        pipe.incrbyfloat(f"cost:by_model:{model}", cost)
        pipe.incrbyfloat(daily_key, cost)
        pipe.expire(daily_key, 60 * 60 * 24 * 30)
        pipe.incrby("cost:tokens:total", total_tokens)
        await pipe.execute()

        tokens_used_counter.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
        tokens_used_counter.labels(provider=provider, model=model, type="completion").inc(
            completion_tokens
        )

        return cost
