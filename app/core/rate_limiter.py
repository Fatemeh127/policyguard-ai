"""Rate limiting using Redis and SlowAPI."""

import logging

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)


# Key function
def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    """
    user_id = request.headers.get("X-User-ID")

    if user_id:
        return f"user:{user_id}"

    return f"ip:{get_remote_address(request)}"


# Rate limiter
limiter = Limiter(
    key_func=get_identifier,
    storage_uri=getattr(settings, "redis_url", None),
    strategy="fixed-window",
    enabled=True,
)


# Handler
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> HTTPException:
    """
    Handle rate limit exceeded errors safely.
    """

    retry_after = getattr(exc, "retry_after", 0)

    logger.warning(
        "Rate limit exceeded | identifier=%s | path=%s",
        get_identifier(request),
        request.url.path,
    )

    raise HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Try again in {retry_after} seconds.",
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )
