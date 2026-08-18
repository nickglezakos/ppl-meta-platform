from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PresenceSessionRecord(Base):
    __tablename__ = "presence_sessions"

    session_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PresenceAttemptRecord(Base):
    __tablename__ = "presence_attempts"

    attempt_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PresenceResourceRecord(Base):
    __tablename__ = "presence_resources"

    resource_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PresenceProfileRecord(Base):
    __tablename__ = "presence_profiles"

    presence_profile_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PresenceAnalyticsEventRecord(Base):
    __tablename__ = "presence_analytics_events"

    event_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PresenceDecisionHistoryRecord(Base):
    __tablename__ = "presence_decision_history"

    decision_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PresencePeopleProfileRecord(Base):
    __tablename__ = "presence_people_profiles"

    ppp_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    installation_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class PresencePeopleProfileLinkRecord(Base):
    __tablename__ = "presence_people_profile_links"

    link_uuid: Mapped[str] = mapped_column(String(64), primary_key=True)
    ppp_uuid: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    group_id: Mapped[str] = mapped_column(String(255), nullable=False)
    individual_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)