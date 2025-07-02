from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from src.schemas.log import LogRead
from src.services.log_service import get_logs
from src.database import get_db

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/", response_model=List[LogRead])
def api_get_logs(
    start: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(get_logs(db, skip=0, limit=100)[0].__class__)
    if start:
        query = query.filter(get_logs(db, skip=0, limit=100)[0].__class__.timestamp >= start)
    if end:
        query = query.filter(get_logs(db, skip=0, limit=100)[0].__class__.timestamp <= end)
    logs = query.order_by(get_logs(db, skip=0, limit=100)[0].__class__.timestamp.desc()).offset(skip).limit(limit).all()
    return logs