"""make tg_user_id nullable for email users

Revision ID: z_make_tg_user_id_nullable
Revises: f9fedebf1890
Create Date: 2026-06-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'z_make_tg_user_id_nullable'
down_revision: Union[str, Sequence[str], None] = 'f9fedebf1890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'tg_user_id', nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'tg_user_id', nullable=False)
