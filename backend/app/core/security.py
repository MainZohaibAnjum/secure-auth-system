from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

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
