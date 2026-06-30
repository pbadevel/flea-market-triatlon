"""add contact_value to users

Revision ID: d_add_contact_value
Revises: c_create_notifications
Create Date: 2026-06-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd_add_contact_value'
down_revision: Union[str, Sequence[str], None] = 'c_create_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('contact_value', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'contact_value')
