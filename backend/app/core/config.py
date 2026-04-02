"""应用配置定义，统一管理环境变量与默认值。"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """后端运行配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "115 同步控制台"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    data_dir: Path = Field(default=Path("data"))
    db_dir: Path = Field(default=Path("db"))
    sqlite_path: Path = Field(default=Path("db/app.db"))
    log_level: str = "INFO"
    p115_cookies: str = ""
    p115_cookies_file: Path | None = None
    p115_check_for_relogin: bool = False
    p115_open_access_token: str = ""
    p115_open_refresh_token: str = ""
    default_part_size_mb: int = 10
    default_max_workers: int = 1
    frontend_dist: Path = Field(default=Path("frontend/dist"))

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.sqlite_path}"


@lru_cache
def get_settings() -> Settings:
    """返回全局单例配置。"""

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.db_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
