import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_token
from app.models import RecoveryCode, User
from app.services.totp import verify_totp_code

# No 0/O or 1/I, so codes are easy to read and type
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# 16 characters from 32 choices = 80 random bits, far too many to guess
_CODE_LENGTH = 16


def create_recovery_codes(db: Session, user: User) -> list[str]:
    """Make a fresh set of codes (old ones stop working). Returns the codes to show ONCE."""
    delete_recovery_codes(db, user)
    codes = [_new_code() for _ in range(settings.recovery_code_count)]
    # Only the hash is saved. The codes are random and long, so a fast hash is safe here
    # (passwords need slow Argon2 because people pick short, guessable ones).
    db.add_all(RecoveryCode(user_id=user.id, code_hash=hash_token(_normalize(c))) for c in codes)
    return codes


def use_recovery_code(db: Session, user: User, code: str) -> bool:
    """Spend one recovery code. True if it was valid and not used before."""
    # One UPDATE does the check and the "mark as used", so two logins racing
    # with the same code can't both succeed
    result = db.execute(
        update(RecoveryCode)
        .where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == hash_token(_normalize(code)),
            RecoveryCode.used_at.is_(None),
        )
        .values(used_at=datetime.now(timezone.utc))
    )
    return result.rowcount == 1


def count_unused_recovery_codes(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count())
        .select_from(RecoveryCode)
        .where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
    )


def delete_recovery_codes(db: Session, user: User) -> None:
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))


def verify_second_factor(db: Session, user: User, code: str) -> bool:
    """A 6-digit code from the authenticator app, or a recovery code."""
    if re.fullmatch(r"\d{6}", code):
        return verify_totp_code(user, code)
    return use_recovery_code(db, user, code)


def _new_code() -> str:
    """Like "K7MP-Q2XR-9HTV-4WNA". The dashes are only there to make it easy to read."""
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))
    return "-".join(raw[i : i + 4] for i in range(0, _CODE_LENGTH, 4))


def _normalize(code: str) -> str:
    """Accept "k7mp q2xr..." or "K7MPQ2XR..." as well as "K7MP-Q2XR-..."."""
    return re.sub(r"[\s-]", "", code).upper()
