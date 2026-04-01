"""同步源相关请求与响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DuplicateCheckMode, RunStatus, UploadMode


class SourceBase(BaseModel):
    """同步源基础字段。"""

    name: str = Field(min_length=1, max_length=100)
    local_path: str = Field(min_length=1)
    remote_path: str = Field(min_length=1)
    upload_mode: UploadMode
    suffix_rules: list[str] = Field(default_factory=list)
    exclude_rules: list[str] = Field(default_factory=list)
    cron_expr: str | None = None
    enabled: bool = True
    duplicate_check_mode: DuplicateCheckMode = DuplicateCheckMode.NONE

    @field_validator("suffix_rules", mode="before")
    @classmethod
    def normalize_suffix_rules(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        normalized = []
        for item in value:
            item = item.strip().lower()
            if not item:
                continue
            if not item.startswith("."):
                item = f".{item}"
            normalized.append(item)
        return list(dict.fromkeys(normalized))

    @field_validator("exclude_rules", mode="before")
    @classmethod
    def normalize_exclude_rules(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("remote_path")
    @classmethod
    def normalize_remote_path(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = f"/{value}"
        return value.rstrip("/") or "/"

    @field_validator("cron_expr")
    @classmethod
    def normalize_cron_expr(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class SourceCreate(SourceBase):
    """创建同步源。"""


class SourceUpdate(BaseModel):
    """更新同步源。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    local_path: str | None = None
    remote_path: str | None = None
    upload_mode: UploadMode | None = None
    suffix_rules: list[str] | None = None
    exclude_rules: list[str] | None = None
    cron_expr: str | None = None
    enabled: bool | None = None
    duplicate_check_mode: DuplicateCheckMode | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("suffix_rules", mode="before")
    @classmethod
    def normalize_suffix_rules(cls, value):
        return SourceBase.normalize_suffix_rules(value)

    @field_validator("exclude_rules", mode="before")
    @classmethod
    def normalize_exclude_rules(cls, value):
        return SourceBase.normalize_exclude_rules(value)

    @field_validator("remote_path")
    @classmethod
    def normalize_remote_path(cls, value):
        if value is None:
            return None
        return SourceBase.normalize_remote_path(value)

    @field_validator("cron_expr")
    @classmethod
    def normalize_cron_expr(cls, value):
        return SourceBase.normalize_cron_expr(value)


class ScheduleState(BaseModel):
    """任务调度状态。"""

    is_scheduled: bool = False
    next_run_time: datetime | None = None
    last_run_at: datetime | None = None
    last_run_status: RunStatus | None = None


class SourceRead(SourceBase):
    """同步源返回模型。"""

    id: int
    created_at: datetime
    updated_at: datetime
    schedule_state: ScheduleState = Field(default_factory=ScheduleState)

    model_config = ConfigDict(from_attributes=True)


class ToggleTaskRequest(BaseModel):
    """任务启停请求。"""

    enabled: bool
