import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_token
from app.models import RefreshSession


class InvalidRefreshToken(Exception):
    """The refresh token is unknown, expired, or was already used."""


def create_refresh_session(
    db: Session,
    user_id: uuid.UUID,
    user_agent: str | None,
    ip: str | None,
    family_id: uuid.UUID | None = None,
) -> tuple[str, RefreshSession]:
    """Store a new session and return (raw token for the cookie, database row)."""
    token = generate_refresh_token()
    session = RefreshSession(
        user_id=user_id,
        token_hash=hash_token(token),
        family_id=family_id or uuid.uuid4(),  # new login = new family
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent[:512] if user_agent else None,
        ip=ip,
    )
    db.add(session)
    db.flush()  # gives session.id a value without committing yet
    return token, session


def rotate_refresh_session(
    db: Session, token: str, user_agent: str | None, ip: str | None
) -> tuple[str, RefreshSession]:
    """Swap a valid refresh token for a brand-new one (the old one stops working)."""
    now = datetime.now(timezone.utc)
    current = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == hash_token(token))
        .with_for_update()  # lock the row so two refreshes can't both use it
    )
    if current is None:
        raise InvalidRefreshToken

    if current.revoked_at is not None:
        # An already-used token came back. Someone may have stolen it,
        # so log out every device in this chain (thief and real user).
        _revoke_family(db, current.family_id, now)
        db.commit()
        raise InvalidRefreshToken

    if current.expires_at <= now:
        raise InvalidRefreshToken

    new_token, new_session = create_refresh_session(
        db, current.user_id, user_agent, ip, family_id=current.family_id
    )
    current.revoked_at = now
    current.replaced_by_id = new_session.id
    return new_token, new_session


def revoke_refresh_session(db: Session, token: str) -> None:
    """Log out: make this refresh token stop working (does nothing if unknown)."""
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == hash_token(token))
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)


def _revoke_family(db: Session, family_id: uuid.UUID, now: datetime) -> None:
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
