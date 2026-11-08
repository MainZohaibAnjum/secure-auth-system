import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
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

# ---------- "Your devices" (session management) ----------
# One device = one login family. Its newest row is the only one that isn't revoked.


def list_active_sessions(
    db: Session, user_id: uuid.UUID
) -> list[tuple[RefreshSession, datetime]]:
    """This user's logged-in devices: (current row of each family, when it first signed in)."""
    first_login = (
        select(
            RefreshSession.family_id,
            func.min(RefreshSession.created_at).label("signed_in_at"),
        )
        .where(RefreshSession.user_id == user_id)
        .group_by(RefreshSession.family_id)
        .subquery()
    )
    rows = db.execute(
        select(RefreshSession, first_login.c.signed_in_at)
        .join(first_login, first_login.c.family_id == RefreshSession.family_id)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(timezone.utc),
        )
        .order_by(RefreshSession.created_at.desc())  # most recently active first
    ).all()
    return [(row[0], row[1]) for row in rows]


def find_family_id(db: Session, user_id: uuid.UUID, token: str) -> uuid.UUID | None:
    """Which device (family) a refresh token belongs to, if it's active and this user's."""
    return db.scalar(
        select(RefreshSession.family_id).where(
            RefreshSession.token_hash == hash_token(token),
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
        )
    )


def revoke_user_family(db: Session, user_id: uuid.UUID, family_id: uuid.UUID) -> bool:
    """Log out one device. Only works on this user's own sessions. True if one was found."""
    result = db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,  # never touch another user's sessions
            RefreshSession.family_id == family_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    return result.rowcount > 0


def revoke_other_families(
    db: Session, user_id: uuid.UUID, keep_family_id: uuid.UUID | None
) -> int:
    """Log out every device of this user except one. Returns how many were logged out."""
    now = datetime.now(timezone.utc)
    query = update(RefreshSession).where(
        RefreshSession.user_id == user_id,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > now,  # expired ones are already logged out
    )
    if keep_family_id is not None:
        query = query.where(RefreshSession.family_id != keep_family_id)
    # Each device has exactly one active row, so rows changed = devices logged out
    return db.execute(query.values(revoked_at=now)).rowcount
