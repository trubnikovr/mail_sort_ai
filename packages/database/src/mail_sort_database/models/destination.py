from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Destination(Base):
    """A user-configured mailbox destination available to the processor."""

    __tablename__ = "destinations"
    __table_args__ = (UniqueConstraint("account_id", "mailbox"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("mailbox_accounts.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512), default="")
    instruction: Mapped[str] = mapped_column(Text, default="")
    mailbox: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    use_for_ai: Mapped[bool] = mapped_column(Boolean, default=True)
