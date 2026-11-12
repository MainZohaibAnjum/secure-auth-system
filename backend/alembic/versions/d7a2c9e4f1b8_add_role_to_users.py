"""add role to users

Revision ID: d7a2c9e4f1b8
Revises: c3e8f1a5b2d7
Create Date: 2026-11-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a2c9e4f1b8'
down_revision: Union[str, Sequence[str], None] = 'c3e8f1a5b2d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing users get 'user' straight away, thanks to the server default
    op.add_column('users', sa.Column('role', sa.String(length=20), server_default='user', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')
