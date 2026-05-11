import json
from app.core.redis import get_redis_client

redis_client = get_redis_client()

CHAT_TTL = 60 * 60 * 24  # 24h


def _key(session_id: str) -> str:
    return f"chat:{session_id}"


def get_chat_history(session_id: str):
    data = redis_client.get(_key(session_id))

    if not data:
        return []

    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return []


def save_chat_history(session_id: str, messages: list):
    redis_client.setex(
        _key(session_id),
        CHAT_TTL,
        json.dumps(messages)
    )