"""merge heads

Revision ID: c4de97d7a4cc
Revises: 6421b6221a22, fddd63338fa1
Create Date: 2026-10-08 19:55:04.366000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4de97d7a4cc'
down_revision: Union[str, Sequence[str], None] = ('6421b6221a22', 'fddd63338fa1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
