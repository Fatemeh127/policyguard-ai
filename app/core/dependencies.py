"""FastAPI dependencies for API-key authentication."""

import logging
from typing import Annotated, Literal

from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)

Role = Literal["employee", "manager", "admin"]


def _auth_error(detail: str) -> HTTPException:
    """Build a standard API-key authentication error."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "ApiKey"},
    )


async def get_current_role(
    x_api_key: Annotated[
        str | None,
        Header(
            alias="X-API-Key",
            description="API key for authentication",
        ),
    ] = None,
) -> Role:
    """
    Verify the API key from the X-API-Key header and return the caller role.

    Returns:
        Role associated with the API key: employee, manager, or admin.

    Raises:
        HTTPException: If authentication is enabled and the API key is missing or invalid.
    """

    if not settings.api_auth_enabled:
        if settings.environment == "production":
            logger.error("API authentication is disabled in production")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server authentication configuration error",
            )

        logger.warning("API authentication is disabled; using default development role")
        return "employee"

    if not x_api_key:
        logger.warning("Missing API key in request")
        raise _auth_error("API key required. Provide X-API-Key header.")

    role = verify_api_key(x_api_key)

    if role is None:
        logger.warning("Invalid API key attempted")
        raise _auth_error("Invalid API key")

    logger.debug("Authenticated request with role: %s", role)
    return role  
