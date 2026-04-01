"""系统设置服务。"""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.app_setting import AppSetting
from app.schemas.settings import SettingsRead, SettingsUpdate


class SettingsService:
    """管理可持久化系统设置。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def get_settings(self) -> SettingsRead:
        return SettingsRead(
            has_cookie_configured=bool(self.settings.p115_cookies or self.settings.p115_cookies_file),
            sqlite_path=str(self.settings.sqlite_path),
            default_part_size_mb=int(self._get_value("default_part_size_mb", str(self.settings.default_part_size_mb))),
            default_max_workers=int(self._get_value("default_max_workers", str(self.settings.default_max_workers))),
        )

    def update_settings(self, payload: SettingsUpdate) -> SettingsRead:
        data = payload.model_dump(exclude_none=True)
        for key, value in data.items():
            setting = self.db.get(AppSetting, key) or AppSetting(key=key, value=str(value))
            setting.value = str(value)
            self.db.add(setting)
        self.db.commit()
        return self.get_settings()

    def _get_value(self, key: str, default: str) -> str:
        item = self.db.get(AppSetting, key)
        return item.value if item else default
