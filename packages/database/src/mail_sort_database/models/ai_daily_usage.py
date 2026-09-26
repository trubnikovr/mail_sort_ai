from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AiDailyUsage(Base):
    """Durable per-provider request counter used to enforce daily API caps."""

    __tablename__ = "ai_daily_usage"
    __table_args__ = (UniqueConstraint("provider", "usage_date"),)

    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
