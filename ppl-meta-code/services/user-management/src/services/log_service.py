from sqlalchemy.orm import Session
from src.models.log import Log
from src.schemas.log import LogCreate

def create_log(db: Session, log_data: LogCreate) -> Log:
    log = Log(**log_data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Log).order_by(Log.timestamp.desc()).offset(skip).limit(limit).all()

def get_log_by_id(db: Session, log_id: int) -> Log | None:
    return db.query(Log).filter(Log.id == log_id).first()