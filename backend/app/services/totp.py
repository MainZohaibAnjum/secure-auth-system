import base64
import hmac
import io
import time

import pyotp
import qrcode

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models import User

# Accept the previous, current and next 30-second code, to allow for phone clock drift
_ALLOWED_STEP_DRIFT = 1


def generate_secret() -> str:
    """A new random secret shared between our server and the user's authenticator app."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    """The otpauth:// link that authenticator apps read from the QR code."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.totp_issuer_name)


def qr_code_data_uri(uri: str) -> str:
    """Draw the otpauth:// link as a QR code image the website can show directly."""
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def verify_totp_code(user: User, code: str) -> bool:
    """Check a 6-digit code for this user. Each code can only be used once.

    On success, remembers the code's time step so the same code can't be replayed.
    """
    if not user.totp_secret_encrypted:
        return False

    totp = pyotp.TOTP(decrypt_secret(user.totp_secret_encrypted))
    current_step = int(time.time()) // totp.interval
    last_used = user.totp_last_used_step if user.totp_last_used_step is not None else -1

    for step in range(current_step - _ALLOWED_STEP_DRIFT, current_step + _ALLOWED_STEP_DRIFT + 1):
        if step <= last_used:
            continue  # this code (or an older one) was already used
        if hmac.compare_digest(totp.at(step * totp.interval), code):
            user.totp_last_used_step = step
            return True
    return False
