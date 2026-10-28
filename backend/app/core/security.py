import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# ---------- Passwords ----------

# Argon2id with the library's recommended settings
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Turn a plain password into a one-way Argon2 hash for storing in the database."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a typed password against the stored hash. Returns True or False."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with older/weaker settings and should be upgraded."""
    return _hasher.check_needs_rehash(password_hash)


# ---------- Access tokens (JWT) ----------


def create_access_token(user_id: uuid.UUID) -> str:
    """Make a short-lived signed token that proves who the user is."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # subject: which user this token belongs to
        "typ": "access",  # token type, so other kinds of tokens can't be used here
        "iss": settings.jwt_issuer,  # who made it
        "aud": settings.jwt_audience,  # who it's meant for
        "iat": now,  # issued at
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),  # expires
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Check the token's signature, expiry, issuer, audience and type.

    Raises jwt.InvalidTokenError if anything is wrong.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub", "iss", "aud"]},
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return payload
