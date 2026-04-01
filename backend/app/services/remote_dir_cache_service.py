"""远端目录缓存服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.remote_dir_cache import RemoteDirCache, RemoteDirEntry


class RemoteDirCacheService:
    """负责远端目录缓存的读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_dir_entries(self, remote_dir_id: int) -> tuple[bool, list[dict]]:
        cache = self.db.get(RemoteDirCache, remote_dir_id)
        if cache is None:
            return False, []
        entries = (
            self.db.query(RemoteDirEntry)
            .filter(RemoteDirEntry.remote_dir_id == remote_dir_id)
            .order_by(RemoteDirEntry.id.asc())
            .all()
        )
        return True, [self._to_dict(item) for item in entries]

    def replace_dir_entries(self, *, remote_dir_id: int, remote_dir_path: str, items: list[dict]) -> None:
        now = datetime.now(timezone.utc)
        cache = self.db.get(RemoteDirCache, remote_dir_id)
        if cache is None:
            cache = RemoteDirCache(remote_dir_id=remote_dir_id, remote_dir_path=remote_dir_path, entry_count=len(items), fetched_at=now)
        else:
            cache.remote_dir_path = remote_dir_path
            cache.entry_count = len(items)
            cache.fetched_at = now
        self.db.add(cache)
        self.db.query(RemoteDirEntry).filter(RemoteDirEntry.remote_dir_id == remote_dir_id).delete()
        for item in items:
            file_id = str(item.get('id') or '')
            if not file_id:
                continue
            self.db.add(
                RemoteDirEntry(
                    remote_dir_id=remote_dir_id,
                    remote_dir_path=remote_dir_path,
                    remote_file_id=file_id,
                    remote_pickcode=item.get('pickcode'),
                    name=item.get('name') or '',
                    sha1=(str(item.get('sha1') or '').upper() or None),
                    size=self._to_int(item.get('size')),
                    is_dir=1 if item.get('is_dir') else 0,
                    fetched_at=now,
                )
            )
        self.db.commit()

    def upsert_file_entry(
        self,
        *,
        remote_dir_id: int,
        remote_dir_path: str,
        remote_file_id: str | None,
        remote_pickcode: str | None,
        name: str,
        sha1: str | None,
        size: int | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        cache = self.db.get(RemoteDirCache, remote_dir_id)
        if cache is None:
            cache = RemoteDirCache(remote_dir_id=remote_dir_id, remote_dir_path=remote_dir_path, entry_count=0, fetched_at=now)
            self.db.add(cache)
            self.db.flush()
        else:
            cache.remote_dir_path = remote_dir_path
            cache.fetched_at = now
        file_id = str(remote_file_id or '').strip()
        entry = None
        if file_id:
            entry = (
                self.db.query(RemoteDirEntry)
                .filter(RemoteDirEntry.remote_dir_id == remote_dir_id, RemoteDirEntry.remote_file_id == file_id)
                .first()
            )
        if entry is None:
            entry = RemoteDirEntry(
                remote_dir_id=remote_dir_id,
                remote_dir_path=remote_dir_path,
                remote_file_id=file_id or f'local:{name}:{sha1 or size or 0}',
                remote_pickcode=remote_pickcode,
                name=name,
                sha1=(sha1 or '').upper() or None,
                size=size,
                is_dir=0,
                fetched_at=now,
            )
        else:
            entry.remote_dir_path = remote_dir_path
            entry.remote_pickcode = remote_pickcode
            entry.name = name
            entry.sha1 = (sha1 or '').upper() or None
            entry.size = size
            entry.fetched_at = now
        self.db.add(entry)
        self.db.flush()
        cache.entry_count = self.db.query(RemoteDirEntry).filter(RemoteDirEntry.remote_dir_id == remote_dir_id).count()
        self.db.add(cache)
        self.db.commit()

    @staticmethod
    def _to_dict(item: RemoteDirEntry) -> dict:
        return {
            'id': item.remote_file_id,
            'pickcode': item.remote_pickcode,
            'name': item.name,
            'sha1': item.sha1 or '',
            'size': item.size,
            'is_dir': bool(item.is_dir),
        }

    @staticmethod
    def _to_int(value) -> int | None:
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
