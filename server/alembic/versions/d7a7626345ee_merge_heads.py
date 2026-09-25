"""merge heads

Revision ID: d7a7626345ee
Revises: 5ff7a3ba3d23, z_make_tg_user_id_nullable
Create Date: 2026-06-21 16:54:24.993869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a7626345ee'
down_revision: Union[str, Sequence[str], None] = ('5ff7a3ba3d23', 'z_make_tg_user_id_nullable')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
