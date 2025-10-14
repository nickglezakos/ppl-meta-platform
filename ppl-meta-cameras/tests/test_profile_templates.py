# ppl-meta-cameras/tests/test_profile_templates.py

"""
Comprehensive tests for Profile Template functionality
Tests models, services, and API endpoints for Phase 3 implementation
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from models.profile_template import (
    TemplateUsageAnalytics,
    UserProfileTemplate,
    UserTemplateFavorite,
)
from services.profile_storage_service import (
    ProfileStorageService,
    TemplateSearchFilters,
)
from services.template_import_export_service import (
    TemplateExportFormat,
    TemplateImportExportService,
    TemplateImportResult,
)


class TestUserProfileTemplate:
    """Test UserProfileTemplate model functionality."""

    def test_template_creation(self):
        """Test creating a new template."""
        template = UserProfileTemplate(
            name="Test Template",
            description="Test description",
            category="test",
            quality="high",
            format="mp4",
            created_by_user_id="user123",
        )

        assert template.name == "Test Template"
        assert template.quality == "high"
        assert template.format == "mp4"
        assert template.created_by_user_id == "user123"

    def test_template_to_dict(self):
        """Test template dictionary conversion."""
        template = UserProfileTemplate(
            name="Test Template",
            description="Test description",
            category="test",
            tags=["tag1", "tag2"],
            quality="high",
            created_by_user_id="user123",
        )

        result = template.to_dict()

        assert result["name"] == "Test Template"
        assert result["description"] == "Test description"
        assert result["category"] == "test"
        assert result["tags"] == ["tag1", "tag2"]
        assert "configuration" in result
        assert "metadata" in result
        assert "usage_stats" in result

    def test_template_configuration(self):
        """Test template configuration extraction."""
        template = UserProfileTemplate(
            name="Test Template",
            quality="ultra",
            format="mp4",
            resolution="3840x2160",
            frame_rate=60,
            enable_face_detection=True,
            created_by_user_id="user123",
        )

        config = template.get_configuration()

        assert config["quality"] == "ultra"
        assert config["format"] == "mp4"
        assert config["resolution"] == "3840x2160"
        assert config["frame_rate"] == 60
        assert config["enable_face_detection"] is True

    def test_template_validation(self):
        """Test template configuration validation."""
        # Valid template
        template = UserProfileTemplate(
            name="Valid Template",
            quality="high",
            format="mp4",
            default_duration_seconds=60,
            max_duration_seconds=3600,
            bitrate_kbps=5000,
            audio_bitrate_kbps=128,
            created_by_user_id="user123",
        )

        validation = template.validate_configuration()
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0

        # Invalid template - bad quality
        template.quality = "invalid"
        validation = template.validate_configuration()
        assert validation["is_valid"] is False
        assert any("quality" in error.lower() for error in validation["errors"])

    def test_template_clone(self):
        """Test template cloning functionality."""
        original = UserProfileTemplate(
            name="Original Template",
            description="Original description",
            category="original",
            tags=["tag1", "tag2"],
            quality="high",
            format="mp4",
            enable_face_detection=True,
            created_by_user_id="user123",
        )

        cloned = original.clone_template("Cloned Template", "user456")

        assert cloned.name == "Cloned Template"
        assert cloned.description == "Copy of Original Template"
        assert cloned.category == "original"
        assert cloned.tags == ["tag1", "tag2"]
        assert cloned.quality == "high"
        assert cloned.format == "mp4"
        assert cloned.enable_face_detection is True
        assert cloned.created_by_user_id == "user456"
        assert cloned.parent_template_id == original.id
        assert cloned.is_template_copy is True
        assert cloned.shared_by_user_id == "user123"

    def test_template_usage_tracking(self):
        """Test template usage increment."""
        template = UserProfileTemplate(
            name="Test Template", usage_count=5, created_by_user_id="user123"
        )

        initial_count = template.usage_count
        initial_time = template.last_used_at

        template.increment_usage()

        assert template.usage_count == initial_count + 1
        assert template.last_used_at is not None
        assert template.last_used_at != initial_time


class TestProfileStorageService:
    """Test ProfileStorageService functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.service = ProfileStorageService(self.mock_db)

    def test_create_template_success(self):
        """Test successful template creation."""
        # Mock database query to return no existing template
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock template creation
        mock_template = Mock()
        mock_template.validate_configuration.return_value = {
            "is_valid": True,
            "errors": [],
        }

        with patch("models.profile_template.UserProfileTemplate") as MockTemplate:
            MockTemplate.return_value = mock_template

            result = self.service.create_template(
                name="Test Template",
                user_id="user123",
                configuration={"quality": "high", "format": "mp4"},
                description="Test description",
            )

            assert result == mock_template
            self.mock_db.add.assert_called_once_with(mock_template)
            self.mock_db.commit.assert_called()

    def test_create_template_duplicate_name(self):
        """Test template creation with duplicate name."""
        # Mock database query to return existing template
        existing_template = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            existing_template
        )

        with pytest.raises(ValueError, match="already exists"):
            self.service.create_template(
                name="Duplicate Template",
                user_id="user123",
                configuration={"quality": "high"},
            )

    def test_search_templates_with_filters(self):
        """Test template search with various filters."""
        # Mock query chain
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        filters = TemplateSearchFilters(
            category="test", tags=["tag1"], is_public=True, search_text="test"
        )

        templates, count = self.service.search_templates(
            filters=filters, user_id="user123", page=1, page_size=20
        )

        assert count == 10
        assert isinstance(templates, list)
        mock_query.filter.assert_called()
        mock_query.count.assert_called_once()

    def test_clone_template_success(self):
        """Test successful template cloning."""
        # Mock template retrieval
        original_template = Mock()
        original_template.clone_template.return_value = Mock()

        with patch.object(self.service, "get_template", return_value=original_template):
            result = self.service.clone_template(
                template_id=1, user_id="user123", new_name="Cloned Template"
            )

            assert result is not None
            original_template.clone_template.assert_called_once_with(
                "Cloned Template", "user123"
            )
            self.mock_db.add.assert_called()
            self.mock_db.commit.assert_called()

    def test_add_favorite_success(self):
        """Test adding template to favorites."""
        # Mock template retrieval
        mock_template = Mock()

        with patch.object(self.service, "get_template", return_value=mock_template):
            result = self.service.add_favorite(template_id=1, user_id="user123")

            assert result is True
            self.mock_db.add.assert_called()
            self.mock_db.commit.assert_called()

    def test_get_template_analytics(self):
        """Test template analytics retrieval."""
        # Mock template retrieval
        mock_template = Mock()
        mock_template.usage_count = 10
        mock_template.favorite_count = 5
        mock_template.last_used_at = datetime.utcnow()

        # Mock analytics query
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch.object(self.service, "get_template", return_value=mock_template):
            analytics = self.service.get_template_analytics(
                template_id=1, user_id="user123"
            )

            assert analytics["template_id"] == 1
            assert analytics["total_usage_count"] == 10
            assert analytics["favorite_count"] == 5
            assert "recent_30_days" in analytics


