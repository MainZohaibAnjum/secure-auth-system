from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models import User
from app.schemas.admin import AdminUserResponse

# Every route in this file is admin-only: require_admin runs before each one
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Every account, newest first."""
    return list(db.scalars(select(User).order_by(User.created_at.desc())))
