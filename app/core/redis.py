# app/core/redis.py
import logging

import redis
from redis import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        _ping(_redis_client)

    return _redis_client


def _ping(client: Redis) -> None:
    try:
        client.ping()
        logger.info("Redis connection established: %s", settings.redis_url)
    except redis.ConnectionError:
        logger.warning("Redis ping failed — will retry on first use")
