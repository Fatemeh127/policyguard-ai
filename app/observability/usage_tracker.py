"""Usage tracking with Redis (production-safe version)."""

import logging
import math
from datetime import datetime
from functools import cached_property
from typing import Any, cast

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

    # Redis connection
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

    # Helpers (type-safe)
    def _safe_int(self, value: Any) -> int:
        try:
            if value is None:
                return 0
            if isinstance(value, int):
                return value
            return int(value)
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            if isinstance(value, float):
                return value
            return float(value)
        except Exception:
            return 0.0

    def _normalize_endpoint(self, endpoint: str) -> str:
        return endpoint.strip("/").lower()

    # Tracking
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

            # latency sorted set (score = latency)
            pipe.zadd("metrics:latency", {ts: float(latency_ms)})

            # trim old samples safely
            start = 0
            end = -(self.LATENCY_WINDOW + 1)
            pipe.zremrangebyrank("metrics:latency", start, end)

            pipe.execute()

        except Exception:
            logger.exception("track_request failed — metrics may be incomplete")

    # Stats helpers
    def _percentile(self, data: list[float], pct: float) -> float:
        if not data:
            return 0.0

        idx = min(math.ceil(len(data) * pct) - 1, len(data) - 1)
        return data[idx]

    # Metrics API
    def get_metrics(self) -> dict[str, Any]:
        """Return observability metrics."""
        if not self.redis:
            return {"error": "redis unavailable"}

        try:
            r = self.redis

            # Safe Redis reads
            total_requests = self._safe_int(r.get("metrics:total_requests"))
            total_tokens = self._safe_int(r.get("metrics:total_tokens"))
            embedding_tokens = self._safe_int(r.get("metrics:embedding_tokens"))
            prompt_tokens = self._safe_int(r.get("metrics:prompt_tokens"))
            completion_tokens = self._safe_int(r.get("metrics:completion_tokens"))

            # Latency stats
            raw: list[tuple[str, float]] = cast(
                list[tuple[str, float]],
                r.zrange("metrics:latency", 0, -1, withscores=True),
            )

            latencies = sorted(self._safe_float(score) for _, score in raw)

            n = len(latencies)
            avg_latency = sum(latencies) / n if n else 0.0

            p95 = self._percentile(latencies, 0.95)
            p99 = self._percentile(latencies, 0.99)

            # Cost calculation
            embedding_cost = (embedding_tokens / 1_000_000) * self.EMBEDDING_COST_PER_M
            input_cost = (prompt_tokens / 1_000_000) * self.INPUT_COST_PER_M
            output_cost = (completion_tokens / 1_000_000) * self.OUTPUT_COST_PER_M

            total_cost = embedding_cost + input_cost + output_cost

            # Response
            return {
                "usage": {
                    "total_requests": total_requests,
                    "total_tokens": total_tokens,
                    "embedding_tokens": embedding_tokens,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
                "cost": {
                    "total_cost": round(total_cost, 6),
                    "avg_cost_per_request": (
                        round(total_cost / total_requests, 6) if total_requests else 0.0
                    ),
                    "embedding_cost": round(embedding_cost, 6),
                    "input_cost": round(input_cost, 6),
                    "output_cost": round(output_cost, 6),
                },
                "performance": {
                    "avg_latency_ms": round(avg_latency, 2),
                    "p95_latency_ms": round(p95, 2),
                    "p99_latency_ms": round(p99, 2),
                    "samples": n,
                },
            }

        except Exception:
            logger.exception("get_metrics failed")
            return {"error": "metrics retrieval failed"}


# Factory
def get_usage_tracker() -> UsageTracker:
    return UsageTracker()
