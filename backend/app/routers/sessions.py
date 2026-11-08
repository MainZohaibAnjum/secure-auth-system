import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.routers.auth import REFRESH_COOKIE_NAME
from app.schemas.auth import RevokeOthersResponse, SessionResponse
from app.services.refresh_sessions import (
    find_family_id,
    list_active_sessions,
    revoke_other_families,
    revoke_user_family,
)

router = APIRouter(prefix="/auth/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    """All devices where this user is logged in."""
    current_family = _current_family_id(db, request, current_user)
    return [
        SessionResponse(
            id=session.family_id,
            user_agent=session.user_agent,
            ip=session.ip,
            signed_in_at=signed_in_at,
            last_active_at=session.created_at,  # each refresh creates a new row
            current=session.family_id == current_family,
        )
        for session, signed_in_at in list_active_sessions(db, current_user.id)
    ]


@router.post("/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Log out one of this user's other devices."""
    if session_id == _current_family_id(db, request, current_user):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "This is your current device. Use log out instead."
        )
    # 404 for "not yours" too, so nobody can probe for other users' session IDs
    if not revoke_user_family(db, current_user.id, session_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    db.commit()


@router.post("/revoke-others", response_model=RevokeOthersResponse)
def revoke_others(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RevokeOthersResponse:
    """Log out every device except this one."""
    keep = _current_family_id(db, request, current_user)
    revoked = revoke_other_families(db, current_user.id, keep)
    db.commit()
    return RevokeOthersResponse(revoked=revoked)


def _current_family_id(db: Session, request: Request, user: User) -> uuid.UUID | None:
    """The device making this request, found through its refresh cookie."""
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    return find_family_id(db, user.id, token) if token else None

