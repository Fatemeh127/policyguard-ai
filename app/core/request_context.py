"""Request context tracking."""

import contextvars
from uuid import uuid4

# Context variable for request ID
request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """
    Get current request ID.

    Returns:
        Request ID or generates new one
    """
    request_id = request_id_context.get()
    if request_id is None:
        request_id = str(uuid4())[:8]
        request_id_context.set(request_id)
    return request_id_context.get()


def set_request_id(request_id: str) -> None:
    """
    Set request ID for current context.

    Args:
        request_id: Request ID to set
    """
    request_id_context.set(request_id)
