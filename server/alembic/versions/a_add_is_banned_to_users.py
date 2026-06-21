"""add is_banned to users

Revision ID: a_add_is_banned_to_users
Revises: d7a7626345ee
Create Date: 2026-06-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a_add_is_banned_to_users'
down_revision: Union[str, Sequence[str], None] = 'd7a7626345ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'is_banned')
