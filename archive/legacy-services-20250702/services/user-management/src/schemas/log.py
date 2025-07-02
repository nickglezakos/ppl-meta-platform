from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LogBase(BaseModel):
    level: str
    message: str
    logger_name: Optional[str] = None
    extra: Optional[str] = None

class LogCreate(LogBase):
    pass

class LogRead(LogBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True