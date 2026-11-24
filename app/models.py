"""Database tables."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApiKey(Base):
    """A client of the API. Only the hash of the key is stored, never the key."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ValidationLog(Base):
    """One row per validation. Stores the masked ID only, never the full number."""

    __tablename__ = "validation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"))
    id_type: Mapped[str] = mapped_column(String(20))
    masked_value: Mapped[str] = mapped_column(String(32))
    is_valid: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # The stats queries filter by key and sort by time, so index both together.
    __table_args__ = (Index("ix_validation_logs_key_created", "api_key_id", "created_at"),)
