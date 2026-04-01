"""added items and inventory

Revision ID: 65fb7cd31f5c
Revises: 6ce2a9583857
Create Date: 2025-09-06 09:00:01.865148

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "65fb7cd31f5c"
down_revision: str | Sequence[str] | None = "6ce2a9583857"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "items",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("photo_url", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_created_at"), "items", ["created_at"], unique=False)
    op.create_index(op.f("ix_items_updated_at"), "items", ["updated_at"], unique=False)
    op.create_table(
        "inventory_items",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="cascade"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="cascade"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_items_created_at"),
        "inventory_items",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_items_updated_at"),
        "inventory_items",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(op.f("ix_inventory_items_updated_at"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_created_at"), table_name="inventory_items")
    op.drop_table("inventory_items")
    op.drop_index(op.f("ix_items_updated_at"), table_name="items")
    op.drop_index(op.f("ix_items_created_at"), table_name="items")
    op.drop_table("items")
