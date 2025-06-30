from pydantic import BaseModel

class AppSettingBase(BaseModel):
    key: str
    value: str

class AppSettingCreate(AppSettingBase):
    pass

class AppSettingRead(AppSettingBase):
    id: int

    class Config:
        orm_mode = True