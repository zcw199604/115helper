"""可中断后台任务测试。"""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.async_run_executor import AsyncRunExecutorService
from app.services.run_service import RunService


class DummyDB:
    def __init__(self, run=None, source=None):
        self.run = run
        self.source = source

    def get(self, model, ident):
        name = getattr(model, '__name__', '')
        if name == 'JobRun':
            return self.run
        if name == 'SyncSource':
            return self.source
        return None

    def add(self, _item):
        return None

    def commit(self):
        return None

    def refresh(self, item):
        if not getattr(item, 'created_at', None):
            item.created_at = datetime.now(timezone.utc)

    class Query:
        def filter(self, *_args, **_kwargs):
            return self
        def order_by(self, *_args, **_kwargs):
            return []

    def query(self, *_args, **_kwargs):
        return self.Query()


def test_async_executor_cancel_flag_lifecycle():
    executor = AsyncRunExecutorService()
    executor.request_cancel(10)
    assert executor.is_cancel_requested(10) is True
    executor.clear_run(10)
    assert executor.is_cancel_requested(10) is False


def test_cancel_pending_run_cancels_immediately(monkeypatch):
    run = SimpleNamespace(id=1, source_id=2, status='pending', finished_at=None, started_at=None, summary_json='{}', trigger_type='manual', error_message=None, created_at=datetime.now(timezone.utc))
    source = SimpleNamespace(id=2, name='任务A')
    service = RunService(DummyDB(run=run, source=source))
    monkeypatch.setattr('app.services.run_service.async_run_executor.request_cancel', lambda _id: None)
    monkeypatch.setattr('app.services.run_service.async_run_executor.clear_run', lambda _id: None)
    monkeypatch.setattr('app.services.run_service.scheduler_service.release_source', lambda _id: None)
    monkeypatch.setattr(service.log_service, 'log', lambda **kwargs: None)
    monkeypatch.setattr(service.log_service, 'publish_status', lambda **kwargs: None)
    result = service.cancel_run(1)
    assert result.status.value == 'cancelled'
