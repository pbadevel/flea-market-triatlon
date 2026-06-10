"""add_roles_to_user_model

Revision ID: 2ca7d4923a6c
Revises: ebdd259fee44
Create Date: 2026-06-10 22:58:00.367607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2ca7d4923a6c'
down_revision: Union[str, Sequence[str], None] = 'ebdd259fee44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Добавляем колонку role в таблицу users.
    # Так как native_enum=False, SQLAlchemy создаст тип sa.Enum как VARCHAR + CHECK constraint.
    op.add_column(
        'users', 
        sa.Column(
            'role', 
            sa.Enum('USER', 'MODERATOR', 'ADMIN', name='userrole', native_enum=False), 
            nullable=False, 
            server_default='USER'
        )
    )
    op.drop_column(
        'users',
        'is_moderator',
    )


def downgrade() -> None:
    """Downgrade schema."""
    # При откате миграции просто удаляем колонку role из таблицы users
    op.drop_column('users', 'role')
    op.add_column(
        'users',
        sa.Column(
            'is_moderator',
            sa.Boolean,
            default=False, nullable=False, server_default="false"
        )
    )