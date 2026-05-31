"""
Redis connection management utilities for PolicyGuard AI.
"""

import inspect
import logging
from collections.abc import Awaitable
from functools import lru_cache

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _maybe_await_bool(value: Awaitable[bool] | bool) -> bool:
    """Return bool from either an awaitable bool or a direct bool."""
    if inspect.isawaitable(value):
        return await value
    return value


async def _maybe_await_none(value: Awaitable[None] | None) -> None:
    """Handle either an awaitable None or direct None."""
    if inspect.isawaitable(value):
        await value


@lru_cache
def get_redis_client() -> Redis:
    """Return a shared async Redis client instance."""

    client: Redis = redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )

    logger.info("Redis client initialized")

    return client


async def ping_redis(client: Redis) -> bool:
    """Verify Redis connectivity."""

    try:
        result = client.ping()
        await _maybe_await_bool(result)

        logger.info("Redis ping successful")
        return True

    except redis.ConnectionError:
        logger.warning("Redis ping failed")
        return False


async def close_redis_client() -> None:
    """Gracefully close Redis connections."""

    client = get_redis_client()

    result = client.close()
    await _maybe_await_none(result)

    logger.info("Redis client closed")
