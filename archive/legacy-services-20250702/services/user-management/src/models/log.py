from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from src.models.user import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    logger_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    extra = Column(Text, nullable=True)  # For any extra data (JSON as string, etc.)