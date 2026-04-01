"""任务调度服务，负责 Cron 注册和手动触发。"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.models.enums import RunStatus, TriggerType
from app.models.run import JobRun
from app.models.source import SyncSource


@dataclass
class ScheduleSnapshot:
    """任务调度状态快照。"""

    is_scheduled: bool
    next_run_time: object | None
    last_run_at: object | None
    last_run_status: RunStatus | None


class SchedulerService:
    """统一管理 APScheduler 实例。"""

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(timezone='UTC')
        self.active_sources: set[int] = set()
        self._lock = Lock()
        if not self.scheduler.running:
            self.scheduler.start()

    def reserve_source(self, source_id: int) -> bool:
        with self._lock:
            if source_id in self.active_sources:
                return False
            self.active_sources.add(source_id)
            return True

    def is_reserved(self, source_id: int) -> bool:
        with self._lock:
            return source_id in self.active_sources

    def release_source(self, source_id: int) -> None:
        with self._lock:
            self.active_sources.discard(source_id)

    def can_start(self, source_id: int) -> bool:
        return self.reserve_source(source_id)

    def finish(self, source_id: int) -> None:
        self.release_source(source_id)

    def sync_source_jobs(self, sources: list[SyncSource]) -> None:
        expected_ids = {f'source:{source.id}' for source in sources if source.enabled and source.cron_expr}
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith('source:') and job.id not in expected_ids:
                self.scheduler.remove_job(job.id)

        for source in sources:
            job_id = f'source:{source.id}'
            if not source.enabled or not source.cron_expr:
                continue
            trigger = CronTrigger.from_crontab(source.cron_expr)
            self.scheduler.add_job(self._execute_source_job, trigger=trigger, id=job_id, replace_existing=True, kwargs={'source_id': source.id})

    def get_snapshot(self, db: Session, source_id: int) -> ScheduleSnapshot:
        job = self.scheduler.get_job(f'source:{source_id}')
        last_run = db.query(JobRun).filter(JobRun.source_id == source_id).order_by(JobRun.id.desc()).first()
        return ScheduleSnapshot(
            is_scheduled=job is not None,
            next_run_time=(job.next_run_time if job else None),
            last_run_at=(last_run.finished_at or last_run.started_at) if last_run else None,
            last_run_status=RunStatus(last_run.status) if last_run else None,
        )

    def _execute_source_job(self, source_id: int) -> None:
        from app.db.session import SessionLocal
        from app.services.async_run_executor import async_run_executor
        from app.services.run_service import RunService

        if not self.reserve_source(source_id):
            return
        db = SessionLocal()
        try:
            service = RunService(db)
            run = service.create_run(source_id, TriggerType.CRON)
            async_run_executor.submit_run(run.id)
        except Exception:
            self.release_source(source_id)
            raise
        finally:
            db.close()


scheduler_service = SchedulerService()
