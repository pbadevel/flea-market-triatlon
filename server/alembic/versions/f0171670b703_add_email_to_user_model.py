"""add_email_to_user_model

Revision ID: f0171670b703
Revises: 2ca7d4923a6c
Create Date: 2026-06-10 23:35:00.541327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f0171670b703'
down_revision: Union[str, Sequence[str], None] = '2ca7d4923a6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users', 
        sa.Column('email', sa.String(255), nullable=True, unique=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        'users',
        'email',
    )