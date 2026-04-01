"""任务日志服务测试。"""

from app.services.task_log_service import TaskLogService


class DummySession:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def commit(self):
        return None

    def refresh(self, item):
        item.id = len(self.items)
        from datetime import datetime, timezone
        item.created_at = datetime.now(timezone.utc)

    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return []

    def query(self, *_args, **_kwargs):
        return self.Query()


def test_task_log_service_sanitizes_sensitive_message() -> None:
    service = TaskLogService(DummySession())
    message = 'UID=abc; CID=def authorization: token123'
    assert 'UID=' not in service.sanitize(message)
    assert 'authorization' not in service.sanitize(message).lower()


def test_task_log_service_dispatches_stream_event(monkeypatch) -> None:
    captured = []

    def fake_publish_sync(run_id: int, event: str, payload: dict):
        captured.append((run_id, event, payload))

    monkeypatch.setattr('app.services.task_log_service.task_log_stream_service.publish_sync', fake_publish_sync)
    service = TaskLogService(DummySession())
    service.log(run_id=2, source_id=1, level='INFO', stage='scan', message='hello')
    assert captured
    assert captured[0][0] == 2
    assert captured[0][1] == 'log'
