from sqlalchemy import Boolean, Column, DateTime, Integer, String
from src.models.user import Base


class InstallationInfo(Base):
    __tablename__ = "installation_info"
    guid = Column(String, primary_key=True, unique=True, nullable=False)
    authority_application_key = Column(String, nullable=True)
    authority_installation_uuid = Column(String, nullable=True)
    authority_licence_name = Column(String, nullable=True)
    authority_tenant_name = Column(String, nullable=True)
    authority_approved_owner_email = Column(String, nullable=True)
    authority_licence_status = Column(String, nullable=True)
    authority_owner_enabled = Column(Boolean, nullable=True)
    authority_warning_period_days = Column(Integer, nullable=True)
    authority_warning_started_at = Column(DateTime, nullable=True)
    authority_offline_grace_days = Column(Integer, nullable=True)
    authority_last_checked_at = Column(DateTime, nullable=True)
    authority_last_successful_check_at = Column(DateTime, nullable=True)
    authority_last_result_reason = Column(String, nullable=True)