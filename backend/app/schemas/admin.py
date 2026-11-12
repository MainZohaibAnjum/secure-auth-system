from app.schemas.auth import UserResponse


class AdminUserResponse(UserResponse):
    """What an admin sees about each account (still no password hash!)."""

    is_active: bool
