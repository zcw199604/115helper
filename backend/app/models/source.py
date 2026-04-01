"""同步源配置模型。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SyncSource(Base):
    """同步源配置。"""

    __tablename__ = "sync_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    remote_path: Mapped[str] = mapped_column(Text, nullable=False)
    upload_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    suffix_rules_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    exclude_rules_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    skip_existing_remote: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_check_mode: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    force_refresh_remote_cache: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    runs = relationship("JobRun", back_populates="source", cascade="all, delete-orphan")
