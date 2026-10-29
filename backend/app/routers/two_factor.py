from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import encrypt_secret, verify_password
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.auth import (
    TwoFactorCodeRequest,
    TwoFactorDisableRequest,
    TwoFactorSetupResponse,
    UserResponse,
)
from app.services.totp import (
    generate_secret,
    provisioning_uri,
    qr_code_data_uri,
    verify_totp_code,
)

router = APIRouter(prefix="/auth/2fa", tags=["2fa"])


@router.post("/setup", response_model=TwoFactorSetupResponse)
def setup(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TwoFactorSetupResponse:
    """Step 1 of turning 2FA on: create a secret and show it as a QR code."""
    if current_user.totp_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA is already enabled")

    # Saved encrypted, but NOT switched on until the user proves their app works (/enable)
    secret = generate_secret()
    current_user.totp_secret_encrypted = encrypt_secret(secret)
    current_user.totp_last_used_step = None
    db.commit()

    uri = provisioning_uri(secret, current_user.email)
    return TwoFactorSetupResponse(
        secret=secret, otpauth_uri=uri, qr_code_data_uri=qr_code_data_uri(uri)
    )


@router.post("/enable", response_model=UserResponse)
def enable(
    data: TwoFactorCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Step 2 of turning 2FA on: confirm with a code from the app."""
    if current_user.totp_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA is already enabled")
    if not current_user.totp_secret_encrypted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Call /auth/2fa/setup first")
    if not verify_totp_code(current_user, data.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")

    current_user.totp_enabled = True
    db.commit()
    return current_user


@router.post("/disable", response_model=UserResponse)
@limiter.limit(settings.rate_limit_login)
def disable(
    data: TwoFactorDisableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Turn 2FA off. Needs the password AND a current code, so a stolen session can't."""
    if not current_user.totp_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA is not enabled")
    if not verify_password(data.password, current_user.password_hash) or not verify_totp_code(
        current_user, data.code
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid password or code")

    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None
    current_user.totp_last_used_step = None
    db.commit()
    return current_user
