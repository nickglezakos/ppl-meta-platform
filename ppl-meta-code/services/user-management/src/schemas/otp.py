from pydantic import BaseModel, constr
from datetime import datetime

OTPCode = constr(min_length=6, max_length=6)

class OTPCreate(BaseModel):
    user_id: int
    code: OTPCode

class OTPVerify(BaseModel):
    user_id: int
    code: constr(min_length=6, max_length=6)

class OTPRead(BaseModel):
    id: int
    user_id: int
    code: str
    expires_at: datetime
    used: bool

    class Config:
        orm_mode = True