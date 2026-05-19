"""FastAPI dependencies for authentication."""

import logging
from typing import Optional
from fastapi import Header, HTTPException, status

from app.core.security import verify_api_key
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_current_role(
    x_api_key: Optional[str] = Header(None, description="API key for authentication")
) -> str:
    """
    Dependency to verify API key and get user role.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        User role (employee/manager/admin)

    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Skip auth if disabled (for development)
    if not settings.api_auth_enabled:
        logger.debug("API auth disabled, allowing request")
        return "employee"  # Default role when auth disabled

    # Check if API key provided
    if not x_api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key
    role = verify_api_key(x_api_key)

    if not role:
        logger.warning("Invalid API key: %s", x_api_key[:10])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("Authenticated request with role: %s", role)
    return role
