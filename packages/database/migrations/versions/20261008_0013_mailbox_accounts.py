"""Add dashboard-managed mailbox accounts."""

from alembic import op
import sqlalchemy as sa


revision = "20261008_0013"
down_revision = "20261006_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mailbox_accounts",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=True),
        sa.Column("email_address", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_mailbox", sa.String(length=255), nullable=False, server_default="INBOX"),
        sa.Column("host", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("username", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("encrypted_password", sa.String(length=4096), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Keep the identifiers already used by jobs and destinations so history
    # remains attached to the same account. The rows are intentionally inactive
    # and contain no connection secrets; an administrator configures them later.
    op.execute(
        """
        INSERT INTO mailbox_accounts (id, name)
        SELECT account_id, account_id
        FROM (
            SELECT account_id FROM destinations
            UNION
            SELECT account_id FROM jobs
            UNION
            SELECT account_id FROM email_records
        ) existing_accounts
        WHERE account_id IS NOT NULL AND account_id <> ''
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO mailbox_accounts (id, name)
        SELECT 'primary-mailbox', 'Основной почтовый ящик'
        WHERE NOT EXISTS (SELECT 1 FROM mailbox_accounts)
        """
    )
    op.create_foreign_key(
        "fk_destinations_account_id_mailbox_accounts",
        "destinations",
        "mailbox_accounts",
        ["account_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_destinations_account_id_mailbox_accounts", "destinations", type_="foreignkey")
    op.drop_table("mailbox_accounts")
