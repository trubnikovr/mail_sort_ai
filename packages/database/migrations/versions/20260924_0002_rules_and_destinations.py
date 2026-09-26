"""add destinations and sorting rules

Revision ID: 20260924_0002
Revises: 20260924_0001
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260924_0002"
down_revision = "20260924_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destinations",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("imap_mailbox", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "imap_mailbox"),
    )
    op.create_index("ix_destinations_account_id", "destinations", ["account_id"])
    op.create_table(
        "sorting_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("condition_type", sa.String(length=32), nullable=False),
        sa.Column("condition_value", sa.String(length=512), nullable=False),
        sa.Column("destination_id", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "condition_type", "condition_value"),
    )
    op.create_index("ix_sorting_rules_account_id", "sorting_rules", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_sorting_rules_account_id", table_name="sorting_rules")
    op.drop_table("sorting_rules")
    op.drop_index("ix_destinations_account_id", table_name="destinations")
    op.drop_table("destinations")
