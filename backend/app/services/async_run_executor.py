"""后台运行执行器，负责将运行记录提交到后台线程执行。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

from app.core.config import get_settings
from app.db.session import SessionLocal


class AsyncRunExecutorService:
    """使用进程内线程池执行后台任务，并维护取消信号。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.executor = ThreadPoolExecutor(max_workers=max(1, settings.default_max_workers), thread_name_prefix='run-worker')
        self._submitted_runs: set[int] = set()
        self._cancel_events: dict[int, Event] = {}
        self._lock = Lock()

    def submit_run(self, run_id: int) -> None:
        with self._lock:
            if run_id in self._submitted_runs:
                return
            self._submitted_runs.add(run_id)
            self._cancel_events.setdefault(run_id, Event())
        self.executor.submit(self._execute_run, run_id)

    def request_cancel(self, run_id: int) -> None:
        with self._lock:
            event = self._cancel_events.setdefault(run_id, Event())
            event.set()

    def is_cancel_requested(self, run_id: int) -> bool:
        with self._lock:
            event = self._cancel_events.get(run_id)
            return bool(event and event.is_set())

    def clear_run(self, run_id: int) -> None:
        with self._lock:
            self._submitted_runs.discard(run_id)
            self._cancel_events.pop(run_id, None)

    def _execute_run(self, run_id: int) -> None:
        from app.services.run_service import RunService

        db = SessionLocal()
        try:
            service = RunService(db)
            service.execute_run(run_id)
        finally:
            db.close()
            self.clear_run(run_id)


async_run_executor = AsyncRunExecutorService()
