"""FastAPI dependency injection helpers."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from math_assistant.server.database import get_db
from math_assistant.server.models.user import User
from math_assistant.server.services.auth_service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT token.

    Raises:
        HTTPException 401: If token is missing, invalid, or user not found.
    """
    from math_assistant.server.config import ServerConfig

    # We need access to the config for the secret key.
    # Import here to avoid circular imports.
    from fastapi import Request

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token — we need the app config for the secret.
    # The config is stored on app.state.config. We access it via
    # a thread-local or by importing directly.
    import os
    from math_assistant.server.config import ServerConfig as SC

    config = SC.load()

    payload = decode_access_token(token, config.auth)
    if payload is None:
        raise credentials_exception

    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user
