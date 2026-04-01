"""系统设置接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=ApiResponse[SettingsRead])
def get_settings(db: Session = Depends(get_db)):
    service = SettingsService(db)
    return ApiResponse(data=service.get_settings())


@router.put("", response_model=ApiResponse[SettingsRead])
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    service = SettingsService(db)
    return ApiResponse(data=service.update_settings(payload))
