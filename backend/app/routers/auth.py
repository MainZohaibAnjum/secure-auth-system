from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.db.session import get_db
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

    # 3. One message for every failure, so attackers can't tell which part was wrong
    if user is None or not password_ok or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. If the hash uses older settings, quietly upgrade it now that we know the password
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
        db.commit()

    # 5. Success: hand out a signed token
    return TokenResponse(access_token=create_access_token(user.id))
