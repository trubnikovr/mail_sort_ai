from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EmailRecord(Base):
    """A short-lived normalized email snapshot used by the processor."""

    __tablename__ = "email_records"
    __table_args__ = (UniqueConstraint("account_id", "provider_message_id"),)

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[str] = mapped_column(String(128), index=True)
    provider_message_id: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(998), default="")
    headers: Mapped[dict] = mapped_column(JSONB, default=dict)
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
