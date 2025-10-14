# ppl-meta-orchestrator/tests/test_recording_session_integration.py
"""
Recording Session Integration Tests - Phase 4 Implementation
Comprehensive tests for recording session workflow and orchestrator integration
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..src.api.recording_session_endpoints import router
from ..src.models.recording_session import RecordingSession, SessionStatus
from ..src.services.recording_session_service import RecordingSessionService

logger = logging.getLogger(__name__)

# Test Database Setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_recording_sessions.db"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


class TestRecordingSessionIntegration:
    """Integration tests for recording session management"""

    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        # Create tables
        from ..src.models.recording_session import Base

        Base.metadata.create_all(bind=test_engine)

        # Create session
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            # Clean up
            Base.metadata.drop_all(bind=test_engine)

    @pytest.fixture
    def recording_service(self, db_session):
        """Create a recording session service"""
        return RecordingSessionService(db_session)

    @pytest.fixture
    def sample_session_data(self):
        """Sample data for testing"""
        return {
            "camera_device_id": "test-camera-001",
            "user_id": "test-user-123",
            "recording_profile_id": 1,
            "recording_config": {
                "quality": "high",
                "duration": 30,
                "format": "mp4",
                "fps": 30,
            },
            "workflow_metadata": {
                "workflow_type": "automatic",
                "trigger_source": "motion_detection",
            },
        }

    def test_create_recording_session(self, recording_service, sample_session_data):
        """Test creating a new recording session"""
        session = recording_service.create_session(**sample_session_data)

        assert session is not None
        assert session.session_uuid is not None
        assert session.camera_device_id == sample_session_data["camera_device_id"]
        assert session.user_id == sample_session_data["user_id"]
        assert session.status == SessionStatus.ACTIVE
        assert session.started_at is not None
        assert session.last_heartbeat is not None
        assert session.current_duration_seconds == 0.0
        assert session.frames_recorded == 0
        assert not session.face_detection_triggered
        assert not session.face_detection_completed
        assert not session.media_upload_started
        assert not session.media_upload_completed

    def test_session_progress_tracking(self, recording_service, sample_session_data):
        """Test session progress updates"""
        session = recording_service.create_session(**sample_session_data)
        session_uuid = session.session_uuid

        # Update progress multiple times to simulate recording
        progress_updates = [
            {"duration": 5.0, "frames": 150, "fps": 30.0, "file_size": 1024000},
            {"duration": 10.0, "frames": 300, "fps": 30.0, "file_size": 2048000},
            {"duration": 15.0, "frames": 450, "fps": 30.0, "file_size": 3072000},
        ]

        for update in progress_updates:
            success = recording_service.update_session_progress(
                session_uuid=session_uuid,
                duration_seconds=update["duration"],
                frames_recorded=update["frames"],
                average_fps=update["fps"],
                estimated_file_size_bytes=update["file_size"],
            )
            assert success

        # Verify final state
        updated_session = recording_service.get_session(session_uuid)
        assert updated_session.current_duration_seconds == 15.0
        assert updated_session.frames_recorded == 450
        assert updated_session.average_fps == 30.0
        assert updated_session.estimated_file_size_bytes == 3072000

    def test_face_detection_workflow(self, recording_service, sample_session_data):
        """Test face detection workflow integration"""
        session = recording_service.create_session(**sample_session_data)
        session_uuid = session.session_uuid
        face_detection_uuid = str(uuid.uuid4())
        workflow_execution_id = str(uuid.uuid4())

        # Trigger face detection
        success = recording_service.trigger_face_detection(
            session_uuid=session_uuid,
            face_detection_session_uuid=face_detection_uuid,
            workflow_execution_id=workflow_execution_id,
        )
        assert success

        # Verify trigger state
        updated_session = recording_service.get_session(session_uuid)
        assert updated_session.face_detection_triggered
        assert updated_session.face_detection_session_uuid == face_detection_uuid
        assert updated_session.workflow_execution_id == workflow_execution_id
        assert not updated_session.face_detection_completed

        # Complete face detection with results
        face_detection_results = {
            "faces_detected": 3,
            "detection_confidence": 0.95,
            "face_locations": [
                {"x": 100, "y": 200, "width": 50, "height": 60},
                {"x": 300, "y": 150, "width": 45, "height": 55},
                {"x": 500, "y": 250, "width": 48, "height": 58},
            ],
        }

        success = recording_service.complete_face_detection(
            session_uuid=session_uuid, face_detection_results=face_detection_results
        )
        assert success

        # Verify completion state
        final_session = recording_service.get_session(session_uuid)
        assert final_session.face_detection_completed
        assert (
            final_session.workflow_metadata["face_detection_results"]
            == face_detection_results
        )

    def test_media_upload_workflow(self, recording_service, sample_session_data):
        """Test media upload workflow integration"""
        session = recording_service.create_session(**sample_session_data)
        session_uuid = session.session_uuid
        media_collection_id = str(uuid.uuid4())
        media_uuid = str(uuid.uuid4())

        # Start media upload
        success = recording_service.update_media_upload_status(
            session_uuid=session_uuid,
            started=True,
            media_collection_id=media_collection_id,
        )
        assert success

        # Verify upload started
        updated_session = recording_service.get_session(session_uuid)
        assert updated_session.media_upload_started
        assert updated_session.media_collection_id == media_collection_id
        assert not updated_session.media_upload_completed

        # Complete media upload
        success = recording_service.update_media_upload_status(
            session_uuid=session_uuid, completed=True, media_uuid=media_uuid
        )
        assert success

        # Verify upload completed
        final_session = recording_service.get_session(session_uuid)
        assert final_session.media_upload_completed
        assert final_session.media_uuid == media_uuid

    def test_complete_session_lifecycle(self, recording_service, sample_session_data):
        """Test complete session lifecycle from start to finish"""
        # Create session
        session = recording_service.create_session(**sample_session_data)
        session_uuid = session.session_uuid

        # Simulate recording progress
        for i in range(1, 6):  # 5 updates over 25 seconds
            recording_service.update_session_progress(
                session_uuid=session_uuid,
                duration_seconds=i * 5.0,
                frames_recorded=i * 150,
                average_fps=30.0,
                estimated_file_size_bytes=i * 1024000,
            )

        # Trigger face detection at 15 seconds
        face_detection_uuid = str(uuid.uuid4())
        recording_service.trigger_face_detection(
            session_uuid=session_uuid, face_detection_session_uuid=face_detection_uuid
        )

        # Start media upload at 20 seconds
        media_collection_id = str(uuid.uuid4())
        recording_service.update_media_upload_status(
            session_uuid=session_uuid,
            started=True,
            media_collection_id=media_collection_id,
        )

        # Complete face detection at 23 seconds
        recording_service.complete_face_detection(
            session_uuid=session_uuid, face_detection_results={"faces_detected": 2}
        )

        # Complete recording at 25 seconds
        recording_service.update_session_status(
            session_uuid=session_uuid, status=SessionStatus.COMPLETED
        )

        # Complete media upload
        media_uuid = str(uuid.uuid4())
        recording_service.update_media_upload_status(
            session_uuid=session_uuid, completed=True, media_uuid=media_uuid
        )

        # Verify final session state
        final_session = recording_service.get_session(session_uuid)
        assert final_session.status == SessionStatus.COMPLETED
        assert final_session.current_duration_seconds == 25.0
        assert final_session.frames_recorded == 750
        assert final_session.face_detection_triggered
        assert final_session.face_detection_completed
        assert final_session.media_upload_started
        assert final_session.media_upload_completed
        assert final_session.stopped_at is not None

    def test_session_monitoring_and_cleanup(
        self, recording_service, sample_session_data
    ):
        """Test session monitoring and stale session cleanup"""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session_data = sample_session_data.copy()
            session_data["camera_device_id"] = f"camera-{i:03d}"
            session = recording_service.create_session(**session_data)
            sessions.append(session)

        # Simulate one session going stale (no heartbeat)
        stale_session = sessions[0]
        active_sessions = sessions[1:]

        # Update heartbeats for active sessions
        for session in active_sessions:
            recording_service.heartbeat_session(session.session_uuid)

        # Manually set stale session heartbeat to old timestamp
        stale_session.last_heartbeat = datetime.utcnow() - timedelta(minutes=10)
        recording_service.db.commit()

        # Find stale sessions
        stale_found = recording_service.find_stale_sessions(heartbeat_timeout_minutes=5)
        assert len(stale_found) == 1
        assert stale_found[0].session_uuid == stale_session.session_uuid

        # Cleanup stale sessions
        cleanup_count = recording_service.cleanup_stale_sessions(
            heartbeat_timeout_minutes=5
        )
        assert cleanup_count == 1

        # Verify stale session marked as timeout
        updated_stale = recording_service.get_session(stale_session.session_uuid)
        assert updated_stale.status == SessionStatus.TIMEOUT

    def test_session_statistics(self, recording_service, sample_session_data):
        """Test session statistics generation"""
        # Create sessions with various states
        sessions_data = [
            {
                "status": SessionStatus.COMPLETED,
                "duration": 30.0,
                "face_detection": True,
            },
            {
                "status": SessionStatus.COMPLETED,
                "duration": 25.0,
                "face_detection": True,
            },
            {"status": SessionStatus.FAILED, "duration": 10.0, "face_detection": False},
            {"status": SessionStatus.ACTIVE, "duration": 15.0, "face_detection": True},
        ]

        camera_id = "test-camera-stats"
        user_id = "test-user-stats"

        for i, session_data in enumerate(sessions_data):
            # Create session
            data = sample_session_data.copy()
            data["camera_device_id"] = camera_id
            data["user_id"] = user_id
            session = recording_service.create_session(**data)

            # Update duration and status
            recording_service.update_session_progress(
                session_uuid=session.session_uuid,
                duration_seconds=session_data["duration"],
                frames_recorded=int(session_data["duration"] * 30),
            )

            if session_data["face_detection"]:
                recording_service.trigger_face_detection(
                    session_uuid=session.session_uuid,
                    face_detection_session_uuid=str(uuid.uuid4()),
                )
                recording_service.complete_face_detection(
                    session_uuid=session.session_uuid
                )

            if session_data["status"] != SessionStatus.ACTIVE:
                recording_service.update_session_status(
                    session_uuid=session.session_uuid, status=session_data["status"]
                )

        # Get statistics
        stats = recording_service.get_session_statistics(
            camera_device_id=camera_id, user_id=user_id
        )

        assert stats["total_sessions"] == 4
        assert stats["active_sessions"] == 1
        assert stats["completed_sessions"] == 2
        assert stats["failed_sessions"] == 1
        assert stats["success_rate"] == 0.5  # 2 completed out of 4 total
        assert stats["face_detection_trigger_rate"] == 0.75  # 3 out of 4
        assert (
            stats["face_detection_completion_rate"] == 1.0
        )  # 3 completed out of 3 triggered

    def test_concurrent_session_management(
        self, recording_service, sample_session_data
    ):
        """Test concurrent session management for the same camera"""
        camera_id = "test-camera-concurrent"
        user_id = "test-user-concurrent"

        # Create multiple sessions for the same camera
        sessions = []
        for i in range(3):
            data = sample_session_data.copy()
            data["camera_device_id"] = camera_id
            data["user_id"] = f"{user_id}-{i}"
            session = recording_service.create_session(**data)
            sessions.append(session)

        # Verify all sessions are active
        active_sessions = recording_service.get_active_sessions(
            camera_device_id=camera_id
        )
        assert len(active_sessions) == 3

        # Complete one session
        recording_service.update_session_status(
            sessions[0].session_uuid, SessionStatus.COMPLETED
        )

        # Verify active count decreased
        active_sessions = recording_service.get_active_sessions(
            camera_device_id=camera_id
        )
        assert len(active_sessions) == 2

        # Get all sessions for camera (including completed)
        all_camera_sessions = recording_service.get_sessions_by_camera(camera_id)
        assert len(all_camera_sessions) == 3

    def test_error_handling_and_recovery(self, recording_service, sample_session_data):
        """Test error handling and session recovery"""
        session = recording_service.create_session(**sample_session_data)
        session_uuid = session.session_uuid

        # Simulate recording error
        error_message = "Camera disconnected during recording"
        success = recording_service.update_session_status(
            session_uuid=session_uuid,
            status=SessionStatus.FAILED,
            error_message=error_message,
        )
        assert success

        # Verify error state
        failed_session = recording_service.get_session(session_uuid)
        assert failed_session.status == SessionStatus.FAILED
        assert failed_session.error_message == error_message
        assert failed_session.retry_count == 1
        assert failed_session.stopped_at is not None

        # Test invalid session operations
        fake_uuid = str(uuid.uuid4())

        # Attempt operations on non-existent session
        assert not recording_service.update_session_status(
            fake_uuid, SessionStatus.COMPLETED
        )
        assert not recording_service.update_session_progress(fake_uuid, 10.0, 300)
        assert not recording_service.heartbeat_session(fake_uuid)
        assert not recording_service.trigger_face_detection(
            fake_uuid, str(uuid.uuid4())
        )


class TestRecordingSessionAPI:
    """Integration tests for recording session REST API"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_api_create_session(self, client):
        """Test creating session via API"""
        session_data = {
            "camera_device_id": "api-test-camera",
            "user_id": "api-test-user",
            "recording_config": {"quality": "high"},
            "workflow_metadata": {"source": "api_test"},
        }

        response = client.post("/api/v1/recording-sessions/", json=session_data)
        assert response.status_code == 200

        data = response.json()
        assert data["camera_device_id"] == session_data["camera_device_id"]
        assert data["user_id"] == session_data["user_id"]
        assert data["status"] == "active"
        assert "session_uuid" in data

    def test_api_session_lifecycle(self, client):
        """Test complete session lifecycle via API"""
        # Create session
        session_data = {
            "camera_device_id": "api-lifecycle-camera",
            "user_id": "api-lifecycle-user",
        }

        create_response = client.post("/api/v1/recording-sessions/", json=session_data)
        assert create_response.status_code == 200
        session_uuid = create_response.json()["session_uuid"]

        # Update progress
        progress_data = {
            "duration_seconds": 10.0,
            "frames_recorded": 300,
            "estimated_file_size_bytes": 2048000,
        }

        progress_response = client.put(
            f"/api/v1/recording-sessions/{session_uuid}/progress", json=progress_data
        )
        assert progress_response.status_code == 200

        # Trigger face detection
        face_detection_data = {"face_detection_session_uuid": str(uuid.uuid4())}

        face_detection_response = client.post(
            f"/api/v1/recording-sessions/{session_uuid}/face-detection/trigger",
            json=face_detection_data,
        )
        assert face_detection_response.status_code == 200

        # Complete session
        status_data = {"status": "completed"}

        status_response = client.put(
            f"/api/v1/recording-sessions/{session_uuid}/status", json=status_data
        )
        assert status_response.status_code == 200

        # Get final session state
        get_response = client.get(f"/api/v1/recording-sessions/{session_uuid}")
        assert get_response.status_code == 200

        final_data = get_response.json()
        assert final_data["status"] == "completed"
        assert final_data["current_duration_seconds"] == 10.0
        assert final_data["face_detection_triggered"] is True


if __name__ == "__main__":
    """Run integration tests for Phase 4 recording session implementation"""
    import os
    import sys

    # Add project root to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
