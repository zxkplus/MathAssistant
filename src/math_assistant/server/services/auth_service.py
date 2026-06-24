"""Authentication service: password hashing with bcrypt and JWT token management."""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from math_assistant.server.config import AuthConfig

# bcrypt rounds — 12 provides a good balance of security and performance
_BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt.

    bcrypt has a 72-byte limit on password length. Longer passwords
    are truncated to 72 bytes before hashing.
    """
    password_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    password_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed.encode("utf-8"))


def create_access_token(
    data: dict,
    config: AuthConfig,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data (must include 'sub' for the user ID).
        config: Auth configuration with secret key and algorithm.
        expires_delta: Optional custom expiry. Falls back to config default.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)


def decode_access_token(token: str, config: AuthConfig) -> dict | None:
    """Decode and validate a JWT access token.

    Args:
        token: JWT string to decode.
        config: Auth configuration with secret key and algorithm.

    Returns:
        Decoded payload dict, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token, config.secret_key, algorithms=[config.algorithm]
        )
        return payload
    except JWTError:
        return None
