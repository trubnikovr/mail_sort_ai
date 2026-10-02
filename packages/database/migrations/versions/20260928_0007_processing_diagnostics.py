"""Persist step and AI request diagnostics independently of job transactions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260928_0007"
down_revision = "20260925_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("job_events", "ai_requests"):
        op.create_table(
            table,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("attempt", sa.Integer(), nullable=False),
            sa.Column("step", sa.String(128), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("details", postgresql.JSONB(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index(f"ix_{table}_job_id", table, ["job_id"])
        op.create_index(f"ix_{table}_run_id", table, ["run_id"])


def downgrade() -> None:
    for table in ("ai_requests", "job_events"):
        op.drop_table(table)
