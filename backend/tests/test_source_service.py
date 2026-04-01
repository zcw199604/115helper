"""同步任务服务测试。"""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.enums import DuplicateCheckMode, RunStatus
from app.schemas.source import ScheduleState
from app.services.source_service import SourceService


class FakeRepo:
    def list_all(self):
        return []


class FakeService(SourceService):
    def __init__(self):
        self.db = None
        self.repo = FakeRepo()


def test_to_read_model_contains_schedule_state(monkeypatch) -> None:
    service = FakeService()
    source = SimpleNamespace(
        id=1,
        name='任务A',
        local_path='/tmp/a',
        remote_path='/remote/a',
        upload_mode='fast_only',
        suffix_rules_json='[".mkv"]',
        exclude_rules_json='[]',
        cron_expr='0 * * * *',
        enabled=1,
        skip_existing_remote=1,
        duplicate_check_mode='name',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr('app.services.source_service.scheduler_service.get_snapshot', lambda _db, _id: ScheduleState(is_scheduled=True, next_run_time=None, last_run_at=None, last_run_status=RunStatus.SUCCESS))
    result = service._to_read_model(source)
    assert result.schedule_state.is_scheduled is True
    assert result.schedule_state.last_run_status == RunStatus.SUCCESS
    assert result.duplicate_check_mode == DuplicateCheckMode.NAME
