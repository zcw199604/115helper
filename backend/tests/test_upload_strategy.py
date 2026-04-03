"""上传策略测试。"""

from pathlib import Path, PurePosixPath

from app.models.enums import DuplicateCheckMode, FileAction, UploadMode
from app.services.sync_scanner import LocalFileCandidate, calc_sha1
from app.services.upload_strategy import UploadStrategyService


class FakeGateway:
    def __init__(self, items: list[dict] | None = None) -> None:
        self.items = items or []
        self.fast_called = False
        self.multipart_called = False
        self.list_count = 0
        self.ensure_count = 0
        self.plugin_ensure_calls: list[str] = []
        self.known_dirs = {'/remote': 100}
        self.files_by_path: dict[str, dict] = {}

    def get_dir_id_by_path(self, remote_dir: PurePosixPath):
        return self.known_dirs.get(remote_dir.as_posix(), 0)

    def ensure_remote_dir(self, remote_dir):
        self.ensure_count += 1
        path = remote_dir.as_posix()
        self.known_dirs[path] = 100
        return 100

    def ensure_remote_dir_plugin_style(self, remote_dir: PurePosixPath):
        path = remote_dir.as_posix()
        self.plugin_ensure_calls.append(path)
        self.known_dirs[path] = len(self.known_dirs) + 100
        return self.known_dirs[path]

    def list_remote_dir_files(self, *, pid: int):
        self.list_count += 1
        assert pid in self.known_dirs.values()
        return list(self.items)

    def fast_upload_init(self, **_kwargs):
        self.fast_called = True
        return {'reuse': True, 'data': {'file_id': '200', 'pickcode': 'pc200'}}

    def multipart_upload(self, **_kwargs):
        self.multipart_called = True
        return {'data': {'file_id': '300', 'pickcode': 'pc300'}}

    def get_remote_file_by_path(self, remote_file_path: PurePosixPath):
        return self.files_by_path.get(remote_file_path.as_posix())


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
    context = service.prepare_dir_context(remote_dir_path='/remote', force_refresh_remote_cache=False)

    result = service.upload_candidate_in_context(candidate, context, UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.NAME)

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
    context = service.prepare_dir_context(remote_dir_path='/remote', force_refresh_remote_cache=False)

    result = service.upload_candidate_in_context(candidate, context, UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.SHA1)

    assert result.action == FileAction.SKIPPED
    assert '按 SHA1匹配命中' in result.message
    assert result.remote_file_id == '902'
    assert gateway.fast_called is False
    assert cache.replaced


def test_prepare_context_caches_remote_dir_listing(tmp_path: Path) -> None:
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=False)
    service = UploadStrategyService(gateway, cache)

    first = service.prepare_dir_context(remote_dir_path='/remote', force_refresh_remote_cache=False)
    second = service.prepare_dir_context(remote_dir_path='/remote', force_refresh_remote_cache=False)

    assert first.remote_dir_id == 100
    assert second.remote_dir_id == 100
    assert gateway.list_count == 1


def test_force_refresh_remote_cache_ignores_local_cache(tmp_path: Path) -> None:
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=True, items=[{'id': '1', 'pickcode': 'pc1', 'name': 'demo.mkv', 'sha1': ''}])
    service = UploadStrategyService(gateway, cache)

    context = service.prepare_dir_context(remote_dir_path='/remote', force_refresh_remote_cache=True)

    assert context.remote_dir_id == 100
    assert gateway.list_count == 1


def test_name_mode_skip_does_not_calculate_sha1(tmp_path: Path, monkeypatch) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=True, items=[{'id': '901', 'pickcode': 'pc901', 'name': 'demo.mkv', 'sha1': ''}])
    service = UploadStrategyService(gateway, cache)
    context = service.prepare_dir_context(remote_dir_path='/remote', force_refresh_remote_cache=False)

    def fail_calc(_path):
        raise AssertionError('name 模式命中时不应计算 SHA1')

    monkeypatch.setattr('app.services.upload_strategy.calc_sha1', fail_calc)
    result = service.upload_candidate_in_context(candidate, context, UploadMode.FAST_THEN_MULTIPART, duplicate_check_mode=DuplicateCheckMode.NAME)
    assert result.action == FileAction.SKIPPED


def test_prepare_plugin_aligned_context_creates_missing_dir_without_listing(tmp_path: Path) -> None:
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=False)
    service = UploadStrategyService(gateway, cache)

    context = service.prepare_plugin_aligned_context(
        remote_dir_path='/remote/new/sub',
        duplicate_check_mode=DuplicateCheckMode.NONE,
        force_refresh_remote_cache=False,
    )

    assert context.remote_dir_path == '/remote/new/sub'
    assert context.items == []
    assert gateway.plugin_ensure_calls == ['/remote/new/sub']
    assert gateway.list_count == 0


def test_verify_uploaded_file_updates_cache(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[])
    gateway.files_by_path['/remote/demo.mkv'] = {'id': '901', 'pickcode': 'pc901', 'name': 'demo.mkv', 'sha1': calc_sha1(candidate.absolute_path), 'size': candidate.size}
    cache = FakeRemoteCacheService(exists=False)
    service = UploadStrategyService(gateway, cache)
    context = service.prepare_plugin_aligned_context(
        remote_dir_path='/remote',
        duplicate_check_mode=DuplicateCheckMode.NONE,
        force_refresh_remote_cache=False,
    )

    verified = service.verify_uploaded_file(
        remote_file_path='/remote/demo.mkv',
        context=context,
        file_sha1=calc_sha1(candidate.absolute_path),
        size=candidate.size,
    )

    assert verified is not None
    assert verified['id'] == '901'
    assert cache.upserts[-1]['remote_file_id'] == '901'


def test_verify_uploaded_file_uses_plugin_style_backoff(tmp_path: Path, monkeypatch) -> None:
    candidate = make_candidate(tmp_path)
    gateway = FakeGateway(items=[])
    cache = FakeRemoteCacheService(exists=False)
    service = UploadStrategyService(gateway, cache)
    context = service.prepare_plugin_aligned_context(
        remote_dir_path='/remote',
        duplicate_check_mode=DuplicateCheckMode.NONE,
        force_refresh_remote_cache=False,
    )

    delays: list[float] = []
    call_count = {'value': 0}

    def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    def fake_get_item(_path: PurePosixPath):
        call_count['value'] += 1
        if call_count['value'] == 3:
            return {'id': '903', 'pickcode': 'pc903', 'name': 'demo.mkv', 'sha1': calc_sha1(candidate.absolute_path), 'size': candidate.size}
        return None

    monkeypatch.setattr('app.services.upload_strategy.sleep', fake_sleep)
    gateway.get_remote_file_by_path = fake_get_item

    verified = service.verify_uploaded_file(
        remote_file_path='/remote/demo.mkv',
        context=context,
        file_sha1=calc_sha1(candidate.absolute_path),
        size=candidate.size,
    )

    assert verified is not None
    assert delays == [2.0, 4.0, 8.0]
