"""任务日志服务，负责写入与查询执行过程日志。"""

from __future__ import annotations

import asyncio
import re

from sqlalchemy.orm import Session

from app.models.task_log import TaskLog
from app.schemas.task_log import TaskLogRead
from app.services.task_log_stream_service import task_log_stream_service

SENSITIVE_PATTERNS = [
    re.compile(r"(UID|CID|SEID|KID)=[^;\s]+", re.IGNORECASE),
    re.compile(r"authorization[:=]\s*[^,\s]+", re.IGNORECASE),
]


class TaskLogService:
    """统一管理任务日志。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def sanitize(message: str) -> str:
        sanitized = message
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub("***", sanitized)
        return sanitized

    def log(self, *, run_id: int, source_id: int, level: str, stage: str, message: str) -> TaskLog:
        item = TaskLog(
            run_id=run_id,
            source_id=source_id,
            level=level.upper(),
            stage=stage,
            message=self.sanitize(message),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        payload = TaskLogRead.model_validate(item).model_dump(mode='json')
        task_log_stream_service.publish_sync(run_id, 'log', payload)
        return item


    def publish_status(self, *, run_id: int, source_id: int | None = None, status: str) -> None:
        payload = {"run_id": run_id, "status": status}
        if source_id is not None:
            payload["source_id"] = source_id
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            loop.create_task(task_log_stream_service.publish(run_id, 'status', payload))

    def list_by_run(self, run_id: int) -> list[TaskLogRead]:
        records = self.db.query(TaskLog).filter(TaskLog.run_id == run_id).order_by(TaskLog.id.asc()).all()
        return [TaskLogRead.model_validate(item) for item in records]
