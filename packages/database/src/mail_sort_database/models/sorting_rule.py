from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SortingRule(Base):
    """A deterministic condition that routes an email before AI is used."""

    __tablename__ = "sorting_rules"
    __table_args__ = (UniqueConstraint("account_id", "condition_type", "condition_value"),)

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[str] = mapped_column(String(128), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    condition_type: Mapped[str] = mapped_column(String(32))
    condition_value: Mapped[str] = mapped_column(String(512))
    destination_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("destinations.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
