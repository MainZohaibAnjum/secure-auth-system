import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

# Reads the "Authorization: Bearer <token>" header from each request
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Guard for protected routes: returns the logged-in user, or stops with 401."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. No token sent at all
    if credentials is None:
        raise unauthorized

    # 2. Check the token: real signature? not expired? right type?
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized

    # 3. Does this user still exist and is the account active?
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized

    return user
