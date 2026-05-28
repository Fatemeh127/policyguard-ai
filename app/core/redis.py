"""
Redis connection management utilities for PolicyGuard AI.
"""

import logging
from collections.abc import Awaitable
from functools import lru_cache
from typing import cast

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis_client() -> Redis:
    """
    Return a shared async Redis client instance.
    """

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
    """
    Verify Redis connectivity.
    """

    try:
        await cast(Awaitable[bool], client.ping())

        logger.info("Redis ping successful")

        return True

    except redis.ConnectionError:
        logger.warning("Redis ping failed")

        return False


async def close_redis_client() -> None:
    """
    Gracefully close Redis connections.
    """

    client = get_redis_client()

    await cast(Awaitable[None], client.close())

    logger.info("Redis client closed")
