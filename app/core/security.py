"""Security utilities - API key authentication."""
import logging
import secrets
from typing import Optional
from datetime import datetime, timedelta

from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.secret_key  
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_api_key(api_key: str) -> Optional[str]:
    """
    Verify API key and return associated role.
    
    Args:
        api_key: API key to verify
        
    Returns:
        User role if valid, None if invalid
    """
    role = settings.valid_api_keys.get(api_key)
    
    if role:
        logger.debug("Valid API key for role: %s", role)
    else:
        logger.warning("Invalid API key attempted: %s", api_key[:10])
    
    return role


def generate_api_key() -> str:
    """
    Generate a random API key.
    
    Returns:
        32-character random API key
    """
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token data if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("Invalid token: %s", e)
        return None