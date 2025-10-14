# ppl-meta-cameras/src/services/profile_storage_service.py

"""
Profile Storage Service
Manages user profile templates with CRUD operations, search, and analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from models.profile_template import (
    TemplateUsageAnalytics,
    UserProfileTemplate,
    UserTemplateFavorite,
)
from models.recording_profile import CameraRecordingProfile
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


class TemplateSearchFilters:
    """Search filters for template queries."""

    def __init__(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by_user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_featured: Optional[bool] = None,
        min_usage_count: Optional[int] = None,
        min_favorite_count: Optional[int] = None,
        search_text: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ):
        self.category = category
        self.tags = tags or []
        self.created_by_user_id = created_by_user_id
        self.organization_id = organization_id
        self.is_public = is_public
        self.is_featured = is_featured
        self.min_usage_count = min_usage_count
        self.min_favorite_count = min_favorite_count
        self.search_text = search_text
        self.created_after = created_after
        self.created_before = created_before


class ProfileStorageService:
    """
    Service for managing user profile templates.

    Provides CRUD operations, search functionality, analytics tracking,
    and template sharing capabilities.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_template(
        self,
        name: str,
        user_id: str,
        configuration: Dict[str, Any],
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = False,
    ) -> UserProfileTemplate:
        """
        Create a new user profile template.

        Args:
            name: Template name
            user_id: User creating the template
            configuration: Recording configuration
            description: Optional description
            category: Template category
            tags: List of tags for search
            is_public: Whether template can be shared publicly

        Returns:
            Created UserProfileTemplate instance

        Raises:
            ValueError: If template name already exists for user
            IntegrityError: If database constraints are violated
        """
        try:
            # Check if template name already exists for user
            existing = (
                self.db.query(UserProfileTemplate)
                .filter(
                    and_(
                        UserProfileTemplate.name == name,
                        UserProfileTemplate.created_by_user_id == user_id,
                    )
                )
                .first()
            )

            if existing:
                raise ValueError(f"Template '{name}' already exists for user {user_id}")

            # Create template with configuration
            template = UserProfileTemplate(
                template_uuid=str(uuid4()),
                name=name,
                description=description,
                category=category,
                tags=tags,
                created_by_user_id=user_id,
                is_public=is_public,
                **configuration,
            )

            # Validate configuration
            validation_result = template.validate_configuration()
            if not validation_result["is_valid"]:
                raise ValueError(
                    f"Invalid configuration: {validation_result['errors']}"
                )

            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)

            # Track creation analytics
            self._track_template_action(template.id, user_id, "created")

            logger.info(f"Created template '{name}' for user {user_id}")
            return template

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database error creating template: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating template: {e}")
            raise

    def get_template(
        self, template_id: int, user_id: str
    ) -> Optional[UserProfileTemplate]:
        """
        Get a template by ID with user permission check.

        Args:
            template_id: Template ID
            user_id: User requesting the template

        Returns:
            UserProfileTemplate if found and accessible, None otherwise
        """
        template = (
            self.db.query(UserProfileTemplate)
            .filter(UserProfileTemplate.id == template_id)
            .first()
        )

        if not template:
            return None

        # Check permissions
        if not self._can_access_template(template, user_id):
            return None

        return template

    def get_template_by_uuid(
        self, template_uuid: str, user_id: str
    ) -> Optional[UserProfileTemplate]:
        """Get a template by UUID with user permission check."""
        template = (
            self.db.query(UserProfileTemplate)
            .filter(UserProfileTemplate.template_uuid == template_uuid)
            .first()
        )

        if not template:
            return None

        if not self._can_access_template(template, user_id):
            return None

        return template

    def update_template(
        self, template_id: int, user_id: str, updates: Dict[str, Any]
    ) -> Optional[UserProfileTemplate]:
        """
        Update a template with user permission check.

        Args:
            template_id: Template ID
            user_id: User updating the template
            updates: Dictionary of updates to apply

        Returns:
            Updated UserProfileTemplate if successful, None otherwise
        """
        template = self.get_template(template_id, user_id)
        if not template:
            return None

        # Only owner can update
        if template.created_by_user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to update template {template_id} without permission"
            )
            return None

        try:
            # Apply updates
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)

            # Validate updated configuration
            validation_result = template.validate_configuration()
            if not validation_result["is_valid"]:
                raise ValueError(
                    f"Invalid configuration: {validation_result['errors']}"
                )

            self.db.commit()
            self.db.refresh(template)

            # Track update analytics
            self._track_template_action(
                template.id,
                user_id,
                "updated",
                {"updated_fields": list(updates.keys())},
            )

            logger.info(f"Updated template {template_id} by user {user_id}")
            return template

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating template {template_id}: {e}")
            raise

    def delete_template(self, template_id: int, user_id: str) -> bool:
        """
        Delete a template with user permission check.

        Args:
            template_id: Template ID
            user_id: User deleting the template

        Returns:
            True if deleted successfully, False otherwise
        """
        template = self.get_template(template_id, user_id)
        if not template:
            return False

        # Only owner can delete
        if template.created_by_user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to delete template {template_id} without permission"
            )
            return False

        try:
            # Track deletion analytics
            self._track_template_action(template.id, user_id, "deleted")

            self.db.delete(template)
            self.db.commit()

            logger.info(f"Deleted template {template_id} by user {user_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting template {template_id}: {e}")
            return False

    def search_templates(
        self,
        filters: TemplateSearchFilters,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[UserProfileTemplate], int]:
        """
        Search templates with filters and pagination.

        Args:
            filters: Search filters
            user_id: User performing the search
            page: Page number (1-based)
            page_size: Number of results per page
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")

        Returns:
            Tuple of (templates, total_count)
        """
        query = self.db.query(UserProfileTemplate)

        # Apply user access filters
        access_filter = or_(
            UserProfileTemplate.created_by_user_id == user_id,
            UserProfileTemplate.is_public == True,
        )
        query = query.filter(access_filter)

        # Apply search filters
        if filters.category:
            query = query.filter(UserProfileTemplate.category == filters.category)

        if filters.tags:
            for tag in filters.tags:
                query = query.filter(UserProfileTemplate.tags.contains([tag]))

        if filters.created_by_user_id:
            query = query.filter(
                UserProfileTemplate.created_by_user_id == filters.created_by_user_id
            )

        if filters.organization_id:
            query = query.filter(
                UserProfileTemplate.organization_id == filters.organization_id
            )

        if filters.is_public is not None:
            query = query.filter(UserProfileTemplate.is_public == filters.is_public)

        if filters.is_featured is not None:
            query = query.filter(UserProfileTemplate.is_featured == filters.is_featured)

        if filters.min_usage_count is not None:
            query = query.filter(
                UserProfileTemplate.usage_count >= filters.min_usage_count
            )

        if filters.min_favorite_count is not None:
            query = query.filter(
                UserProfileTemplate.favorite_count >= filters.min_favorite_count
            )

        if filters.search_text:
            search_filter = or_(
                UserProfileTemplate.name.ilike(f"%{filters.search_text}%"),
                UserProfileTemplate.description.ilike(f"%{filters.search_text}%"),
            )
            query = query.filter(search_filter)

        if filters.created_after:
            query = query.filter(
                UserProfileTemplate.created_at >= filters.created_after
            )

        if filters.created_before:
            query = query.filter(
                UserProfileTemplate.created_at <= filters.created_before
            )

        # Get total count
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(
            UserProfileTemplate, sort_by, UserProfileTemplate.created_at
        )
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        templates = query.all()

        logger.info(
            f"Search returned {len(templates)} templates (total: {total_count}) for user {user_id}"
        )
        return templates, total_count

    def clone_template(
        self,
        template_id: int,
        user_id: str,
        new_name: str,
        description: Optional[str] = None,
    ) -> Optional[UserProfileTemplate]:
        """
        Clone an existing template for a user.

        Args:
            template_id: Template ID to clone
            user_id: User creating the clone
            new_name: Name for the cloned template
            description: Optional description for the clone

        Returns:
            Cloned UserProfileTemplate if successful, None otherwise
        """
        template = self.get_template(template_id, user_id)
        if not template:
            return None

        try:
            cloned_template = template.clone_template(new_name, user_id)
            if description:
                cloned_template.description = description

            self.db.add(cloned_template)
            self.db.commit()
            self.db.refresh(cloned_template)

            # Track cloning analytics
            self._track_template_action(template.id, user_id, "cloned")
            self._track_template_action(cloned_template.id, user_id, "created")

            logger.info(
                f"Cloned template {template_id} as '{new_name}' for user {user_id}"
            )
            return cloned_template

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cloning template {template_id}: {e}")
            return None

    def add_favorite(self, template_id: int, user_id: str) -> bool:
        """Add a template to user favorites."""
        template = self.get_template(template_id, user_id)
        if not template:
            return False

        try:
            favorite = UserTemplateFavorite(user_id=user_id, template_id=template_id)
            self.db.add(favorite)
            self.db.commit()

            # Track favorite analytics
            self._track_template_action(template_id, user_id, "favorited")

            logger.info(f"User {user_id} favorited template {template_id}")
            return True

        except IntegrityError:
            # Already favorited
            self.db.rollback()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding favorite: {e}")
            return False

    def remove_favorite(self, template_id: int, user_id: str) -> bool:
        """Remove a template from user favorites."""
        try:
            favorite = (
                self.db.query(UserTemplateFavorite)
                .filter(
                    and_(
                        UserTemplateFavorite.user_id == user_id,
                        UserTemplateFavorite.template_id == template_id,
                    )
                )
                .first()
            )

            if favorite:
                self.db.delete(favorite)
                self.db.commit()

                # Track unfavorite analytics
                self._track_template_action(template_id, user_id, "unfavorited")

                logger.info(f"User {user_id} unfavorited template {template_id}")

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing favorite: {e}")
            return False

    def get_user_favorites(self, user_id: str) -> List[UserProfileTemplate]:
        """Get all templates favorited by a user."""
        favorites = (
            self.db.query(UserTemplateFavorite)
            .options(joinedload(UserTemplateFavorite.template))
            .filter(UserTemplateFavorite.user_id == user_id)
            .all()
        )

        return [favorite.template for favorite in favorites if favorite.template]

    def apply_template_to_profile(
        self,
        template_id: int,
        user_id: str,
        profile_name: str,
        camera_id: Optional[str] = None,
    ) -> Optional[CameraRecordingProfile]:
        """
        Apply a template to create a new recording profile.

        Args:
            template_id: Template ID to apply
            user_id: User applying the template
            profile_name: Name for the new profile
            camera_id: Optional camera ID context

        Returns:
            Created CameraRecordingProfile if successful, None otherwise
        """
        template = self.get_template(template_id, user_id)
        if not template:
            return None

        try:
            # Create recording profile from template
            config = template.get_configuration()
            profile = CameraRecordingProfile(
                name=profile_name,
                description=f"Profile created from template: {template.name}",
                created_by_user_id=user_id,
                **config,
            )

            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

            # Update template usage
            template.increment_usage()
            self.db.commit()

            # Track application analytics
            context_data = {"profile_id": profile.id}
            if camera_id:
                context_data["camera_id"] = camera_id
            self._track_template_action(template_id, user_id, "applied", context_data)

            logger.info(
                f"Applied template {template_id} to create profile '{profile_name}' for user {user_id}"
            )
            return profile

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error applying template {template_id}: {e}")
            return None

    def get_template_analytics(self, template_id: int, user_id: str) -> Dict[str, Any]:
        """Get analytics for a template."""
        template = self.get_template(template_id, user_id)
        if not template:
            return {}

        # Get usage analytics for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        analytics = (
            self.db.query(TemplateUsageAnalytics)
            .filter(
                and_(
                    TemplateUsageAnalytics.template_id == template_id,
                    TemplateUsageAnalytics.timestamp >= thirty_days_ago,
                )
            )
            .all()
        )

        # Aggregate analytics data
        action_counts = {}
        recent_users = set()
        daily_usage = {}

        for record in analytics:
            action_counts[record.action] = action_counts.get(record.action, 0) + 1
            recent_users.add(record.user_id)
            day_key = record.timestamp.date().isoformat()
            daily_usage[day_key] = daily_usage.get(day_key, 0) + 1

        return {
            "template_id": template_id,
            "total_usage_count": template.usage_count,
            "favorite_count": template.favorite_count,
            "last_used_at": (
                template.last_used_at.isoformat() if template.last_used_at else None
            ),
            "recent_30_days": {
                "action_counts": action_counts,
                "unique_users": len(recent_users),
                "daily_usage": daily_usage,
            },
        }

    def get_popular_templates(
        self, user_id: str, limit: int = 10
    ) -> List[UserProfileTemplate]:
        """Get most popular templates based on usage and favorites."""
        query = self.db.query(UserProfileTemplate)

        # Apply user access filters
        access_filter = or_(
            UserProfileTemplate.created_by_user_id == user_id,
            UserProfileTemplate.is_public == True,
        )
        query = query.filter(access_filter)

        # Order by popularity (usage count + favorite count)
        query = query.order_by(
            desc(UserProfileTemplate.usage_count + UserProfileTemplate.favorite_count)
        ).limit(limit)

        return query.all()

    def _can_access_template(self, template: UserProfileTemplate, user_id: str) -> bool:
        """Check if user can access a template."""
        return template.created_by_user_id == user_id or template.is_public

    def _track_template_action(
        self,
        template_id: int,
        user_id: str,
        action: str,
        context_data: Optional[Dict[str, Any]] = None,
    ):
        """Track template usage analytics."""
        try:
            analytics_record = TemplateUsageAnalytics(
                template_id=template_id,
                user_id=user_id,
                action=action,
                context_data=context_data,
            )
            self.db.add(analytics_record)
            # Note: Commit is handled by the calling method
        except Exception as e:
            logger.error(f"Error tracking template action: {e}")
