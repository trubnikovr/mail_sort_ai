from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MailboxCursor(Base):
    __tablename__ = "mailbox_cursors"

    account_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    cursor: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
