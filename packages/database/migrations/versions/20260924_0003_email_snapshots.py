"""add short-lived email snapshots

Revision ID: 20260924_0003
Revises: 20260924_0002
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260924_0003"
down_revision = "20260924_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=False),
        sa.Column("headers", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "provider_message_id"),
    )
    op.create_index("ix_email_records_account_id", "email_records", ["account_id"])
    op.create_index("ix_email_records_expires_at", "email_records", ["expires_at"])
    op.add_column("jobs", sa.Column("email_record_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "jobs_email_record_id_fkey",
        "jobs",
        "email_records",
        ["email_record_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("jobs_email_record_id_fkey", "jobs", type_="foreignkey")
    op.drop_column("jobs", "email_record_id")
    op.drop_index("ix_email_records_expires_at", table_name="email_records")
    op.drop_index("ix_email_records_account_id", table_name="email_records")
    op.drop_table("email_records")
