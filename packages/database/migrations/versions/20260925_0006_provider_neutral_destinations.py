"""make destinations mailbox-provider neutral

Revision ID: 20260925_0006
Revises: 20260924_0005
Create Date: 2026-09-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0006"
down_revision = "20260924_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("destinations", "imap_mailbox", new_column_name="mailbox")
    op.drop_constraint(
        "destinations_account_id_imap_mailbox_key",
        "destinations",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_destinations_account_mailbox",
        "destinations",
        ["account_id", "mailbox"],
    )
    op.add_column(
        "destinations",
        sa.Column("description", sa.String(length=512), nullable=False, server_default=""),
    )
    op.alter_column("destinations", "description", server_default=None)


def downgrade() -> None:
    op.drop_column("destinations", "description")
    op.drop_constraint("uq_destinations_account_mailbox", "destinations", type_="unique")
    op.alter_column("destinations", "mailbox", new_column_name="imap_mailbox")
    op.create_unique_constraint(
        "destinations_account_id_imap_mailbox_key",
        "destinations",
        ["account_id", "imap_mailbox"],
    )
