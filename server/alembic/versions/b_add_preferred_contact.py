"""add preferred_contact to users

Revision ID: b_add_preferred_contact
Revises: a_add_is_banned_to_users
Create Date: 2026-06-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b_add_preferred_contact'
down_revision: Union[str, Sequence[str], None] = 'a_add_is_banned_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('preferred_contact', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'preferred_contact')
