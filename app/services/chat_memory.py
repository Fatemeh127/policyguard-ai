"""
Chat memory management utilities for conversational context persistence.
"""

import inspect
import json
import logging
from collections.abc import Awaitable
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _maybe_await_bool(value: Awaitable[bool] | bool) -> bool:
    """Return bool from either an awaitable bool or direct bool."""
    if inspect.isawaitable(value):
        return await value

    return value


async def _maybe_await_int(value: Awaitable[int] | int) -> int:
    """Return int from either an awaitable int or direct int."""
    if inspect.isawaitable(value):
        return await value

    return value


def _key(session_id: str) -> str:
    """Build Redis key for chat session."""

    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string")

    return f"chat:{session_id}"


async def get_chat_history(
    session_id: str,
    redis: Redis,
) -> list[dict[str, Any]]:
    """Retrieve chat history for a session."""

    try:
        raw_data = await redis.get(_key(session_id))

    except Exception:
        logger.exception("Redis GET failed for session %s", session_id)
        return []

    if raw_data is None:
        return []

    data = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data

    try:
        messages = json.loads(data)

        if not isinstance(messages, list):
            logger.warning("Unexpected Redis data type for session %s", session_id)
            return []

        return messages

    except json.JSONDecodeError:
        logger.warning("Corrupt JSON in Redis for session %s", session_id)
        return []


async def save_chat_history(
    session_id: str,
    messages: list[dict[str, Any]],
    redis: Redis,
) -> None:
    """Persist chat history for a session, capping at max configured messages."""

    if len(messages) > settings.max_messages:
        messages = messages[-settings.max_messages :]

    try:
        payload = json.dumps(messages)

    except (TypeError, ValueError):
        logger.exception("Failed to serialize messages for session %s", session_id)
        raise

    try:
        result = redis.setex(
            _key(session_id),
            settings.chat_ttl,
            payload,
        )

        await _maybe_await_bool(result)

    except Exception:
        logger.exception("Redis SETEX failed for session %s", session_id)
        raise


async def delete_chat_history(
    session_id: str,
    redis: Redis,
) -> None:
    """Delete chat history for a session."""

    try:
        result = redis.delete(_key(session_id))

        await _maybe_await_int(result)

    except Exception:
        logger.exception("Redis DELETE failed for session %s", session_id)
        raise
