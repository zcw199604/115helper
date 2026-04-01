"""任务运行相关请求与响应模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import FileAction, RunStatus, TriggerType
from app.schemas.task_log import TaskLogRead


class RunCreateRequest(BaseModel):
    """手动执行参数。"""

    retry_failed_only: bool = False


class FileRecordRead(BaseModel):
    """文件记录返回模型。"""

    id: int
    relative_path: str
    file_size: int
    file_sha1: str | None
    suffix: str
    action: FileAction
    remote_file_id: str | None
    remote_pickcode: str | None
    message: str | None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunRead(BaseModel):
    """运行记录返回模型。"""

    id: int
    source_id: int
    source_name: str
    trigger_type: TriggerType
    status: RunStatus
    started_at: datetime | None
    finished_at: datetime | None
    summary: dict[str, Any]
    error_message: str | None
    created_at: datetime


class RunDetail(RunRead):
    """运行详情。"""

    records: list[FileRecordRead]
    logs: list[TaskLogRead]
