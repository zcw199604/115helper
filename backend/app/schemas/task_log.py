"""任务日志响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskLogRead(BaseModel):
    """任务日志返回模型。"""

    id: int
    run_id: int
    source_id: int
    level: str
    stage: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
