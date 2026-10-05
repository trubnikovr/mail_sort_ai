"""Store classification guidance on destinations and remove legacy rules.

Revision ID: 20261003_0010
Revises: 20261002_0009
"""
from alembic import op
import sqlalchemy as sa


revision = "20261003_0010"
down_revision = "20261002_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destinations",
        sa.Column("instruction", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "destinations",
        sa.Column("use_for_ai", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(
        """
        UPDATE destinations AS destination
        SET instruction = concat_ws(
            E'\\n\\n',
            nullif(destination.description, ''),
            (
                SELECT string_agg(
                    sorting_rule.condition_type || ': ' || sorting_rule.condition_value,
                    E'\\n' ORDER BY sorting_rule.priority
                )
                FROM sorting_rules AS sorting_rule
                WHERE sorting_rule.destination_id = destination.id
            )
        )
        WHERE destination.instruction = ''
          AND (
              destination.description <> ''
              OR EXISTS (
                  SELECT 1 FROM sorting_rules AS sorting_rule
                  WHERE sorting_rule.destination_id = destination.id
              )
          )
        """
    )
    op.alter_column("destinations", "instruction", server_default=None)
    op.alter_column("destinations", "use_for_ai", server_default=None)
    op.drop_index("ix_sorting_rules_account_id", table_name="sorting_rules")
    op.drop_table("sorting_rules")


def downgrade() -> None:
    op.create_table(
        "sorting_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("condition_type", sa.String(length=32), nullable=False),
        sa.Column("condition_value", sa.String(length=512), nullable=False),
        sa.Column("destination_id", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "condition_type", "condition_value"),
    )
    op.create_index("ix_sorting_rules_account_id", "sorting_rules", ["account_id"])
    op.drop_column("destinations", "use_for_ai")
    op.drop_column("destinations", "instruction")
