# ppl-meta-cameras/src/services/recording_profile_service.py

"""
Recording Profile Service
Handles CRUD operations and business logic for camera recording profiles
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.recording_profile import CameraRecordingProfile

logger = logging.getLogger(__name__)


class RecordingProfileService:
    """Service for managing camera recording profiles."""

    def __init__(self, db: Session):
        self.db = db

    async def create_profile(
        self,
        name: str,
        created_by_user_id: str,
        description: Optional[str] = None,
        **config_params,
    ) -> CameraRecordingProfile:
        """
        Create a new recording profile.

        Args:
            name: Profile name
            created_by_user_id: ID of the user creating the profile
            description: Optional profile description
            **config_params: Recording configuration parameters

        Returns:
            Created recording profile

        Raises:
            ValueError: If validation fails
        """
        # Create new profile instance
        profile = CameraRecordingProfile(
            profile_uuid=str(uuid4()),
            name=name,
            description=description,
            created_by_user_id=created_by_user_id,
            is_system_default=False,  # User profiles are never system defaults
            **config_params,
        )

        # Validate configuration
        validation_errors = profile.validate_configuration()
        if validation_errors:
            error_msg = "; ".join(
                [f"{key}: {msg}" for key, msg in validation_errors.items()]
            )
            raise ValueError(f"Profile validation failed: {error_msg}")

        # Save to database
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Created recording profile: {profile.name} (ID: {profile.id})")
        return profile

    async def get_profile_by_id(
        self, profile_id: int
    ) -> Optional[CameraRecordingProfile]:
        """Get a recording profile by ID."""
        return (
            self.db.query(CameraRecordingProfile)
            .filter(
                CameraRecordingProfile.id == profile_id,
                CameraRecordingProfile.is_active == True,
            )
            .first()
        )

    async def get_profile_by_uuid(
        self, profile_uuid: str
    ) -> Optional[CameraRecordingProfile]:
        """Get a recording profile by UUID."""
        return (
            self.db.query(CameraRecordingProfile)
            .filter(
                CameraRecordingProfile.profile_uuid == profile_uuid,
                CameraRecordingProfile.is_active == True,
            )
            .first()
        )

    async def get_user_profiles(
        self,
        user_id: str,
        include_system_defaults: bool = True,
        organization_id: Optional[str] = None,
    ) -> List[CameraRecordingProfile]:
        """
        Get all profiles accessible to a user.

        Args:
            user_id: User ID
            include_system_defaults: Whether to include system default profiles
            organization_id: Optional organization filter

        Returns:
            List of accessible recording profiles
        """
        query = self.db.query(CameraRecordingProfile).filter(
            CameraRecordingProfile.is_active == True
        )

        # Build filter conditions
        conditions = []

        # User's own profiles
        conditions.append(CameraRecordingProfile.created_by_user_id == user_id)

        # System default profiles
        if include_system_defaults:
            conditions.append(CameraRecordingProfile.is_system_default == True)

        # Organization profiles (if applicable)
        if organization_id:
            conditions.append(
                and_(
                    CameraRecordingProfile.organization_id == organization_id,
                    CameraRecordingProfile.created_by_user_id
                    != user_id,  # Exclude own profiles to avoid duplicates
                )
            )

        # Apply OR filter
        query = query.filter(or_(*conditions))

        # Order by system defaults first, then by usage, then by name
        return query.order_by(
            CameraRecordingProfile.is_system_default.desc(),
            CameraRecordingProfile.usage_count.desc(),
            CameraRecordingProfile.name,
        ).all()

    async def get_system_default_profiles(self) -> List[CameraRecordingProfile]:
        """Get all system default profiles."""
        return (
            self.db.query(CameraRecordingProfile)
            .filter(
                CameraRecordingProfile.is_system_default == True,
                CameraRecordingProfile.is_active == True,
            )
            .order_by(CameraRecordingProfile.name)
            .all()
        )

    async def update_profile(
        self, profile_id: int, user_id: str, updates: Dict[str, Any]
    ) -> Optional[CameraRecordingProfile]:
        """
        Update a recording profile.

        Args:
            profile_id: Profile ID to update
            user_id: User making the update
            updates: Dictionary of fields to update

        Returns:
            Updated profile or None if not found/unauthorized
        """
        # Get profile and check permissions
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return None

        # Check if user can modify this profile
        if not self._can_user_modify_profile(profile, user_id):
            logger.warning(
                f"User {user_id} attempted to modify profile {profile_id} without permission"
            )
            return None

        # Prevent modification of certain fields
        protected_fields = [
            "id",
            "profile_uuid",
            "is_system_default",
            "created_by_user_id",
            "created_at",
        ]
        updates = {k: v for k, v in updates.items() if k not in protected_fields}

        # Apply updates
        for field, value in updates.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        # Validate updated configuration
        validation_errors = profile.validate_configuration()
        if validation_errors:
            error_msg = "; ".join(
                [f"{key}: {msg}" for key, msg in validation_errors.items()]
            )
            raise ValueError(f"Profile validation failed: {error_msg}")

        # Save changes
        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Updated recording profile: {profile.name} (ID: {profile.id})")
        return profile

    async def delete_profile(self, profile_id: int, user_id: str) -> bool:
        """
        Soft delete a recording profile.

        Args:
            profile_id: Profile ID to delete
            user_id: User requesting deletion

        Returns:
            True if deleted successfully, False otherwise
        """
        # Get profile and check permissions
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return False

        # Check if user can delete this profile
        if not self._can_user_modify_profile(profile, user_id):
            logger.warning(
                f"User {user_id} attempted to delete profile {profile_id} without permission"
            )
            return False

        # System default profiles cannot be deleted
        if profile.is_system_default:
            logger.warning(f"Attempted to delete system default profile {profile_id}")
            return False

        # Check if profile is in use by cameras
        cameras_using_profile = self.db.execute(
            "SELECT COUNT(*) FROM cameras WHERE recording_profile_id = :profile_id",
            {"profile_id": profile_id},
        ).scalar()

        if cameras_using_profile > 0:
            logger.warning(
                f"Cannot delete profile {profile_id}: still in use by {cameras_using_profile} cameras"
            )
            return False

        # Soft delete
        profile.is_active = False
        self.db.commit()

        logger.info(f"Deleted recording profile: {profile.name} (ID: {profile.id})")
        return True

    async def clone_profile(
        self,
        source_profile_id: int,
        new_name: str,
        user_id: str,
        description: Optional[str] = None,
    ) -> Optional[CameraRecordingProfile]:
        """
        Clone an existing recording profile.

        Args:
            source_profile_id: ID of profile to clone
            new_name: Name for the cloned profile
            user_id: User creating the clone
            description: Optional description for cloned profile

        Returns:
            Cloned profile or None if source not found
        """
        # Get source profile
        source_profile = await self.get_profile_by_id(source_profile_id)
        if not source_profile:
            return None

        # Create clone
        cloned_profile = source_profile.clone(new_name, user_id)
        if description:
            cloned_profile.description = description

        # Save clone
        self.db.add(cloned_profile)
        self.db.commit()
        self.db.refresh(cloned_profile)

        logger.info(
            f"Cloned profile {source_profile.name} -> {cloned_profile.name} (ID: {cloned_profile.id})"
        )
        return cloned_profile

    async def assign_profile_to_camera(
        self, camera_id: int, profile_id: int, user_id: str
    ) -> bool:
        """
        Assign a recording profile to a camera.

        Args:
            camera_id: Camera ID
            profile_id: Profile ID to assign
            user_id: User making the assignment

        Returns:
            True if assigned successfully, False otherwise
        """
        # Verify profile exists and user has access
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return False

        # Check if user has access to this profile
        user_profiles = await self.get_user_profiles(user_id)
        if profile not in user_profiles:
            logger.warning(
                f"User {user_id} attempted to assign inaccessible profile {profile_id}"
            )
            return False

        # Update camera with profile assignment
        result = self.db.execute(
            "UPDATE cameras SET recording_profile_id = :profile_id WHERE id = :camera_id",
            {"profile_id": profile_id, "camera_id": camera_id},
        )

        if result.rowcount == 0:
            logger.warning(f"Camera {camera_id} not found for profile assignment")
            return False

        # Update profile usage statistics
        profile.update_usage_stats()
        self.db.commit()

        logger.info(f"Assigned profile {profile.name} to camera {camera_id}")
        return True

    async def remove_profile_from_camera(self, camera_id: int) -> bool:
        """
        Remove recording profile assignment from a camera.

        Args:
            camera_id: Camera ID

        Returns:
            True if removed successfully, False otherwise
        """
        result = self.db.execute(
            "UPDATE cameras SET recording_profile_id = NULL WHERE id = :camera_id",
            {"camera_id": camera_id},
        )

        success = result.rowcount > 0
        if success:
            self.db.commit()
            logger.info(f"Removed profile assignment from camera {camera_id}")

        return success

    async def get_cameras_using_profile(self, profile_id: int) -> List[Dict[str, Any]]:
        """
        Get list of cameras using a specific recording profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of camera information
        """
        cameras = self.db.execute(
            """
            SELECT id, device_id, name, location, status 
            FROM cameras 
            WHERE recording_profile_id = :profile_id
            """,
            {"profile_id": profile_id},
        ).fetchall()

        return [
            {
                "id": camera.id,
                "device_id": camera.device_id,
                "name": camera.name,
                "location": camera.location,
                "status": camera.status,
            }
            for camera in cameras
        ]

    async def get_profile_usage_statistics(self, profile_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for a recording profile.

        Args:
            profile_id: Profile ID

        Returns:
            Usage statistics dictionary
        """
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return {}

        cameras_using = await self.get_cameras_using_profile(profile_id)

        return {
            "profile_id": profile_id,
            "profile_name": profile.name,
            "usage_count": profile.usage_count,
            "last_used_at": (
                profile.last_used_at.isoformat() if profile.last_used_at else None
            ),
            "cameras_assigned": len(cameras_using),
            "cameras_list": cameras_using,
            "created_at": profile.created_at.isoformat(),
            "is_system_default": profile.is_system_default,
        }

    def _can_user_modify_profile(
        self, profile: CameraRecordingProfile, user_id: str
    ) -> bool:
        """
        Check if a user can modify a recording profile.

        Args:
            profile: Profile to check
            user_id: User ID

        Returns:
            True if user can modify, False otherwise
        """
        # System default profiles cannot be modified by users
        if profile.is_system_default:
            return False

        # Users can only modify their own profiles
        return profile.created_by_user_id == user_id

    async def search_profiles(
        self, user_id: str, query: str, include_system_defaults: bool = True
    ) -> List[CameraRecordingProfile]:
        """
        Search recording profiles by name or description.

        Args:
            user_id: User ID for access control
            query: Search query string
            include_system_defaults: Whether to include system defaults

        Returns:
            List of matching profiles
        """
        # Get user's accessible profiles
        profiles = await self.get_user_profiles(user_id, include_system_defaults)

        # Filter by search query
        query_lower = query.lower()
        matching_profiles = [
            profile
            for profile in profiles
            if (
                query_lower in profile.name.lower()
                or (profile.description and query_lower in profile.description.lower())
            )
        ]

        return matching_profiles
