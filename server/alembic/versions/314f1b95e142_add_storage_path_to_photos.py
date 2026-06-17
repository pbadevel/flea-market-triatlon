"""add_storage_path_to_photos

Revision ID: 314f1b95e142
Revises: 
Create Date: 2026-05-19 01:39:12.768256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '314f1b95e142'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ad_photos', sa.Column('storage_path', sa.String(), nullable=True))
    op.add_column('ad_edit_photos', sa.Column('storage_path', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('ad_edit_photos', 'storage_path')
    op.drop_column('ad_photos', 'storage_path')
