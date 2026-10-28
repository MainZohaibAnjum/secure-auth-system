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


