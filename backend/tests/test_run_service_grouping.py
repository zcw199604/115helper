"""运行服务目录分组测试。"""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.services.run_service import RunService


class DummyQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return []


class DummyDB:
    def __init__(self, run, source):
        self.run = run
        self.source = source
        self.added = []

    def get(self, model, _ident):
        if getattr(model, '__name__', '') == 'JobRun':
            return self.run
        if getattr(model, '__name__', '') == 'SyncSource':
            return self.source
        return None

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None

    def refresh(self, _item):
        return None

    def query(self, *_args, **_kwargs):
        return DummyQuery()


class FakeUploader:
    prepared_paths = []

    def __init__(self, *_args, **_kwargs):
        pass

    @staticmethod
    def resolve_remote_dir_path(remote_root, candidate):
        return f"{remote_root}/{candidate.relative_path.parent.as_posix()}" if str(candidate.relative_path.parent) != '.' else remote_root

    def prepare_dir_context(self, *, remote_dir_path, force_refresh_remote_cache, log=None):
        self.prepared_paths.append(remote_dir_path)
        return SimpleNamespace(remote_dir_id=len(self.prepared_paths), remote_dir_path=remote_dir_path, items=[])

    def upload_candidate_in_context(self, candidate, context, upload_mode, *, duplicate_check_mode):
        return SimpleNamespace(action=SimpleNamespace(value='skipped'), message='ok', file_sha1=None, remote_file_id=None, remote_pickcode=None)


def test_execute_run_groups_candidates_by_remote_dir(monkeypatch, tmp_path: Path):
    run = SimpleNamespace(id=1, source_id=2, status='pending', finished_at=None, started_at=None, summary_json='{}', trigger_type='manual', error_message=None, created_at=datetime.now(timezone.utc))
    source = SimpleNamespace(id=2, name='任务A', local_path=str(tmp_path), remote_path='/remote', upload_mode='fast_then_multipart', suffix_rules_json='[]', exclude_rules_json='[]', duplicate_check_mode='name', skip_existing_remote=1, force_refresh_remote_cache=0)
    db = DummyDB(run, source)
    service = RunService(db)

    candidates = [
        SimpleNamespace(relative_path=Path('Season 1/a.mkv'), absolute_path=tmp_path / 'a.mkv', suffix='.mkv', size=1),
        SimpleNamespace(relative_path=Path('Season 1/b.mkv'), absolute_path=tmp_path / 'b.mkv', suffix='.mkv', size=1),
        SimpleNamespace(relative_path=Path('Season 2/c.mkv'), absolute_path=tmp_path / 'c.mkv', suffix='.mkv', size=1),
    ]

    monkeypatch.setattr('app.services.run_service.scan_local_files', lambda *_args, **_kwargs: candidates)
    monkeypatch.setattr('app.services.run_service.P115Gateway', lambda: object())
    monkeypatch.setattr('app.services.run_service.UploadStrategyService', FakeUploader)
    monkeypatch.setattr('app.services.run_service.scheduler_service.is_reserved', lambda _id: False)
    monkeypatch.setattr('app.services.run_service.scheduler_service.reserve_source', lambda _id: True)
    monkeypatch.setattr('app.services.run_service.scheduler_service.release_source', lambda _id: None)
    monkeypatch.setattr('app.services.run_service.async_run_executor.is_cancel_requested', lambda _id: False)
    monkeypatch.setattr(service.log_service, 'log', lambda **kwargs: None)
    monkeypatch.setattr(service.log_service, 'publish_status', lambda **kwargs: None)

    FakeUploader.prepared_paths = []
    service.execute_run(1)

    assert FakeUploader.prepared_paths == ['/remote/Season 1', '/remote/Season 2']
