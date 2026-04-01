"""avatar in users and cases

Revision ID: b3a94e437771
Revises: 65fb7cd31f5c
Create Date: 2025-09-06 10:26:55.908754

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3a94e437771"
down_revision: str | Sequence[str] | None = "65fb7cd31f5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "cases",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("image", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cases_created_at"), "cases", ["created_at"], unique=False)
    op.create_index(op.f("ix_cases_updated_at"), "cases", ["updated_at"], unique=False)
    op.add_column("users", sa.Column("avatar", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("users", "avatar")
    op.drop_index(op.f("ix_cases_updated_at"), table_name="cases")
    op.drop_index(op.f("ix_cases_created_at"), table_name="cases")
    op.drop_table("cases")
