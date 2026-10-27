from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import SignupRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


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
