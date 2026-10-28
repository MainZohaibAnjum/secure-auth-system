import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """What the client must send to sign up."""

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        # "Ali@Mail.com" and "ali@mail.com" must count as the same account
        return value.lower()


class UserResponse(BaseModel):
    """What we send back about a user. Notice: no password or hash!"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    totp_enabled: bool
    created_at: datetime




class LoginRequest(BaseModel):
    """What the client must send to log in."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    """What we send back after a successful login."""

    access_token: str
    token_type: str = "bearer"




class LoginResponse(BaseModel):
    """Login answer: either an access token, or "now send your 2FA code"."""

    access_token: str | None = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    challenge_token: str | None = None


class TwoFactorCodeRequest(BaseModel):
    """A 6-digit code from the authenticator app."""

    code: str = Field(pattern=r"^\d{6}$")


class TwoFactorVerifyRequest(TwoFactorCodeRequest):
    """Second login step: the challenge token from /login plus the 6-digit code."""

    challenge_token: str


class TwoFactorDisableRequest(TwoFactorCodeRequest):
    """Turning 2FA off needs both the password and a current code."""

    password: str = Field(min_length=1, max_length=128)


class TwoFactorSetupResponse(BaseModel):
    """Everything needed to add this account to an authenticator app."""

    secret: str
    otpauth_uri: str
    qr_code_data_uri: str
