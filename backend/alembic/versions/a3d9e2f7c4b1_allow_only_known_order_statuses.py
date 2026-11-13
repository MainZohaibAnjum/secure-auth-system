"""allow only known order statuses

Revision ID: a3d9e2f7c4b1
Revises: 771d9837e9ae
Create Date: 2026-11-13 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3d9e2f7c4b1'
down_revision: Union[str, Sequence[str], None] = '771d9837e9ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alembic can't spot new CHECK rules by itself, so this file was written by hand
    op.create_check_constraint(
        'status_known', 'orders', "status IN ('paid', 'shipped', 'delivered', 'cancelled')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('status_known', 'orders', type_='check')
