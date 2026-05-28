"""Rate limiting utilities using Redis and SlowAPI."""

import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_identifier(request: Request) -> str:
    """
    Return the identifier used for rate limiting.

    Prefer authenticated identity when available.
    Fall back to client IP address.
    """

    user_id = getattr(request.state, "user_id", None)

    if user_id:
        return f"user:{user_id}"

    role = getattr(request.state, "role", None)

    if role:
        return f"role:{role}:{get_remote_address(request)}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_identifier,
    storage_uri=settings.redis_url,
    strategy=settings.rate_limit_strategy,
    enabled=settings.rate_limit_enabled,
)


async def custom_rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """
    Return a safe structured response when rate limit is exceeded.
    """

    retry_after = int(getattr(exc, "retry_after", 0) or 0)

    logger.warning(
        "Rate limit exceeded | identifier=%s | path=%s",
        get_identifier(request),
        request.url.path,
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )
