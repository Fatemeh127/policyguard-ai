"""Security utilities for API key authentication, password hashing, and JWT handling."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.types import Role

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return str(pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bool(pwd_context.verify(plain_password, hashed_password))


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""

    to_encode = data.copy()

    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )

    to_encode.update({"exp": expire})

    return str(
        jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT access token."""

    try:
        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.jwt_algorithm],
            ),
        )

    except JWTError:
        logger.warning("Invalid or expired token")
        return None
