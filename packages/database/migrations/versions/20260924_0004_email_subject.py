"""store email subject separately

Revision ID: 20260924_0004
Revises: 20260924_0003
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_0004"
down_revision = "20260924_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_records",
        sa.Column("subject", sa.String(length=998), nullable=False, server_default=""),
    )
    op.execute("UPDATE email_records SET subject = COALESCE(headers->>'subject', '')")
    op.alter_column("email_records", "subject", server_default=None)


def downgrade() -> None:
    op.drop_column("email_records", "subject")
