# ppl-meta-cameras/src/services/template_import_export_service.py

"""
Template Import/Export Service
Handles template import/export functionality for sharing configurations
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models.profile_template import UserProfileTemplate
from services.profile_storage_service import ProfileStorageService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TemplateExportFormat:
    """Template export format specification."""

    CURRENT_VERSION = "1.0"
    SUPPORTED_VERSIONS = ["1.0"]

    @classmethod
    def create_export_data(
        cls,
        templates: List[UserProfileTemplate],
        include_metadata: bool = True,
        include_analytics: bool = False,
    ) -> Dict[str, Any]:
        """Create export data structure for templates."""
        export_data = {
            "format_version": cls.CURRENT_VERSION,
            "export_timestamp": datetime.utcnow().isoformat(),
            "template_count": len(templates),
            "templates": [],
        }

        for template in templates:
            template_data = {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags or [],
                "configuration": template.get_configuration(),
                "version": template.version,
            }

            if include_metadata:
                template_data["metadata"] = {
                    "is_public": template.is_public,
                    "is_featured": template.is_featured,
                    "original_template_uuid": template.template_uuid,
                    "created_at": (
                        template.created_at.isoformat() if template.created_at else None
                    ),
                }

            if include_analytics:
                template_data["analytics"] = template.get_usage_stats()

            export_data["templates"].append(template_data)

        return export_data


class TemplateImportResult:
    """Result of template import operation."""

    def __init__(self):
        self.successful_imports: List[UserProfileTemplate] = []
        self.failed_imports: List[Dict[str, Any]] = []
        self.skipped_imports: List[Dict[str, Any]] = []
        self.total_processed = 0

    @property
    def success_count(self) -> int:
        return len(self.successful_imports)

    @property
    def failure_count(self) -> int:
        return len(self.failed_imports)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_imports)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "total_processed": self.total_processed,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "skipped_count": self.skipped_count,
            "successful_imports": [
                {
                    "template_id": template.id,
                    "template_uuid": template.template_uuid,
                    "name": template.name,
                }
                for template in self.successful_imports
            ],
            "failed_imports": self.failed_imports,
            "skipped_imports": self.skipped_imports,
        }


class TemplateImportExportService:
    """
    Service for importing and exporting user profile templates.

    Provides functionality to export templates to JSON format and import
    templates from various sources with validation and conflict resolution.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.storage_service = ProfileStorageService(db_session)

    def export_templates(
        self,
        template_ids: List[int],
        user_id: str,
        include_metadata: bool = True,
        include_analytics: bool = False,
    ) -> Dict[str, Any]:
        """
        Export templates to JSON format.

        Args:
            template_ids: List of template IDs to export
            user_id: User performing the export
            include_metadata: Include template metadata in export
            include_analytics: Include usage analytics in export

        Returns:
            Export data dictionary

        Raises:
            ValueError: If no templates found or access denied
        """
        templates = []

        for template_id in template_ids:
            template = self.storage_service.get_template(template_id, user_id)
            if template:
                templates.append(template)
            else:
                logger.warning(
                    "Template %d not found or access denied for user %s",
                    template_id,
                    user_id,
                )

        if not templates:
            raise ValueError("No accessible templates found for export")

        export_data = TemplateExportFormat.create_export_data(
            templates=templates,
            include_metadata=include_metadata,
            include_analytics=include_analytics,
        )

        logger.info("Exported %d templates for user %s", len(templates), user_id)
        return export_data

    def export_user_templates(
        self,
        user_id: str,
        category: Optional[str] = None,
        include_metadata: bool = True,
        include_analytics: bool = False,
    ) -> Dict[str, Any]:
        """
        Export all templates for a user.

        Args:
            user_id: User whose templates to export
            category: Optional category filter
            include_metadata: Include template metadata in export
            include_analytics: Include usage analytics in export

        Returns:
            Export data dictionary
        """
        from services.profile_storage_service import TemplateSearchFilters

        filters = TemplateSearchFilters(created_by_user_id=user_id, category=category)

        templates, _ = self.storage_service.search_templates(
            filters=filters,
            user_id=user_id,
            page=1,
            page_size=1000,  # Large limit to get all templates
        )

        export_data = TemplateExportFormat.create_export_data(
            templates=templates,
            include_metadata=include_metadata,
            include_analytics=include_analytics,
        )

        logger.info("Exported %d user templates for user %s", len(templates), user_id)
        return export_data

    def import_templates(
        self,
        import_data: Dict[str, Any],
        user_id: str,
        conflict_resolution: str = "skip",  # "skip", "rename", "overwrite"
        category_override: Optional[str] = None,
        make_private: bool = True,
    ) -> TemplateImportResult:
        """
        Import templates from JSON data.

        Args:
            import_data: Import data dictionary
            user_id: User performing the import
            conflict_resolution: How to handle name conflicts ("skip", "rename", "overwrite")
            category_override: Override category for all imported templates
            make_private: Make all imported templates private

        Returns:
            TemplateImportResult with import statistics and results
        """
        result = TemplateImportResult()

        try:
            # Validate import data format
            self._validate_import_data(import_data)

            templates_data = import_data.get("templates", [])
            result.total_processed = len(templates_data)

            for template_data in templates_data:
                try:
                    imported_template = self._import_single_template(
                        template_data=template_data,
                        user_id=user_id,
                        conflict_resolution=conflict_resolution,
                        category_override=category_override,
                        make_private=make_private,
                    )

                    if imported_template:
                        result.successful_imports.append(imported_template)
                    else:
                        result.skipped_imports.append(
                            {
                                "name": template_data.get("name", "Unknown"),
                                "reason": "Name conflict - skipped",
                            }
                        )

                except Exception as e:
                    logger.error(
                        "Failed to import template '%s': %s",
                        template_data.get("name", "Unknown"),
                        e,
                    )
                    result.failed_imports.append(
                        {"name": template_data.get("name", "Unknown"), "error": str(e)}
                    )

            logger.info(
                "Import completed for user %s: %d success, %d failed, %d skipped",
                user_id,
                result.success_count,
                result.failure_count,
                result.skipped_count,
            )

            return result

        except Exception as e:
            logger.error("Import failed for user %s: %s", user_id, e)
            raise

    def import_from_json_string(
        self,
        json_string: str,
        user_id: str,
        conflict_resolution: str = "skip",
        category_override: Optional[str] = None,
        make_private: bool = True,
    ) -> TemplateImportResult:
        """Import templates from JSON string."""
        try:
            import_data = json.loads(json_string)
            return self.import_templates(
                import_data=import_data,
                user_id=user_id,
                conflict_resolution=conflict_resolution,
                category_override=category_override,
                make_private=make_private,
            )
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON format: %s", e)
            raise ValueError(f"Invalid JSON format: {e}")

    def export_to_json_string(
        self,
        template_ids: List[int],
        user_id: str,
        include_metadata: bool = True,
        include_analytics: bool = False,
        pretty_print: bool = True,
    ) -> str:
        """Export templates to JSON string."""
        export_data = self.export_templates(
            template_ids=template_ids,
            user_id=user_id,
            include_metadata=include_metadata,
            include_analytics=include_analytics,
        )

        if pretty_print:
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(export_data, ensure_ascii=False)

    def get_import_preview(
        self, import_data: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """
        Preview import operation without actually importing.

        Args:
            import_data: Import data dictionary
            user_id: User performing the import

        Returns:
            Preview information about the import
        """
        try:
            self._validate_import_data(import_data)

            templates_data = import_data.get("templates", [])
            preview = {
                "total_templates": len(templates_data),
                "conflicts": [],
                "valid_templates": [],
                "invalid_templates": [],
            }

            for template_data in templates_data:
                name = template_data.get("name", "Unknown")

                # Check for name conflicts
                existing = (
                    self.db.query(UserProfileTemplate)
                    .filter(
                        UserProfileTemplate.name == name,
                        UserProfileTemplate.created_by_user_id == user_id,
                    )
                    .first()
                )

                if existing:
                    preview["conflicts"].append(
                        {"name": name, "existing_template_id": existing.id}
                    )

                # Validate template configuration
                try:
                    self._validate_template_data(template_data)
                    preview["valid_templates"].append(name)
                except Exception as e:
                    preview["invalid_templates"].append({"name": name, "error": str(e)})

            return preview

        except Exception as e:
            logger.error("Preview failed: %s", e)
            raise

    def _validate_import_data(self, import_data: Dict[str, Any]):
        """Validate import data format."""
        if not isinstance(import_data, dict):
            raise ValueError("Import data must be a dictionary")

        format_version = import_data.get("format_version")
        if format_version not in TemplateExportFormat.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported format version: {format_version}")

        if "templates" not in import_data:
            raise ValueError("Import data must contain 'templates' field")

        if not isinstance(import_data["templates"], list):
            raise ValueError("Templates field must be a list")

    def _validate_template_data(self, template_data: Dict[str, Any]):
        """Validate individual template data."""
        required_fields = ["name", "configuration"]

        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate configuration structure
        config = template_data["configuration"]
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Basic validation of configuration fields
        if "quality" in config and config["quality"] not in [
            "low",
            "medium",
            "high",
            "ultra",
        ]:
            raise ValueError("Invalid quality setting")

    def _import_single_template(
        self,
        template_data: Dict[str, Any],
        user_id: str,
        conflict_resolution: str,
        category_override: Optional[str],
        make_private: bool,
    ) -> Optional[UserProfileTemplate]:
        """Import a single template."""
        name = template_data["name"]

        # Check for name conflicts
        existing = (
            self.db.query(UserProfileTemplate)
            .filter(
                UserProfileTemplate.name == name,
                UserProfileTemplate.created_by_user_id == user_id,
            )
            .first()
        )

        if existing:
            if conflict_resolution == "skip":
                return None
            elif conflict_resolution == "rename":
                name = self._generate_unique_name(name, user_id)
            elif conflict_resolution == "overwrite":
                self.storage_service.delete_template(existing.id, user_id)

        # Prepare template configuration
        configuration = template_data["configuration"].copy()

        # Apply overrides
        category = category_override or template_data.get("category")
        is_public = (
            False
            if make_private
            else template_data.get("metadata", {}).get("is_public", False)
        )

        # Create template
        template = self.storage_service.create_template(
            name=name,
            user_id=user_id,
            configuration=configuration,
            description=template_data.get("description"),
            category=category,
            tags=template_data.get("tags", []),
            is_public=is_public,
        )

        return template

    def _generate_unique_name(self, base_name: str, user_id: str) -> str:
        """Generate a unique template name for the user."""
        counter = 1
        while True:
            candidate_name = f"{base_name} ({counter})"
            existing = (
                self.db.query(UserProfileTemplate)
                .filter(
                    UserProfileTemplate.name == candidate_name,
                    UserProfileTemplate.created_by_user_id == user_id,
                )
                .first()
            )

            if not existing:
                return candidate_name

            counter += 1

            # Safety limit
            if counter > 1000:
                raise ValueError("Unable to generate unique name")
