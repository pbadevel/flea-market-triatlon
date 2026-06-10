"""make ad_photos file_id and storage_path nullable

Revision ID: ebdd259fee44
Revises: d79d035f93c4
Create Date: 2026-06-10 17:15:43.788906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ebdd259fee44'
down_revision: Union[str, Sequence[str], None] = 'd79d035f93c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Делаем file_id nullable
    op.alter_column(
        'ad_photos',
        'file_id',
        existing_type=sa.String(),
        nullable=True,
    )
    # Делаем storage_path nullable
    op.alter_column(
        'ad_photos',
        'storage_path',
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'ad_photos',
        'storage_path',
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        'ad_photos',
        'file_id',
        existing_type=sa.String(),
        nullable=False,
    )