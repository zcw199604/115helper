"""上传策略测试。"""

from pathlib import Path

from app.models.enums import DuplicateCheckMode, FileAction, UploadMode
from app.services.sync_scanner import LocalFileCandidate, calc_sha1
from app.services.upload_strategy import UploadStrategyService


class FakeGateway:
    def __init__(self, items: list[dict] | None = None) -> None:
        self.items = items or []
        self.fast_called = False
        self.multipart_called = False
        self.list_count = 0

    def ensure_remote_dir(self, _remote_dir):
        return 100

    def list_remote_dir_files(self, *, pid: int):
        assert pid == 100
        self.list_count += 1
        return list(self.items)

    def fast_upload_init(self, **_kwargs):
        self.fast_called = True
        return {'reuse': True, 'data': {'file_id': '200', 'pickcode': 'pc200'}}

    def multipart_upload(self, **_kwargs):
        self.multipart_called = True
        return {'data': {'file_id': '300', 'pickcode': 'pc300'}}


class FakeRemoteCacheService:
    def __init__(self, exists: bool = False, items: list[dict] | None = None) -> None:
        self.exists = exists
        self.items = items or []
        self.replaced = []
        self.upserts = []

    def get_dir_entries(self, remote_dir_id: int):
        return self.exists, list(self.items)

    def replace_dir_entries(self, **kwargs):
        self.replaced.append(kwargs)
        self.exists = True
        self.items = list(kwargs['items'])

    def upsert_file_entry(self, **kwargs):
        self.upserts.append(kwargs)


def make_candidate(tmp_path: Path, name: str = 'demo.mkv', content: bytes = b'hello world') -> LocalFileCandidate:
    file_path = tmp_path / name
    file_path.write_bytes(content)
    return LocalFileCandidate(
        absolute_path=file_path,
        relative_path=Path(name),
        suffix=file_path.suffix.lower(),
        size=file_path.stat().st_size,
    )


def test_upload_candidate_skips_when_remote_name_exists_from_cache(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=True, items=[{'id': '901', 'pickcode': 'pc901', 'name': 'demo.mkv', 'sha1': ''}])
    service = UploadStrategyService(gateway, cache)

    result = service.upload_candidate(candidate, '/remote', UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.NAME)

    assert result.action == FileAction.SKIPPED
    assert '按文件名匹配命中' in result.message
    assert result.remote_file_id == '901'
    assert gateway.fast_called is False
    assert gateway.multipart_called is False
    assert gateway.list_count == 0


def test_upload_candidate_skips_when_remote_sha1_exists(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[{'id': '902', 'pickcode': 'pc902', 'name': 'other.mkv', 'sha1': calc_sha1(candidate.absolute_path)}])
    cache = FakeRemoteCacheService(exists=False)
    service = UploadStrategyService(gateway, cache)

    result = service.upload_candidate(candidate, '/remote', UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.SHA1)

    assert result.action == FileAction.SKIPPED
    assert '按 SHA1匹配命中' in result.message
    assert result.remote_file_id == '902'
    assert gateway.fast_called is False
    assert cache.replaced


def test_upload_candidate_caches_remote_dir_listing(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=False)
    service = UploadStrategyService(gateway, cache)

    first = service.upload_candidate(candidate, '/remote', UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.NAME)
    second = service.upload_candidate(candidate, '/remote', UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.NAME)

    assert first.action == FileAction.FAST_UPLOADED
    assert second.action == FileAction.SKIPPED
    assert gateway.list_count == 1
    assert cache.upserts


def test_force_refresh_remote_cache_ignores_local_cache(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=True, items=[{'id': '1', 'pickcode': 'pc1', 'name': 'demo.mkv', 'sha1': ''}])
    service = UploadStrategyService(gateway, cache)

    result = service.upload_candidate(candidate, '/remote', UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.NAME, force_refresh_remote_cache=True)

    assert result.action == FileAction.FAST_UPLOADED
    assert gateway.list_count == 1
