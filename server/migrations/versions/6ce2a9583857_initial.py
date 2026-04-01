"""initial

Revision ID: 6ce2a9583857
Revises:
Create Date: 2025-09-05 06:19:29.948711

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ce2a9583857"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("USER", "ADMIN", name="userrole", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_updated_at"), "users", ["updated_at"], unique=False)
    op.create_table(
        "user_sessions",
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="cascade"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_user_sessions_created_at"),
        "user_sessions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_sessions_expires_at"),
        "user_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_sessions_updated_at"),
        "user_sessions",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_sessions_updated_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_created_at"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_users_updated_at"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_table("users")
