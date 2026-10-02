"""Remove provider cursors; collectors scan unread messages instead."""
from alembic import op
import sqlalchemy as sa

revision = "20261002_0008"
down_revision = "20260928_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("mailbox_cursors")


def downgrade() -> None:
    op.create_table(
        "mailbox_cursors",
        sa.Column("account_id", sa.String(length=128), primary_key=True),
        sa.Column("cursor", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
