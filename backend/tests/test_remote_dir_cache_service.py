"""远端目录缓存服务测试。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.remote_dir_cache import RemoteDirCache, RemoteDirEntry
from app.services.remote_dir_cache_service import RemoteDirCacheService


def create_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cache.db'}", connect_args={'check_same_thread': False})
    Base.metadata.create_all(bind=engine, tables=[RemoteDirCache.__table__, RemoteDirEntry.__table__])
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_replace_and_read_dir_entries(tmp_path):
    db = create_db(tmp_path)
    service = RemoteDirCacheService(db)
    service.replace_dir_entries(remote_dir_id=10, remote_dir_path='/a', items=[{'id': '1', 'pickcode': 'pc1', 'name': 'demo.mkv', 'sha1': 'abc', 'size': 12}])
    exists, items = service.get_dir_entries(10)
    assert exists is True
    assert len(items) == 1
    assert items[0]['name'] == 'demo.mkv'


def test_upsert_file_entry_updates_cache(tmp_path):
    db = create_db(tmp_path)
    service = RemoteDirCacheService(db)
    service.upsert_file_entry(remote_dir_id=10, remote_dir_path='/a', remote_file_id='1', remote_pickcode='pc1', name='demo.mkv', sha1='abc', size=12)
    exists, items = service.get_dir_entries(10)
    assert exists is True
    assert items[0]['sha1'] == 'ABC'
