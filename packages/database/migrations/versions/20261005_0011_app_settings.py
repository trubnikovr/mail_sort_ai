"""Add generic runtime application settings."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261005_0011"
down_revision = "20261003_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        """
        INSERT INTO app_settings (key, value, description)
        VALUES (
            'mail_decision.enabled',
            'true'::jsonb,
            'Controls whether Decision claims new classification jobs.'
        )
        """
    )


def downgrade() -> None:
    op.drop_table("app_settings")
