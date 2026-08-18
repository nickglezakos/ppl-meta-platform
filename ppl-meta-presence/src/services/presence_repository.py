from __future__ import annotations

import json
import logging
from typing import Dict, List

from sqlalchemy import inspect, select

from database import SessionLocal
from models.presence_models import (
    PresenceAnalyticsEvent,
    PresenceDecisionRecord,
    PresenceDetectionAttempt,
    PresencePeopleProfile,
    PresencePeopleProfileLink,
    PresenceProfile,
    PresenceResource,
    PresenceSession,
)


logger = logging.getLogger(__name__)
from models.persistence_models import (
    PresenceAnalyticsEventRecord,
    PresenceDecisionHistoryRecord,
    PresenceAttemptRecord,
    PresencePeopleProfileLinkRecord,
    PresencePeopleProfileRecord,
    PresenceProfileRecord,
    PresenceResourceRecord,
    PresenceSessionRecord,
)


class PresenceRepository:
    def _table_exists(self, db, table_name: str) -> bool:
        return inspect(db.bind).has_table(table_name)

    def load_sessions(self) -> Dict[str, PresenceSession]:
        with SessionLocal() as db:
            rows = db.execute(select(PresenceSessionRecord)).scalars().all()
            return {
                row.session_uuid: PresenceSession.model_validate(json.loads(row.payload_json))
                for row in rows
            }

    def load_attempts(self) -> Dict[str, List[PresenceDetectionAttempt]]:
        with SessionLocal() as db:
            rows = db.execute(
                select(PresenceAttemptRecord).order_by(
                    PresenceAttemptRecord.session_uuid,
                    PresenceAttemptRecord.attempt_index,
                )
            ).scalars().all()
            attempts: Dict[str, List[PresenceDetectionAttempt]] = {}
            for row in rows:
                attempts.setdefault(row.session_uuid, []).append(
                    PresenceDetectionAttempt.model_validate(json.loads(row.payload_json))
                )
            return attempts

    def load_resources(self, resource_type: str) -> Dict[str, PresenceResource]:
        with SessionLocal() as db:
            rows = db.execute(
                select(PresenceResourceRecord).where(
                    PresenceResourceRecord.resource_type == resource_type
                )
            ).scalars().all()
            return {
                row.resource_uuid: PresenceResource.model_validate(json.loads(row.payload_json))
                for row in rows
            }

    def load_profiles(self) -> Dict[str, PresenceProfile]:
        with SessionLocal() as db:
            rows = db.execute(select(PresenceProfileRecord)).scalars().all()
            return {
                row.presence_profile_uuid: PresenceProfile.model_validate(json.loads(row.payload_json))
                for row in rows
            }

    def load_analytics_events(self) -> List[PresenceAnalyticsEvent]:
        with SessionLocal() as db:
            rows = db.execute(select(PresenceAnalyticsEventRecord)).scalars().all()
            return [PresenceAnalyticsEvent.model_validate(json.loads(row.payload_json)) for row in rows]

    def load_decision_history(self) -> List[PresenceDecisionRecord]:
        with SessionLocal() as db:
            if not self._table_exists(db, PresenceDecisionHistoryRecord.__tablename__):
                logger.warning("Presence decision history table is missing; returning empty history until migrations are applied")
                return []
            rows = db.execute(
                select(PresenceDecisionHistoryRecord).order_by(PresenceDecisionHistoryRecord.session_uuid)
            ).scalars().all()
            return [PresenceDecisionRecord.model_validate(json.loads(row.payload_json)) for row in rows]

    def save_session(self, session: PresenceSession) -> None:
        with SessionLocal() as db:
            record = db.get(PresenceSessionRecord, session.session_uuid)
            if record is None:
                record = PresenceSessionRecord(session_uuid=session.session_uuid)
            record.payload_json = json.dumps(session.model_dump(mode="json"))
            record.updated_at = session.updated_at
            db.merge(record)
            db.commit()

    def save_attempt(self, attempt: PresenceDetectionAttempt) -> None:
        with SessionLocal() as db:
            record = db.get(PresenceAttemptRecord, attempt.attempt_uuid)
            if record is None:
                record = PresenceAttemptRecord(attempt_uuid=attempt.attempt_uuid)
            record.session_uuid = attempt.session_uuid
            record.attempt_index = attempt.attempt_index
            record.payload_json = json.dumps(attempt.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def save_resource(self, resource: PresenceResource) -> None:
        with SessionLocal() as db:
            record = db.get(PresenceResourceRecord, resource.resource_uuid)
            if record is None:
                record = PresenceResourceRecord(resource_uuid=resource.resource_uuid)
            record.resource_type = resource.resource_type
            record.payload_json = json.dumps(resource.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def delete_resources(self, resource_uuids: List[str]) -> None:
        if not resource_uuids:
            return

        with SessionLocal() as db:
            for resource_uuid in resource_uuids:
                record = db.get(PresenceResourceRecord, resource_uuid)
                if record is not None:
                    db.delete(record)
            db.commit()

    def save_profile(self, profile: PresenceProfile) -> None:
        with SessionLocal() as db:
            record = db.get(PresenceProfileRecord, profile.presence_profile_uuid)
            if record is None:
                record = PresenceProfileRecord(presence_profile_uuid=profile.presence_profile_uuid)
            record.profile_type = profile.profile_type
            record.payload_json = json.dumps(profile.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def save_analytics_event(self, event: PresenceAnalyticsEvent) -> None:
        with SessionLocal() as db:
            record = db.get(PresenceAnalyticsEventRecord, event.event_uuid)
            if record is None:
                record = PresenceAnalyticsEventRecord(event_uuid=event.event_uuid)
            record.session_uuid = event.session_uuid
            record.user_uuid = event.user_uuid
            record.device_uuid = event.device_uuid
            record.outcome = event.outcome
            record.payload_json = json.dumps(event.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def save_decision_record(self, decision_record: PresenceDecisionRecord) -> None:
        with SessionLocal() as db:
            if not self._table_exists(db, PresenceDecisionHistoryRecord.__tablename__):
                logger.warning("Presence decision history table is missing; skipping decision history persistence until migrations are applied")
                return
            record = db.get(PresenceDecisionHistoryRecord, decision_record.decision_uuid)
            if record is None:
                record = PresenceDecisionHistoryRecord(decision_uuid=decision_record.decision_uuid)
            record.session_uuid = decision_record.session_uuid
            record.user_uuid = decision_record.user_uuid
            record.device_uuid = decision_record.device_uuid
            record.decision = decision_record.decision.value
            record.payload_json = json.dumps(decision_record.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def load_people_profiles(self) -> Dict[str, PresencePeopleProfile]:
        with SessionLocal() as db:
            rows = db.execute(select(PresencePeopleProfileRecord)).scalars().all()
            return {
                row.ppp_uuid: PresencePeopleProfile.model_validate(json.loads(row.payload_json))
                for row in rows
            }

    def list_people_profile_links(self) -> List[PresencePeopleProfileLink]:
        with SessionLocal() as db:
            rows = db.execute(select(PresencePeopleProfileLinkRecord)).scalars().all()
            return [PresencePeopleProfileLink.model_validate(json.loads(row.payload_json)) for row in rows]

    def list_people_profile_links_for_ppp(self, ppp_uuid: str) -> List[PresencePeopleProfileLink]:
        with SessionLocal() as db:
            rows = db.execute(
                select(PresencePeopleProfileLinkRecord).where(
                    PresencePeopleProfileLinkRecord.ppp_uuid == ppp_uuid
                )
            ).scalars().all()
            return [PresencePeopleProfileLink.model_validate(json.loads(row.payload_json)) for row in rows]

    def save_people_profile(self, profile: PresencePeopleProfile) -> None:
        with SessionLocal() as db:
            record = db.get(PresencePeopleProfileRecord, profile.ppp_uuid)
            if record is None:
                record = PresencePeopleProfileRecord(ppp_uuid=profile.ppp_uuid)
            record.installation_uuid = profile.installation_uuid
            record.payload_json = json.dumps(profile.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def save_people_profile_link(self, link: PresencePeopleProfileLink) -> None:
        with SessionLocal() as db:
            record = db.get(PresencePeopleProfileLinkRecord, link.link_uuid) \
                if hasattr(link, "link_uuid") else None
            if record is None:
                from uuid import uuid5, NAMESPACE_URL
                link_uuid = str(uuid5(NAMESPACE_URL, f"{link.ppp_uuid}:{link.group_id}:{link.individual_id}"))
                record = PresencePeopleProfileLinkRecord(
                    link_uuid=link_uuid,
                    ppp_uuid=link.ppp_uuid,
                    group_id=link.group_id,
                    individual_id=link.individual_id,
                )
            record.payload_json = json.dumps(link.model_dump(mode="json"))
            db.merge(record)
            db.commit()

    def delete_people_profile_link(self, ppp_uuid: str, group_id: str, individual_id: str) -> bool:
        from uuid import uuid5, NAMESPACE_URL
        link_uuid = str(uuid5(NAMESPACE_URL, f"{ppp_uuid}:{group_id}:{individual_id}"))
        with SessionLocal() as db:
            record = db.get(PresencePeopleProfileLinkRecord, link_uuid)
            if record is None:
                return False
            db.delete(record)
            db.commit()
            return True