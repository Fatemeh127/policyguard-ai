"""Security utilities for API key authentication."""

import logging
import secrets

from app.core.config import settings
from app.core.types import Role

logger = logging.getLogger(__name__)


def verify_api_key(api_key: str) -> Role | None:
    """Verify an API key and return the associated role if valid."""

    for stored_key, role in settings.api_key_role_map.items():
        if secrets.compare_digest(api_key, stored_key):
            logger.debug("Valid API key for role: %s", role)
            return role

    logger.warning("Invalid API key attempted")
    return None


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)