import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_2fa_challenge_token,
    create_access_token,
    decode_2fa_challenge_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    TokenResponse,
    TwoFactorVerifyRequest,
    UserResponse,
)
from app.services.refresh_sessions import (
    InvalidRefreshToken,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)
from app.services.totp import verify_totp_code

router = APIRouter(prefix="/auth", tags=["auth"])

# Used when the email doesn't exist, so a wrong email takes as long as a wrong password
_DUMMY_HASH = hash_password("not-a-real-password")

# The refresh token lives in this cookie, sent by the browser only to /auth/... routes
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_signup)
def signup(data: SignupRequest, request: Request, db: Session = Depends(get_db)) -> User:

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


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.rate_limit_login)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    # 1. Find the user by email
    user = db.scalar(select(User).where(User.email == data.email))

    # 2. Always check a password, even for unknown emails (same timing either way)
    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = verify_password(data.password, password_hash)

    # 3. Is the account currently locked from too many wrong passwords?
    now = datetime.now(timezone.utc)
    locked = user is not None and _is_locked(user, now)

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

    # 5. If the hash uses older settings, quietly upgrade it now that we know the password
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)

    # 6. 2FA is on: the password alone isn't enough. Hand out a short-lived challenge
    #    instead. The failure counter is NOT reset yet, so wrong codes still count.
    if user.totp_enabled:
        db.commit()
        return LoginResponse(
            requires_2fa=True, challenge_token=create_2fa_challenge_token(user.id)
        )

    # 7. No 2FA: the user is fully logged in
    return _complete_login(db, user, request, response)


@router.post("/2fa/verify", response_model=LoginResponse)
@limiter.limit(settings.rate_limit_login)
def verify_2fa(
    data: TwoFactorVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Second login step: swap the challenge token + a 6-digit code for real tokens."""
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired code")

    # 1. The challenge token proves the password step passed (in the last few minutes)
    try:
        payload = decode_2fa_challenge_token(data.challenge_token)
        user = db.get(User, uuid.UUID(payload["sub"]))
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized

    now = datetime.now(timezone.utc)
    if user is None or not user.is_active or not user.totp_enabled or _is_locked(user, now):
        raise unauthorized

    # 2. Wrong codes count toward the same lockout as wrong passwords
    if not verify_totp_code(user, data.code):
        _record_failed_login(user, now)
        db.commit()
        raise unauthorized

    return _complete_login(db, user, request, response)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_refresh)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    """Swap the refresh cookie for a new access token (and a new refresh cookie)."""
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise unauthorized

    try:
        new_token, session = rotate_refresh_session(
            db, token, request.headers.get("user-agent"), _client_ip(request)
        )
    except InvalidRefreshToken:
        raise unauthorized

    # The account may have been disabled since the user logged in
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        db.rollback()
        raise unauthorized

    db.commit()
    _set_refresh_cookie(response, new_token)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    """End this device's session and remove the refresh cookie."""
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token:
        revoke_refresh_session(db, token)
        db.commit()
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user. Only works with a valid access token."""
    return current_user


def _complete_login(
    db: Session, user: User, request: Request, response: Response
) -> LoginResponse:
    """Every check passed: reset the failure counter, start a session, hand out tokens."""
    user.failed_login_count = 0
    user.locked_until = None

    refresh_token, _ = create_refresh_session(
        db, user.id, request.headers.get("user-agent"), _client_ip(request)
    )
    db.commit()

    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(access_token=create_access_token(user.id))


def _is_locked(user: User, now: datetime) -> bool:
    return user.locked_until is not None and user.locked_until > now


def _record_failed_login(user: User, now: datetime) -> None:
    """Count a wrong password or code; lock the account once the limit is reached."""
    user.failed_login_count += 1
    if user.failed_login_count >= settings.max_failed_login_attempts:
        user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
        user.failed_login_count = 0


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        secure=settings.cookie_secure,  # HTTPS-only in production
        httponly=True,  # JavaScript can't read it, so XSS can't steal it
        samesite="strict",  # other websites can't make the browser send it
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
