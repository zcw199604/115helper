"""后台异步运行服务测试。"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.enums import TriggerType
from app.services.run_service import RunService


class DummyDB:
    def __init__(self, run=None, source=None):
        self.run = run
        self.source = source
        self.added = []

    def get(self, model, ident):
        name = getattr(model, '__name__', '')
        if name == 'JobRun':
            return self.run
        if name == 'SyncSource':
            return self.source
        return None

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None

    def refresh(self, item):
        if not getattr(item, 'created_at', None):
            item.created_at = datetime.now(timezone.utc)
        if not getattr(item, 'id', None):
            item.id = 99


def test_retry_run_async_creates_pending_run(monkeypatch):
    old_run = SimpleNamespace(id=1, source_id=7, status='failed')
    source = SimpleNamespace(id=7, name='任务A')
    db = DummyDB(run=old_run, source=source)
    service = RunService(db)
    monkeypatch.setattr('app.services.run_service.scheduler_service.is_reserved', lambda _id: False)
    monkeypatch.setattr('app.services.run_service.scheduler_service.reserve_source', lambda _id: True)
    monkeypatch.setattr(service.log_service, 'log', lambda **kwargs: None)
    monkeypatch.setattr(service.log_service, 'publish_status', lambda **kwargs: None)
    result = service.retry_run_async(1)
    assert result.source_id == 7
    assert result.trigger_type == TriggerType.RETRY
    assert result.status.value == 'pending'


def test_ensure_source_idle_raises_when_reserved(monkeypatch):
    service = RunService(DummyDB())
    monkeypatch.setattr('app.services.run_service.scheduler_service.is_reserved', lambda _id: True)
    with pytest.raises(HTTPException):
        service.ensure_source_idle(3)
