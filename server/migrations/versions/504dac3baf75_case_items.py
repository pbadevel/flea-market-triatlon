"""items.photo_url -> items.image

Revision ID: 504dac3baf75
Revises: b3a94e437771
Create Date: 2025-09-09 09:18:34.861984

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "504dac3baf75"
down_revision: str | Sequence[str] | None = "b3a94e437771"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "case_items",
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("chance", sa.Float(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_case_items_created_at"), "case_items", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_case_items_updated_at"), "case_items", ["updated_at"], unique=False
    )

    op.alter_column("items", "photo_url", new_column_name="image")


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column("items", "image", new_column_name="photo_url")

    op.drop_index(op.f("ix_case_items_updated_at"), table_name="case_items")
    op.drop_index(op.f("ix_case_items_created_at"), table_name="case_items")
    op.drop_table("case_items")
