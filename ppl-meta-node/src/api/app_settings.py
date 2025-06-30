from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.schemas.app_setting import AppSettingRead, AppSettingCreate
from src.services.app_setting_service import get_setting, set_setting
from src.database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/{key}", response_model=AppSettingRead)
def read_setting(key: str, db: Session = Depends(get_db)):
    setting = get_setting(db, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.post("/", response_model=AppSettingRead)
def update_setting(setting: AppSettingCreate, db: Session = Depends(get_db)):
    return set_setting(db, setting)