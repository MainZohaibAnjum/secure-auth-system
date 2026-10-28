from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Used when the email doesn't exist, so a wrong email takes as long as a wrong password
_DUMMY_HASH = hash_password("not-a-real-password")


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Session = Depends(get_db)) -> User:
    # 1. Is this email already taken?
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    # 2. Create the user with a HASHED password (never the real one)
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)

    # 3. Save. The unique index on email also protects us if two signups race.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    db.refresh(user)  # load values the database filled in, like created_at
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    # 1. Find the user by email
    user = db.scalar(select(User).where(User.email == data.email))

    # 2. Always check a password, even for unknown emails (same timing either way)
    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = verify_password(data.password, password_hash)

    # 3. Is the account currently locked from too many wrong passwords?
    now = datetime.now(timezone.utc)
    locked = user is not None and user.locked_until is not None and user.locked_until > now

    # 4. One message for every failure, so attackers can't tell which part was wrong
    if user is None or locked or not password_ok or not user.is_active:
        if user is not None and not locked and not password_ok:
            _record_failed_login(user, now)
            db.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Success: clear the failure counter and any old lock
    user.failed_login_count = 0
    user.locked_until = None

    # 6. If the hash uses older settings, quietly upgrade it now that we know the password
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)

    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user. Only works with a valid access token."""
    return current_user


def _record_failed_login(user: User, now: datetime) -> None:
    """Count a wrong password; lock the account once the limit is reached."""
    user.failed_login_count += 1
    if user.failed_login_count >= settings.max_failed_login_attempts:
        user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
        user.failed_login_count = 0
