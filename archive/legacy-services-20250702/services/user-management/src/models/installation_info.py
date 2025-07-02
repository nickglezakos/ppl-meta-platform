from sqlalchemy import Column, String
from src.models.user import Base

class InstallationInfo(Base):
    __tablename__ = "installation_info"
    guid = Column(String, primary_key=True, unique=True, nullable=False)