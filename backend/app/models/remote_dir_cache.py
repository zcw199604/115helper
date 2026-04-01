"""远端目录缓存模型。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RemoteDirCache(Base):
    """远端目录缓存元数据。"""

    __tablename__ = "remote_dir_caches"

    remote_dir_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    remote_dir_path: Mapped[str] = mapped_column(Text, nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RemoteDirEntry(Base):
    """远端目录文件缓存条目。"""

    __tablename__ = "remote_dir_entries"
    __table_args__ = (
        Index("idx_remote_dir_entries_dir_name", "remote_dir_id", "name"),
        Index("idx_remote_dir_entries_dir_sha1", "remote_dir_id", "sha1"),
        Index("idx_remote_dir_entries_dir_file", "remote_dir_id", "remote_file_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    remote_dir_id: Mapped[int] = mapped_column(Integer, nullable=False)
    remote_dir_path: Mapped[str] = mapped_column(Text, nullable=False)
    remote_file_id: Mapped[str] = mapped_column(String(64), nullable=False)
    remote_pickcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sha1: Mapped[str | None] = mapped_column(String(40), nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_dir: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
