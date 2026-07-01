"""Matrix Service — business logic for group management, membership, and auto-creation."""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.database import (
    MatrixGroup,
    MatrixInstallationMembership,
    MatrixUser,
    MatrixUserCapability,
    SessionLocal,
)

logger = logging.getLogger(__name__)

# Matrix capabilities constant (matches proposal Section 5.4.3)
MATRIX_CAPABILITIES = {
    "matrix:view_reports": "View aggregated reports across all member installations",
    "matrix:manage_group": "Create, update, delete Matrix groups; manage installation memberships",
    "matrix:manage_users": "Add/remove users from the Matrix directory; assign capabilities",
    "matrix:view_logs": "View aggregated log reports",
    "matrix:admin": "Full administrative access (all of the above)",
}


class MatrixService:
    """Core Matrix business logic."""

    # ------------------------------------------------------------------
    # Phase 1: Auto-creation
    # ------------------------------------------------------------------

    def auto_create_default_group(self) -> Optional[MatrixGroup]:
        """Auto-create a single-member Matrix group on first boot.

        Returns the created/existing group, or None on failure.
        """
        db = SessionLocal()
        try:
            existing = db.query(MatrixGroup).first()
            if existing:
                logger.info("Matrix group already exists: %s", existing.name)
                return existing

            # Create default group
            group = MatrixGroup(
                name=os.environ.get("MATRIX_GROUP_NAME", "Default Matrix"),
                description="Auto-created single-installation Matrix group",
                licence_multi_install=False,
            )
            db.add(group)
            db.flush()

            # Add this installation as the sole member
            installation_uuid = self._get_local_installation_uuid()
            membership = MatrixInstallationMembership(
                matrix_group_id=group.id,
                installation_uuid=installation_uuid,
                installation_name=os.environ.get("INSTALLATION_NAME", "Primary Installation"),
                node_url=f"http://localhost:8000",
            )
            db.add(membership)
            db.commit()

            logger.info("Auto-created Matrix group '%s' with installation %s", group.name, installation_uuid)
            return group

        except Exception as exc:
            db.rollback()
            logger.error("Failed to auto-create default Matrix group: %s", exc)
            return None
        finally:
            db.close()

    def _get_local_installation_uuid(self) -> str:
        """Get the local installation UUID from the node's database or generate one."""
        try:
            # Try reading from node's SQLite database
            import sqlite3
            node_db = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ppl-meta-node", "database", "ppl_meta_node.db")
            if os.path.exists(node_db):
                conn = sqlite3.connect(node_db)
                cursor = conn.execute("SELECT guid FROM installation_info LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                if row:
                    return row[0]
        except Exception:
            pass

        # Fallback: generate a unique ID
        return f"matrix-{uuid.uuid4().hex[:12]}"

    # ------------------------------------------------------------------
    # Phase 2: Group CRUD
    # ------------------------------------------------------------------

    def create_group(self, name: str, description: str = "", multi_install: bool = False) -> MatrixGroup:
        db = SessionLocal()
        try:
            group = MatrixGroup(name=name, description=description, licence_multi_install=multi_install)
            db.add(group)
            db.commit()
            db.refresh(group)
            logger.info("Created Matrix group: %s (multi_install=%s)", name, multi_install)
            return group
        except Exception as exc:
            db.rollback()
            logger.error("Failed to create group: %s", exc)
            raise
        finally:
            db.close()

    def list_groups(self) -> list[MatrixGroup]:
        db = SessionLocal()
        try:
            return db.query(MatrixGroup).all()
        finally:
            db.close()

    def get_group(self, group_id: str) -> Optional[MatrixGroup]:
        db = SessionLocal()
        try:
            return db.query(MatrixGroup).filter(MatrixGroup.id == uuid.UUID(group_id)).first()
        finally:
            db.close()

    def update_group(self, group_id: str, name: str = None, description: str = None) -> Optional[MatrixGroup]:
        db = SessionLocal()
        try:
            group = db.query(MatrixGroup).filter(MatrixGroup.id == uuid.UUID(group_id)).first()
            if not group:
                return None
            if name is not None:
                group.name = name
            if description is not None:
                group.description = description
            group.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(group)
            return group
        except Exception as exc:
            db.rollback()
            logger.error("Failed to update group %s: %s", group_id, exc)
            raise
        finally:
            db.close()

    def delete_group(self, group_id: str) -> bool:
        db = SessionLocal()
        try:
            group = db.query(MatrixGroup).filter(MatrixGroup.id == uuid.UUID(group_id)).first()
            if not group:
                return False
            db.delete(group)
            db.commit()
            logger.info("Deleted Matrix group: %s", group_id)
            return True
        except Exception as exc:
            db.rollback()
            logger.error("Failed to delete group %s: %s", group_id, exc)
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Phase 2: Membership management
    # ------------------------------------------------------------------

    def add_installation(self, group_id: str, installation_uuid: str,
                         installation_name: str = "", node_url: str = "") -> MatrixInstallationMembership:
        db = SessionLocal()
        try:
            # Check if group allows multi-install
            group = db.query(MatrixGroup).filter(MatrixGroup.id == uuid.UUID(group_id)).first()
            if not group:
                raise ValueError(f"Group {group_id} not found")
            if not group.licence_multi_install:
                existing = db.query(MatrixInstallationMembership).filter(
                    MatrixInstallationMembership.matrix_group_id == uuid.UUID(group_id)
                ).count()
                if existing >= 1:
                    raise ValueError("Group does not allow multiple installations (licence_multi_install=false)")

            membership = MatrixInstallationMembership(
                matrix_group_id=uuid.UUID(group_id),
                installation_uuid=installation_uuid,
                installation_name=installation_name,
                node_url=node_url or f"http://localhost:8000",
            )
            db.add(membership)
            db.commit()
            db.refresh(membership)
            logger.info("Added installation %s to group %s", installation_uuid, group_id)
            return membership
        except Exception as exc:
            db.rollback()
            logger.error("Failed to add installation: %s", exc)
            raise
        finally:
            db.close()

    def list_installations(self, group_id: str) -> list[MatrixInstallationMembership]:
        db = SessionLocal()
        try:
            return db.query(MatrixInstallationMembership).filter(
                MatrixInstallationMembership.matrix_group_id == uuid.UUID(group_id)
            ).all()
        finally:
            db.close()

    def remove_installation(self, group_id: str, installation_uuid: str) -> bool:
        db = SessionLocal()
        try:
            membership = db.query(MatrixInstallationMembership).filter(
                MatrixInstallationMembership.matrix_group_id == uuid.UUID(group_id),
                MatrixInstallationMembership.installation_uuid == installation_uuid,
            ).first()
            if not membership:
                return False
            db.delete(membership)
            db.commit()
            logger.info("Removed installation %s from group %s", installation_uuid, group_id)
            return True
        except Exception as exc:
            db.rollback()
            logger.error("Failed to remove installation: %s", exc)
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Phase 3: User directory + SSO
    # ------------------------------------------------------------------

    def get_user_matrix_profile(self, user_email: str) -> dict:
        """Get a user's Matrix groups and capabilities across all groups."""
        db = SessionLocal()
        try:
            users = db.query(MatrixUser).filter(MatrixUser.user_email == user_email).all()
            groups = []
            all_capabilities = []
            for user in users:
                caps = db.query(MatrixUserCapability).filter(
                    MatrixUserCapability.matrix_user_id == user.id
                ).all()
                groups.append({
                    "group_id": str(user.matrix_group_id),
                    "home_installation_uuid": user.home_installation_uuid,
                    "capabilities": [c.capability for c in caps],
                })
                all_capabilities.extend([c.capability for c in caps])

            return {
                "groups": groups,
                "capabilities": list(set(all_capabilities)),
            }
        finally:
            db.close()

    def list_users(self, group_id: str) -> list[MatrixUser]:
        db = SessionLocal()
        try:
            return db.query(MatrixUser).filter(
                MatrixUser.matrix_group_id == uuid.UUID(group_id)
            ).all()
        finally:
            db.close()

    def add_user(self, group_id: str, user_email: str, home_installation_uuid: str,
                 home_node_url: str, display_name: str, capabilities: list[str],
                 granted_by_user_id: int) -> tuple:
        db = SessionLocal()
        try:
            user = MatrixUser(
                matrix_group_id=uuid.UUID(group_id),
                user_email=user_email,
                home_installation_uuid=home_installation_uuid,
                home_node_url=home_node_url,
                display_name=display_name,
            )
            db.add(user)
            db.flush()

            added_caps = []
            for cap in capabilities:
                if cap in MATRIX_CAPABILITIES:
                    db.add(MatrixUserCapability(
                        matrix_user_id=user.id,
                        capability=cap,
                        granted_by_user_id=granted_by_user_id,
                    ))
                    added_caps.append(cap)

            db.commit()
            logger.info("Added user %s to group %s with caps %s", user_email, group_id, added_caps)
            return user, added_caps
        except Exception as exc:
            db.rollback()
            logger.error("Failed to add user: %s", exc)
            raise
        finally:
            db.close()

    def remove_user(self, group_id: str, user_email: str) -> bool:
        db = SessionLocal()
        try:
            user = db.query(MatrixUser).filter(
                MatrixUser.matrix_group_id == uuid.UUID(group_id),
                MatrixUser.user_email == user_email,
            ).first()
            if not user:
                return False
            db.delete(user)
            db.commit()
            logger.info("Removed user %s from group %s", user_email, group_id)
            return True
        except Exception as exc:
            db.rollback()
            logger.error("Failed to remove user: %s", exc)
            raise
        finally:
            db.close()

    def get_user_capabilities(self, user_id: int) -> list[str]:
        db = SessionLocal()
        try:
            return [c.capability for c in db.query(MatrixUserCapability).filter(
                MatrixUserCapability.matrix_user_id == user_id
            ).all()]
        finally:
            db.close()

    def set_user_capabilities(self, group_id: str, user_email: str,
                               capabilities: list[str], granted_by_user_id: int) -> list[str]:
        db = SessionLocal()
        try:
            user = db.query(MatrixUser).filter(
                MatrixUser.matrix_group_id == uuid.UUID(group_id),
                MatrixUser.user_email == user_email,
            ).first()
            if not user:
                raise ValueError(f"User {user_email} not found in group {group_id}")

            db.query(MatrixUserCapability).filter(
                MatrixUserCapability.matrix_user_id == user.id
            ).delete()

            added_caps = []
            for cap in capabilities:
                if cap in MATRIX_CAPABILITIES:
                    db.add(MatrixUserCapability(
                        matrix_user_id=user.id,
                        capability=cap,
                        granted_by_user_id=granted_by_user_id,
                    ))
                    added_caps.append(cap)

            db.commit()
            logger.info("Updated capabilities for %s in group %s: %s", user_email, group_id, added_caps)
            return added_caps
        except Exception as exc:
            db.rollback()
            logger.error("Failed to set capabilities: %s", exc)
            raise
        finally:
            db.close()


# Module-level singleton — imported by API routers
matrix_service = MatrixService()
