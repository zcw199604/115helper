"""文件级同步结果模型。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FileRecord(Base):
    """文件级同步记录。"""

    __tablename__ = "file_records"
    __table_args__ = (
        Index("uniq_source_relative_path", "source_id", "relative_path", unique=False),
        Index("idx_file_records_run_id", "run_id"),
        Index("idx_file_records_sha1", "file_sha1"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sync_sources.id"), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_sha1: Mapped[str | None] = mapped_column(String(40), nullable=True)
    suffix: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    remote_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_pickcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    run = relationship("JobRun", back_populates="file_records")
