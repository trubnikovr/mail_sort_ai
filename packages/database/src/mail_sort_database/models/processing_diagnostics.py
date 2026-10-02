from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DiagnosticColumns:
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("jobs.id"), index=True)
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    step: Mapped[str] = mapped_column(String(128))
    step_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobEvent(DiagnosticColumns, Base):
    __tablename__ = "job_events"


class AiRequest(DiagnosticColumns, Base):
    """Append-only request events paired by request_id in details."""
    __tablename__ = "ai_requests"
