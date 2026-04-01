"""任务级执行日志模型。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskLog(Base):
    """任务执行日志。"""

    __tablename__ = "task_logs"
    __table_args__ = (
        Index("idx_task_logs_run_id", "run_id"),
        Index("idx_task_logs_source_id", "source_id"),
        Index("idx_task_logs_stage", "stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_runs.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sync_sources.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