class TestTemplateImportExportService:
    """Test TemplateImportExportService functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.service = TemplateImportExportService(self.mock_db)

    def test_export_format_creation(self):
        """Test export format data structure creation."""
        mock_templates = [
            Mock(
                name="Template 1",
                description="Description 1",
                category="test",
                tags=["tag1"],
                version="1.0",
                is_public=True,
                is_featured=False,
                template_uuid="uuid1",
                created_at=datetime.utcnow(),
            ),
            Mock(
                name="Template 2",
                description="Description 2",
                category="test",
                tags=["tag2"],
                version="1.0",
                is_public=False,
                is_featured=True,
                template_uuid="uuid2",
                created_at=datetime.utcnow(),
            ),
        ]

        # Mock get_configuration method
        for template in mock_templates:
            template.get_configuration.return_value = {
                "quality": "high",
                "format": "mp4",
            }

        export_data = TemplateExportFormat.create_export_data(
            templates=mock_templates, include_metadata=True, include_analytics=False
        )

        assert export_data["format_version"] == "1.0"
        assert export_data["template_count"] == 2
        assert len(export_data["templates"]) == 2

        template_data = export_data["templates"][0]
        assert template_data["name"] == "Template 1"
        assert template_data["description"] == "Description 1"
        assert template_data["category"] == "test"
        assert template_data["tags"] == ["tag1"]
        assert "configuration" in template_data
        assert "metadata" in template_data

    def test_export_templates_success(self):
        """Test successful template export."""
        # Mock storage service
        mock_template = Mock()
        mock_template.name = "Test Template"
        mock_template.description = "Test description"
        mock_template.category = "test"
        mock_template.tags = ["tag1"]
        mock_template.version = "1.0"
        mock_template.get_configuration.return_value = {"quality": "high"}

        self.service.storage_service.get_template.return_value = mock_template

        export_data = self.service.export_templates(
            template_ids=[1],
            user_id="user123",
            include_metadata=True,
            include_analytics=False,
        )

        assert export_data["format_version"] == "1.0"
        assert export_data["template_count"] == 1
        assert len(export_data["templates"]) == 1

    def test_import_validation(self):
        """Test import data validation."""
        # Valid import data
        valid_data = {
            "format_version": "1.0",
            "templates": [
                {
                    "name": "Test Template",
                    "configuration": {"quality": "high", "format": "mp4"},
                }
            ],
        }

        # Should not raise exception
        self.service._validate_import_data(valid_data)

        # Invalid format version
        invalid_data = {"format_version": "2.0", "templates": []}

        with pytest.raises(ValueError, match="Unsupported format version"):
            self.service._validate_import_data(invalid_data)

        # Missing templates field
        invalid_data = {"format_version": "1.0"}

        with pytest.raises(ValueError, match="must contain 'templates' field"):
            self.service._validate_import_data(invalid_data)

    def test_import_result_tracking(self):
        """Test import result tracking."""
        result = TemplateImportResult()

        # Add successful import
        mock_template = Mock()
        mock_template.id = 1
        mock_template.template_uuid = "uuid1"
        mock_template.name = "Template 1"
        result.successful_imports.append(mock_template)

        # Add failed import
        result.failed_imports.append(
            {"name": "Failed Template", "error": "Validation error"}
        )

        # Add skipped import
        result.skipped_imports.append(
            {"name": "Skipped Template", "reason": "Name conflict"}
        )

        result.total_processed = 3

        assert result.success_count == 1
        assert result.failure_count == 1
        assert result.skipped_count == 1
        assert result.total_processed == 3

        result_dict = result.to_dict()
        assert result_dict["success_count"] == 1
        assert result_dict["failure_count"] == 1
        assert result_dict["skipped_count"] == 1
        assert len(result_dict["successful_imports"]) == 1
        assert len(result_dict["failed_imports"]) == 1
        assert len(result_dict["skipped_imports"]) == 1

    def test_import_preview(self):
        """Test import preview functionality."""
        import_data = {
            "format_version": "1.0",
            "templates": [
                {
                    "name": "Template 1",
                    "configuration": {"quality": "high", "format": "mp4"},
                },
                {
                    "name": "Template 2",
                    "configuration": {
                        "quality": "invalid",  # Invalid quality
                        "format": "mp4",
                    },
                },
            ],
        }

        # Mock database query for conflicts
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        preview = self.service.get_import_preview(
            import_data=import_data, user_id="user123"
        )

        assert preview["total_templates"] == 2
        assert len(preview["conflicts"]) == 0  # No conflicts in this test
        assert len(preview["valid_templates"]) == 1  # Template 1 is valid
        assert len(preview["invalid_templates"]) == 1  # Template 2 is invalid

    def test_json_string_import_export(self):
        """Test JSON string import/export functionality."""
        # Test JSON export
        mock_template = Mock()
        mock_template.name = "Test Template"
        mock_template.get_configuration.return_value = {"quality": "high"}

        self.service.storage_service.get_template.return_value = mock_template

        json_string = self.service.export_to_json_string(
            template_ids=[1], user_id="user123", pretty_print=True
        )

        assert isinstance(json_string, str)
        assert "Test Template" in json_string

        # Test JSON import
        import_data = {
            "format_version": "1.0",
            "templates": [
                {
                    "name": "Imported Template",
                    "configuration": {"quality": "high", "format": "mp4"},
                }
            ],
        }

        json_string = json.dumps(import_data)

        with patch.object(self.service, "import_templates") as mock_import:
            mock_import.return_value = TemplateImportResult()

            result = self.service.import_from_json_string(
                json_string=json_string, user_id="user123"
            )

            assert isinstance(result, TemplateImportResult)
            mock_import.assert_called_once()


class TestUserTemplateFavorite:
    """Test UserTemplateFavorite model functionality."""

    def test_favorite_creation(self):
        """Test creating a new favorite."""
        favorite = UserTemplateFavorite(user_id="user123", template_id=1)

        assert favorite.user_id == "user123"
        assert favorite.template_id == 1

    def test_favorite_to_dict(self):
        """Test favorite dictionary conversion."""
        # Mock template relationship
        mock_template = Mock()
        mock_template.template_uuid = "uuid123"
        mock_template.name = "Test Template"

        favorite = UserTemplateFavorite(user_id="user123", template_id=1)
        favorite.template = mock_template

        result = favorite.to_dict()

        assert result["user_id"] == "user123"
        assert result["template_id"] == 1
        assert result["template_uuid"] == "uuid123"
        assert result["template_name"] == "Test Template"


class TestTemplateUsageAnalytics:
    """Test TemplateUsageAnalytics model functionality."""

    def test_analytics_creation(self):
        """Test creating analytics record."""
        analytics = TemplateUsageAnalytics(
            template_id=1,
            user_id="user123",
            action="applied",
            camera_id="camera456",
            context_data={"profile_id": 789},
        )

        assert analytics.template_id == 1
        assert analytics.user_id == "user123"
        assert analytics.action == "applied"
        assert analytics.camera_id == "camera456"
        assert analytics.context_data == {"profile_id": 789}

    def test_analytics_to_dict(self):
        """Test analytics dictionary conversion."""
        analytics = TemplateUsageAnalytics(
            template_id=1,
            user_id="user123",
            action="favorited",
            context_data={"source": "api"},
        )

        result = analytics.to_dict()

        assert result["template_id"] == 1
        assert result["user_id"] == "user123"
        assert result["action"] == "favorited"
        assert result["context_data"] == {"source": "api"}


# Integration Tests


class TestTemplateIntegration:
    """Integration tests for template functionality."""

    def test_template_lifecycle(self):
        """Test complete template lifecycle: create, use, clone, favorite, delete."""
        # This would be an integration test that exercises the full workflow
        # In a real implementation, this would use a test database
        pass

    def test_import_export_roundtrip(self):
        """Test importing exported templates maintains data integrity."""
        # This would test that exporting templates and then importing them
        # results in equivalent templates
        pass

    def test_template_search_performance(self):
        """Test template search performance with large datasets."""
        # This would test search functionality with a large number of templates
        pass

    def test_concurrent_template_operations(self):
        """Test concurrent template operations for race conditions."""
        # This would test concurrent access to templates for thread safety
        pass
