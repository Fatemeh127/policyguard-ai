import hashlib
import json
from typing import Any, cast

from redis.asyncio import Redis

CACHE_TTL_SECONDS = 3600  # 1 hour


def make_cache_key(query: str, role: str, limit: int) -> str:
    normalized_query = query.strip().lower()
    raw_key = f"{role}:{limit}:{normalized_query}"
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    return f"llm_response_cache:{hashed}"


async def get_cached_response(
    redis: Redis,
    cache_key: str,
) -> dict[str, Any] | None:
    cached = await redis.get(cache_key)

    if cached is None:
        return None

    return cast(dict[str, Any], json.loads(cached))


async def save_cached_response(
    redis: Redis,
    cache_key: str,
    response_data: dict[str, Any],
) -> None:
    await redis.set(
        cache_key,
        json.dumps(response_data),
        ex=CACHE_TTL_SECONDS,
    )
