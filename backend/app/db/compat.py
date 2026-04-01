"""SQLite 轻量兼容迁移。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema_compat(engine: Engine) -> None:
    """为无迁移框架场景补齐关键列。"""

    inspector = inspect(engine)
    if "sync_sources" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("sync_sources")}
    with engine.begin() as conn:
        if "skip_existing_remote" not in columns:
            conn.execute(text("ALTER TABLE sync_sources ADD COLUMN skip_existing_remote INTEGER NOT NULL DEFAULT 0"))
        if "duplicate_check_mode" not in columns:
            conn.execute(text("ALTER TABLE sync_sources ADD COLUMN duplicate_check_mode VARCHAR(16) NOT NULL DEFAULT 'none'"))
            conn.execute(text("UPDATE sync_sources SET duplicate_check_mode = CASE WHEN skip_existing_remote = 1 THEN 'sha1' ELSE 'none' END"))
