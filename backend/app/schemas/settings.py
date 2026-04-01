"""系统设置接口模型。"""

from pydantic import BaseModel


class SettingsRead(BaseModel):
    """返回给前端的系统设置。"""

    has_cookie_configured: bool
    sqlite_path: str
    default_part_size_mb: int
    default_max_workers: int


class SettingsUpdate(BaseModel):
    """可修改的系统设置。"""

    default_part_size_mb: int | None = None
    default_max_workers: int | None = None
