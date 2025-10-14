# ppl-meta-cameras/tests/test_recording_profiles.py

"""
Tests for Recording Profile functionality
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.orm import Session
from src.models.recording_profile import CameraRecordingProfile
from src.services.recording_profile_service import RecordingProfileService


class TestCameraRecordingProfile:
    """Test the CameraRecordingProfile model."""

    def test_create_system_defaults(self):
        """Test creation of system default profiles."""
        defaults = CameraRecordingProfile.create_system_defaults()

        assert len(defaults) == 5
        assert all(profile.is_system_default for profile in defaults)
        assert all(profile.created_by_user_id == "system" for profile in defaults)

        # Check specific profiles exist
        profile_names = [profile.name for profile in defaults]
        expected_names = [
            "Manual Recording Only",
            "Security Monitor",
            "Activity Logger",
            "Event Detection",
            "High Traffic",
        ]

        for expected_name in expected_names:
            assert expected_name in profile_names

    def test_validate_configuration_valid(self):
        """Test configuration validation with valid parameters."""
        profile = CameraRecordingProfile(
            name="Test Profile",
            segment_interval_seconds=60,
            segment_duration_seconds=30,
            recording_quality="high",
            video_codec="h264",
            storage_location="local",
            retention_days=30,
        )

        errors = profile.validate_configuration()
        assert errors == {}

    def test_validate_configuration_invalid_interval(self):
        """Test configuration validation with invalid interval."""
        profile = CameraRecordingProfile(
            name="Test Profile",
            segment_interval_seconds=3,  # Too low
            segment_duration_seconds=30,
        )

        errors = profile.validate_configuration()
        assert "segment_interval" in errors
        assert "5 seconds" in errors["segment_interval"]

    def test_validate_configuration_invalid_duration(self):
        """Test configuration validation with invalid duration."""
        profile = CameraRecordingProfile(
            name="Test Profile", segment_duration_seconds=400  # Too high
        )

        errors = profile.validate_configuration()
        assert "segment_duration" in errors
        assert "5 minutes" in errors["segment_duration"]

    def test_is_manual_only_property(self):
        """Test the is_manual_only property."""
        # Manual only profile
        manual_profile = CameraRecordingProfile(
            name="Manual", segment_interval_seconds=None, auto_segment_recording=False
        )
        assert manual_profile.is_manual_only

        # Automatic profile
        auto_profile = CameraRecordingProfile(
            name="Auto", segment_interval_seconds=60, auto_segment_recording=True
        )
        assert not auto_profile.is_manual_only

    def test_clone_profile(self):
        """Test profile cloning functionality."""
        original = CameraRecordingProfile(
            name="Original Profile",
            description="Original description",
            segment_interval_seconds=60,
            segment_duration_seconds=30,
            recording_quality="high",
            created_by_user_id="user1",
        )

        cloned = original.clone("Cloned Profile", "user2")

        assert cloned.name == "Cloned Profile"
        assert cloned.created_by_user_id == "user2"
        assert not cloned.is_system_default  # Clones are never system defaults
        assert cloned.segment_interval_seconds == original.segment_interval_seconds
        assert cloned.segment_duration_seconds == original.segment_duration_seconds
        assert cloned.recording_quality == original.recording_quality
        assert "Cloned from:" in cloned.description


class TestRecordingProfileService:
    """Test the RecordingProfileService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def service(self, mock_db):
        """Create a RecordingProfileService instance."""
        return RecordingProfileService(mock_db)

    @pytest.mark.asyncio
    async def test_create_profile_valid(self, service, mock_db):
        """Test creating a valid recording profile."""
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        profile = await service.create_profile(
            name="Test Profile",
            created_by_user_id="user123",
            description="Test description",
            segment_interval_seconds=60,
            segment_duration_seconds=30,
        )

        assert profile.name == "Test Profile"
        assert profile.created_by_user_id == "user123"
        assert not profile.is_system_default

        # Verify database operations were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_invalid_validation(self, service):
        """Test creating a profile with invalid configuration."""
        with pytest.raises(ValueError) as exc_info:
            await service.create_profile(
                name="Invalid Profile",
                created_by_user_id="user123",
                segment_interval_seconds=3,  # Invalid - too low
                segment_duration_seconds=30,
            )

        assert "validation failed" in str(exc_info.value)
        assert "5 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_profiles(self, service, mock_db):
        """Test getting user profiles with system defaults."""
        # Mock database query
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        # Create mock profiles
        user_profile = Mock()
        user_profile.created_by_user_id = "user123"
        user_profile.is_system_default = False

        system_profile = Mock()
        system_profile.created_by_user_id = "system"
        system_profile.is_system_default = True

        mock_query.all.return_value = [user_profile, system_profile]

        profiles = await service.get_user_profiles(
            user_id="user123", include_system_defaults=True
        )

        assert len(profiles) == 2
        mock_db.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_profile_to_camera_success(self, service, mock_db):
        """Test successful profile assignment to camera."""
        # Mock profile lookup
        service.get_profile_by_id = AsyncMock()
        mock_profile = Mock()
        mock_profile.update_usage_stats = Mock()
        service.get_profile_by_id.return_value = mock_profile

        # Mock user profile access
        service.get_user_profiles = AsyncMock()
        service.get_user_profiles.return_value = [mock_profile]

        # Mock database execute
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = Mock()

        success = await service.assign_profile_to_camera(
            camera_id=1, profile_id=1, user_id="user123"
        )

        assert success
        mock_profile.update_usage_stats.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_profile_to_camera_no_access(self, service, mock_db):
        """Test profile assignment when user has no access to profile."""
        # Mock profile lookup
        service.get_profile_by_id = AsyncMock()
        mock_profile = Mock()
        service.get_profile_by_id.return_value = mock_profile

        # Mock user profile access (empty list - no access)
        service.get_user_profiles = AsyncMock()
        service.get_user_profiles.return_value = []

        success = await service.assign_profile_to_camera(
            camera_id=1, profile_id=1, user_id="user123"
        )

        assert not success
        mock_db.execute.assert_not_called()


class TestRecordingProfileEndpoints:
    """Test the recording profile API endpoints."""

    # Note: These would typically be integration tests using FastAPI's TestClient
    # For now, we'll include placeholder tests

    def test_create_profile_endpoint_placeholder(self):
        """Placeholder for create profile endpoint test."""
        # TODO: Implement with FastAPI TestClient
        pass

    def test_get_profiles_endpoint_placeholder(self):
        """Placeholder for get profiles endpoint test."""
        # TODO: Implement with FastAPI TestClient
        pass

    def test_assign_profile_endpoint_placeholder(self):
        """Placeholder for profile assignment endpoint test."""
        # TODO: Implement with FastAPI TestClient
        pass


# Integration test placeholders
class TestRecordingProfileIntegration:
    """Integration tests for recording profile functionality."""

    def test_end_to_end_profile_lifecycle_placeholder(self):
        """Placeholder for end-to-end profile lifecycle test."""
        # TODO: Implement full integration test
        # 1. Create profile
        # 2. Assign to camera
        # 3. Verify automatic recording triggers
        # 4. Update profile
        # 5. Clone profile
        # 6. Delete profile
        pass

    def test_system_default_profiles_seeded_placeholder(self):
        """Placeholder for verifying system defaults are properly seeded."""
        # TODO: Test that migration creates all expected system default profiles
        pass
