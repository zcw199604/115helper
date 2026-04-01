"""同步源服务，负责 DTO 转换和调度刷新。"""

import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.source_repository import SourceRepository
from app.schemas.source import ScheduleState, SourceCreate, SourceRead, SourceUpdate
from app.services.scheduler_service import scheduler_service


class SourceService:
    """同步源业务服务。"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SourceRepository(db)

    def _to_read_model(self, source) -> SourceRead:
        snapshot = scheduler_service.get_snapshot(self.db, source.id)
        return SourceRead(
            id=source.id,
            name=source.name,
            local_path=source.local_path,
            remote_path=source.remote_path,
            upload_mode=source.upload_mode,
            suffix_rules=json.loads(source.suffix_rules_json or "[]"),
            exclude_rules=json.loads(source.exclude_rules_json or "[]"),
            cron_expr=source.cron_expr,
            enabled=bool(source.enabled),
            created_at=source.created_at,
            updated_at=source.updated_at,
            schedule_state=ScheduleState(
                is_scheduled=snapshot.is_scheduled,
                next_run_time=snapshot.next_run_time,
                last_run_at=snapshot.last_run_at,
                last_run_status=snapshot.last_run_status,
            ),
        )

    def _refresh_scheduler(self) -> None:
        scheduler_service.sync_source_jobs(self.repo.list_all())

    def list_sources(self) -> list[SourceRead]:
        return [self._to_read_model(item) for item in self.repo.list_all()]

    def get_source_or_404(self, source_id: int):
        source = self.repo.get(source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="同步任务不存在")
        return source

    def create_source(self, payload: SourceCreate) -> SourceRead:
        if not Path(payload.local_path).exists():
            raise HTTPException(status_code=400, detail="本地目录不存在")
        source = self.repo.create(payload)
        self._refresh_scheduler()
        return self._to_read_model(source)

    def update_source(self, source_id: int, payload: SourceUpdate) -> SourceRead:
        source = self.get_source_or_404(source_id)
        if payload.local_path and not Path(payload.local_path).exists():
            raise HTTPException(status_code=400, detail="本地目录不存在")
        source = self.repo.update(source, payload)
        self._refresh_scheduler()
        return self._to_read_model(source)

    def delete_source(self, source_id: int) -> None:
        source = self.get_source_or_404(source_id)
        self.repo.delete(source)
        self._refresh_scheduler()

    def toggle_enabled(self, source_id: int, enabled: bool) -> SourceRead:
        source = self.get_source_or_404(source_id)
        source.enabled = 1 if enabled else 0
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        self._refresh_scheduler()
        return self._to_read_model(source)
