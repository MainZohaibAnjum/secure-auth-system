import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet

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


# ---------- Signed tokens (JWT) ----------

ACCESS_TOKEN_TYPE = "access"
TWO_FA_CHALLENGE_TOKEN_TYPE = "2fa_challenge"


def create_access_token(user_id: uuid.UUID) -> str:
    """Make a short-lived signed token that proves who the user is."""
    return _create_token(user_id, ACCESS_TOKEN_TYPE, settings.access_token_expire_minutes)


def decode_access_token(token: str) -> dict:
    """Check an access token. Raises jwt.InvalidTokenError if anything is wrong."""
    return _decode_token(token, ACCESS_TOKEN_TYPE)


def create_2fa_challenge_token(user_id: uuid.UUID) -> str:
    """A short-lived token meaning: password was correct, now waiting for the 2FA code."""
    return _create_token(
        user_id, TWO_FA_CHALLENGE_TOKEN_TYPE, settings.two_fa_challenge_expire_minutes
    )


def decode_2fa_challenge_token(token: str) -> dict:
    """Check a 2FA challenge token. Raises jwt.InvalidTokenError if anything is wrong."""
    return _decode_token(token, TWO_FA_CHALLENGE_TOKEN_TYPE)


def _create_token(user_id: uuid.UUID, token_type: str, expire_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # subject: which user this token belongs to
        "typ": token_type,  # so one kind of token can't be used as another
        "iss": settings.jwt_issuer,  # who made it
        "aud": settings.jwt_audience,  # who it's meant for
        "iat": now,  # issued at
        "exp": now + timedelta(minutes=expire_minutes),  # expires
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str, expected_type: str) -> dict:
    """Check signature, expiry, issuer, audience and type."""
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub", "iss", "aud"]},
    )
    if payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


# ---------- Refresh tokens ----------


def generate_refresh_token() -> str:
    """A long random string (256 bits). Unguessable, and it means nothing by itself."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 of a refresh token, which is what we store in the database."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- 2FA secret encryption ----------

_fernet = Fernet(settings.totp_encryption_key)


def encrypt_secret(secret: str) -> str:
    """Encrypt a TOTP secret before saving it in the database."""
    return _fernet.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    """Decrypt a TOTP secret read from the database."""
    return _fernet.decrypt(encrypted.encode()).decode()
