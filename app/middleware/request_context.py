"""Request-scoped context utilities."""

import contextvars
from uuid import uuid4

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


def generate_request_id() -> str:
    """Generate a short request correlation ID."""
    return str(uuid4())[:8]


def get_request_id() -> str | None:
    """
    Return the current request ID from async-local context.
    """
    return request_id_context.get()


def set_request_id(request_id: str) -> contextvars.Token[str | None]:
    """
    Store request ID in async-local context.

    Returns:
        Context token for later reset.
    """
    return request_id_context.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    """
    Reset request context using the provided token.
    """
    request_id_context.reset(token)
