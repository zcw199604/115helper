"""调度服务测试。"""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.enums import RunStatus
from app.services.scheduler_service import SchedulerService


class FakeQuery:
    def __init__(self, item):
        self.item = item

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.item


class FakeSession:
    def __init__(self, item):
        self.item = item

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.item)


def test_scheduler_running_guard() -> None:
    service = SchedulerService()
    try:
        assert service.can_start(1) is True
        assert service.can_start(1) is False
        service.finish(1)
        assert service.can_start(1) is True
    finally:
        if service.scheduler.running:
            service.scheduler.shutdown(wait=False)


def test_get_snapshot_contains_last_run() -> None:
    service = SchedulerService()
    try:
        item = SimpleNamespace(status='success', finished_at=datetime.now(timezone.utc), started_at=None)
        snapshot = service.get_snapshot(FakeSession(item), 1)
        assert snapshot.last_run_status == RunStatus.SUCCESS
    finally:
        if service.scheduler.running:
            service.scheduler.shutdown(wait=False)
