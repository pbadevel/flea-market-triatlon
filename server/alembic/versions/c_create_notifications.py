"""create notifications table

Revision ID: c_create_notifications
Revises: b_add_preferred_contact
Create Date: 2026-06-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c_create_notifications'
down_revision: Union[str, Sequence[str], None] = 'b_add_preferred_contact'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False, server_default='info'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ad_id', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('notifications')
