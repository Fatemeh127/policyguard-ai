import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


def _key(session_id: str) -> str:
    if not session_id or not session_id.strip():
        raise ValueError("session_id must be a non-empty string")
    return f"chat:{session_id}"


async def get_chat_history(
    session_id: str,
    redis: Redis,
) -> list[dict[str, Any]]:
    """Retrieve chat history for a session. Returns [] if not found or invalid."""
    try:
        data: str | None = await redis.get(_key(session_id))
    except Exception:
        logger.exception("Redis GET failed for session %s", session_id)
        return []

    if not data:
        return []

    try:
        messages = json.loads(data)
        if not isinstance(messages, list):
            logger.warning("Unexpected data type in Redis for session %s", session_id)
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
    """Persist chat history for a session, capping at MAX_MESSAGES."""
    if len(messages) > settings.max_messages:
        messages = messages[-settings.max_messages :]

    try:
        payload = json.dumps(messages)
    except (TypeError, ValueError):
        logger.exception("Failed to serialize messages for session %s", session_id)
        raise

    try:
        await redis.setex(_key(session_id), settings.chat_ttl, payload)
    except Exception:
        logger.exception("Redis SETEX failed for session %s", session_id)
        raise


async def delete_chat_history(
    session_id: str,
    redis: Redis,
) -> None:
    """Delete chat history for a session."""
    try:
        await redis.delete(_key(session_id))
    except Exception:
        logger.exception("Redis DELETE failed for session %s", session_id)
        raise
