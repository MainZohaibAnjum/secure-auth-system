"""Give a user the admin role, or take it away.

There is no API route for this on purpose: only someone who can run commands
on the server can make an admin.

Run from the backend folder (with the venv on):
    python -m app.make_admin you@example.com
    python -m app.make_admin you@example.com --remove
"""
import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Role, User


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Give a user the admin role, or take it away.")
    parser.add_argument("email")
    parser.add_argument("--remove", action="store_true", help="make the user a normal user again")
    args = parser.parse_args(argv)
    role = Role.USER if args.remove else Role.ADMIN

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None:
            print(f"No user with the email {args.email}")
            return 1
        user.role = role.value
        db.commit()

    print(f"{user.email} is now: {role.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
