from sqlalchemy.orm import Session
from src.models.app_setting import AppSetting
from src.schemas.app_setting import AppSettingCreate

def get_setting(db: Session, key: str):
    return db.query(AppSetting).filter(AppSetting.key == key).first()

def set_setting(db: Session, setting: AppSettingCreate):
    db_setting = get_setting(db, setting.key)
    if db_setting:
        db_setting.value = setting.value
    else:
        db_setting = AppSetting(key=setting.key, value=setting.value)
        db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting