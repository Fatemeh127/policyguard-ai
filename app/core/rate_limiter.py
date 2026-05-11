"""Rate limiting using Redis and SlowAPI."""
import logging
from typing import Callable
from functools import wraps

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from redis import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


# Custom key function - use IP address or user identifier
def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    
    Priority:
    1. User ID from auth header (if implemented)
    2. Client IP address
    
    Args:
        request: FastAPI request object
        
    Returns:
        Unique identifier string
    """
    # Check for user ID in headers 
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Initialize rate limiter
limiter = Limiter(
    key_func=get_identifier,
    storage_uri=settings.redis_url,
    strategy="fixed-window",  
    enabled=True
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    
    Returns user-friendly error message with retry-after header.
    """
    logger.warning(
        "Rate limit exceeded | identifier=%s | path=%s",
        get_identifier(request),
        request.url.path
    )
    
    raise HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Try again in {exc.retry_after} seconds.",
            "retry_after": exc.retry_after
        },
        headers={"Retry-After": str(exc.retry_after)}
    )