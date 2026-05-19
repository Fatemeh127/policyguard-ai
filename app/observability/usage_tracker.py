"""Usage tracking with Redis."""

import logging
import math
from datetime import datetime
from functools import cached_property
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class UsageTracker:
    """Track API usage, costs, and performance metrics using Redis."""

    # Pricing per million tokens — override via settings
    EMBEDDING_COST_PER_M: float = getattr(settings, "cost_embedding_per_m", 0.02)
    INPUT_COST_PER_M: float = getattr(settings, "cost_input_per_m", 0.50)
    OUTPUT_COST_PER_M: float = getattr(settings, "cost_output_per_m", 1.50)

    LATENCY_WINDOW = 10_000  # keep last N latency samples

    @cached_property
    def redis(self) -> redis.Redis | None:
        """Lazy Redis connection — created on first use."""
        try:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            logger.info("UsageTracker connected to Redis")
            return client
        except Exception as e:
            logger.warning("Redis unavailable: %s", e)
            return None

    def _normalize_endpoint(self, endpoint: str) -> str:
        return endpoint.strip("/").lower()

    def track_request(
        self,
        endpoint: str,
        embedding_tokens: int = 0,
        llm_prompt_tokens: int = 0,
        llm_completion_tokens: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """Track request metrics."""
        if not self.redis:
            return

        endpoint = self._normalize_endpoint(endpoint)
        total_tokens = embedding_tokens + llm_prompt_tokens + llm_completion_tokens
        ts = str(datetime.now().timestamp())

        try:
            pipe = self.redis.pipeline()

            pipe.incr("metrics:total_requests")
            pipe.incr(f"metrics:endpoint:{endpoint}")

            pipe.incrby("metrics:total_tokens", total_tokens)
            pipe.incrby("metrics:embedding_tokens", embedding_tokens)
            pipe.incrby("metrics:prompt_tokens", llm_prompt_tokens)
            pipe.incrby("metrics:completion_tokens", llm_completion_tokens)

            # member = timestamp (unique key), score = latency for sorting
            pipe.zadd("metrics:latency", {ts: latency_ms})
            pipe.zremrangebyrank("metrics:latency", 0, -(self.LATENCY_WINDOW + 1))

            pipe.execute()

        except Exception:
            logger.exception("track_request failed — metrics may be incomplete")
            # Optionally: self.redis.incr("metrics:tracking_errors")

    def _percentile(self, sorted_data: list[float], pct: float) -> float:
        """Safe percentile from a pre-sorted list."""
        if not sorted_data:
            return 0.0
        idx = min(math.ceil(len(sorted_data) * pct) - 1, len(sorted_data) - 1)
        return sorted_data[idx]

    def get_metrics(self) -> dict[str, Any]:
        """Return observability metrics."""
        if not self.redis:
            return {"error": "redis unavailable"}

        try:
            r = self.redis

            total_requests = int(r.get("metrics:total_requests") or 0)
            total_tokens = int(r.get("metrics:total_tokens") or 0)
            embedding_tokens = int(r.get("metrics:embedding_tokens") or 0)
            prompt_tokens = int(r.get("metrics:prompt_tokens") or 0)
            completion_tokens = int(r.get("metrics:completion_tokens") or 0)

            # Correct: extract scores from (member, score) tuples
            raw = r.zrange("metrics:latency", 0, -1, withscores=True)
            latencies = sorted(score for _, score in raw)

            n = len(latencies)
            avg_latency = sum(latencies) / n if n else 0.0

            embedding_cost = embedding_tokens / 1_000_000 * self.EMBEDDING_COST_PER_M
            input_cost = prompt_tokens / 1_000_000 * self.INPUT_COST_PER_M
            output_cost = completion_tokens / 1_000_000 * self.OUTPUT_COST_PER_M
            total_cost = embedding_cost + input_cost + output_cost

            return {
                "usage": {
                    "total_requests": total_requests,
                    "total_tokens": total_tokens,
                    "embedding_tokens": embedding_tokens,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
                "cost": {
                    "total_cost": round(total_cost, 4),
                    "avg_cost_per_request": (
                        round(total_cost / total_requests, 4) if total_requests else 0
                    ),
                    "embedding_cost": round(embedding_cost, 4),
                    "input_cost": round(input_cost, 4),
                    "output_cost": round(output_cost, 4),
                },
                "performance": {
                    "avg_latency_ms": round(avg_latency, 2),
                    "p95_latency_ms": round(self._percentile(latencies, 0.95), 2),
                    "p99_latency_ms": round(self._percentile(latencies, 0.99), 2),
                    "samples": n,
                },
            }

        except Exception:
            logger.exception("get_metrics failed")
            return {"error": "metrics retrieval failed"}


# Lazy — no connection on import; instantiate where needed via DI
def get_usage_tracker() -> UsageTracker:
    return UsageTracker()
