from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MailboxAccount(Base):
    """Mailbox connection managed by the dashboard; credentials are encrypted."""

    __tablename__ = "mailbox_accounts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str | None] = mapped_column(String(16))
    email_address: Mapped[str] = mapped_column(String(255), default="", server_default="")
    source_mailbox: Mapped[str] = mapped_column(
        String(255), default="INBOX", server_default="INBOX"
    )
    host: Mapped[str] = mapped_column(String(512), default="", server_default="")
    port: Mapped[int] = mapped_column(Integer, default=993, server_default="993")
    username: Mapped[str] = mapped_column(String(255), default="", server_default="")
    encrypted_password: Mapped[str | None] = mapped_column(String(4096))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def is_configured(self) -> bool:
        return bool(
            self.provider in {"ews", "imap"}
            and self.email_address.strip()
            and self.host.strip()
            and self.username.strip()
            and self.encrypted_password
            and self.port > 0
        )
