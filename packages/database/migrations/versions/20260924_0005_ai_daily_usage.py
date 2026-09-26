"""add durable AI daily usage limit

Revision ID: 20260924_0005
Revises: 20260924_0004
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_0005"
down_revision = "20260924_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_daily_usage",
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("provider", "usage_date"),
        sa.UniqueConstraint("provider", "usage_date"),
    )


def downgrade() -> None:
    op.drop_table("ai_daily_usage")
