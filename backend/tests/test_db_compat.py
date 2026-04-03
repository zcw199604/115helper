"""数据库兼容迁移测试。"""

from sqlalchemy import create_engine, inspect, text

from app.db.compat import ensure_schema_compat


def test_ensure_schema_compat_adds_duplicate_columns(tmp_path) -> None:
    db_path = tmp_path / 'compat.db'
    engine = create_engine(f'sqlite:///{db_path}')
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE sync_sources (id INTEGER PRIMARY KEY, name TEXT NOT NULL, local_path TEXT NOT NULL, remote_path TEXT NOT NULL, upload_mode TEXT NOT NULL, suffix_rules_json TEXT NOT NULL DEFAULT '[]', exclude_rules_json TEXT NOT NULL DEFAULT '[]', cron_expr TEXT, enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"))
    ensure_schema_compat(engine)
    columns = {col['name'] for col in inspect(engine).get_columns('sync_sources')}
    assert 'skip_existing_remote' in columns
    assert 'duplicate_check_mode' in columns
    assert 'force_refresh_remote_cache' in columns
    assert 'upload_flow_mode' in columns
