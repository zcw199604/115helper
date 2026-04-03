"""同步源仓储。"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source import SyncSource
from app.schemas.source import SourceCreate, SourceUpdate


class SourceRepository:
    """封装同步源数据库操作。"""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[SyncSource]:
        return list(self.db.scalars(select(SyncSource).order_by(SyncSource.id.desc())))

    def get(self, source_id: int) -> SyncSource | None:
        return self.db.get(SyncSource, source_id)

    def create(self, payload: SourceCreate) -> SyncSource:
        source = SyncSource(
            name=payload.name,
            local_path=payload.local_path,
            remote_path=payload.remote_path,
            upload_mode=payload.upload_mode.value,
            upload_flow_mode=payload.upload_flow_mode.value,
            suffix_rules_json=json.dumps(payload.suffix_rules, ensure_ascii=False),
            exclude_rules_json=json.dumps(payload.exclude_rules, ensure_ascii=False),
            cron_expr=payload.cron_expr,
            enabled=1 if payload.enabled else 0,
            skip_existing_remote=1 if payload.duplicate_check_mode.value != 'none' else 0,
            duplicate_check_mode=payload.duplicate_check_mode.value,
            force_refresh_remote_cache=1 if payload.force_refresh_remote_cache else 0,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def update(self, source: SyncSource, payload: SourceUpdate) -> SyncSource:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key in {"upload_mode", "upload_flow_mode"} and value is not None:
                setattr(source, key, value.value)
            elif key == "suffix_rules" and value is not None:
                source.suffix_rules_json = json.dumps(value, ensure_ascii=False)
            elif key == "exclude_rules" and value is not None:
                source.exclude_rules_json = json.dumps(value, ensure_ascii=False)
            elif key == "enabled" and value is not None:
                source.enabled = 1 if value else 0
            elif key == 'duplicate_check_mode' and value is not None:
                source.duplicate_check_mode = value.value
                source.skip_existing_remote = 1 if value.value != 'none' else 0
            elif key == 'force_refresh_remote_cache' and value is not None:
                source.force_refresh_remote_cache = 1 if value else 0
            else:
                setattr(source, key, value)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete(self, source: SyncSource) -> None:
        self.db.delete(source)
        self.db.commit()
