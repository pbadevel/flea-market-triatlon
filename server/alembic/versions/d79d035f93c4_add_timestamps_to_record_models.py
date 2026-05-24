"""add_timestamps_to_record_models

Revision ID: d79d035f93c4
Revises: 314f1b95e142
Create Date: 2026-05-22 12:47:09.635524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd79d035f93c4'
down_revision: Union[str, Sequence[str], None] = '314f1b95e142'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблицы без временных меток: добавляем created_at + updated_at
    for table in ['ad_photos', 'ad_edit_photos', 'delete_messages']:
        op.add_column(table, sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()))
        op.add_column(table, sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True))

    # Таблицы с created_at: добавляем только updated_at
    for table in ['users', 'ads', 'ad_edits', 'reviews', 'contact_logs', 'details_logs', 'tags', 'blacklist']:
        op.add_column(table, sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    # Удаляем updated_at везде
    for table in ['ad_photos', 'ad_edit_photos', 'delete_messages', 'users', 'ads', 'ad_edits', 'reviews', 'contact_logs', 'details_logs', 'tags', 'blacklist']:
        op.drop_column(table, 'updated_at')

    # Удаляем created_at только из тех, куда мы его добавили
    for table in ['ad_photos', 'ad_edit_photos', 'delete_messages']:
        op.drop_column(table, 'created_at')