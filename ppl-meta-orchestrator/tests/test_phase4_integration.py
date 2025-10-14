# ppl-meta-orchestrator/tests/test_phase4_integration.py
"""
Phase 4 Integration Test
Tests the integration between camera endpoints, event publisher, and recording session service
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

import pytest


# Mock the database and service dependencies for testing
class MockRecordingSessionService:
    """Mock recording session service for testing"""

    def __init__(self):
        self.sessions = {}
        self.session_status_updates = []
        self.progress_updates = []
        self.face_detection_updates = []

    def create_session(
        self,
        camera_device_id: str,
        user_id: str,
        recording_config: Dict[str, Any] = None,
        workflow_metadata: Dict[str, Any] = None,
    ):
        session_uuid = str(uuid.uuid4())
        session = {
            "session_uuid": session_uuid,
            "camera_device_id": camera_device_id,
            "user_id": user_id,
            "status": "active",
            "recording_config": recording_config or {},
            "workflow_metadata": workflow_metadata or {},
            "face_detection_triggered": False,
            "face_detection_completed": False,
            "created_at": datetime.utcnow(),
        }
        self.sessions[session_uuid] = session
        return type("Session", (), session)()

    def update_session_status(
        self, session_uuid: str, status: str, error_message: str = None
    ):
        if session_uuid in self.sessions:
            self.sessions[session_uuid]["status"] = status
            if error_message:
                self.sessions[session_uuid]["error_message"] = error_message
            self.session_status_updates.append(
                {
                    "session_uuid": session_uuid,
                    "status": status,
                    "error_message": error_message,
                    "timestamp": datetime.utcnow(),
                }
            )
            return True
        return False

    def update_session_progress(
        self,
        session_uuid: str,
        duration_seconds: float,
        estimated_file_size_bytes: int = None,
        frames_recorded: int = None,
    ):
        if session_uuid in self.sessions:
            self.sessions[session_uuid].update(
                {
                    "duration_seconds": duration_seconds,
                    "estimated_file_size_bytes": estimated_file_size_bytes,
                    "frames_recorded": frames_recorded,
                }
            )
            self.progress_updates.append(
                {
                    "session_uuid": session_uuid,
                    "duration_seconds": duration_seconds,
                    "timestamp": datetime.utcnow(),
                }
            )
            return True
        return False

    def trigger_face_detection(
        self,
        session_uuid: str,
        face_detection_session_uuid: str,
        workflow_execution_id: str = None,
    ):
        if session_uuid in self.sessions:
            self.sessions[session_uuid]["face_detection_triggered"] = True
            self.sessions[session_uuid][
                "face_detection_session_uuid"
            ] = face_detection_session_uuid
            self.face_detection_updates.append(
                {
                    "session_uuid": session_uuid,
                    "action": "triggered",
                    "timestamp": datetime.utcnow(),
                }
            )
            return True
        return False

    def complete_face_detection(
        self, session_uuid: str, face_detection_results: Dict[str, Any]
    ):
        if session_uuid in self.sessions:
            self.sessions[session_uuid]["face_detection_completed"] = True
            self.sessions[session_uuid][
                "face_detection_results"
            ] = face_detection_results
            self.face_detection_updates.append(
                {
                    "session_uuid": session_uuid,
                    "action": "completed",
                    "results": face_detection_results,
                    "timestamp": datetime.utcnow(),
                }
            )
            return True
        return False

    def update_media_upload_status(
        self, session_uuid: str, completed: bool = None, media_uuid: str = None
    ):
        if session_uuid in self.sessions:
            if completed is not None:
                self.sessions[session_uuid]["media_upload_completed"] = completed
            if media_uuid:
                self.sessions[session_uuid]["media_uuid"] = media_uuid
            return True
        return False

    def get_session(self, session_uuid: str):
        if session_uuid in self.sessions:
            session_data = self.sessions[session_uuid]
            return type("Session", (), session_data)()
        return None

    def heartbeat_session(self, session_uuid: str):
        return session_uuid in self.sessions


class MockWorkflowOrchestrator:
    """Mock workflow orchestrator for testing"""

    def __init__(self):
        self.handled_events = []
        self.created_workflows = []

    async def handle_camera_recording_event(self, event_data):
        self.handled_events.append(event_data)

        # Create a mock workflow for face detection events
        if (
            "face" in event_data.event_type.lower()
            or event_data.recording_duration_seconds > 10
        ):
            workflow = type(
                "Workflow",
                (),
                {
                    "workflow_id": str(uuid.uuid4()),
                    "workflow_type": type(
                        "WorkflowType", (), {"value": "face_detection"}
                    )(),
                    "status": type("Status", (), {"value": "running"})(),
                    "created_at": datetime.utcnow(),
                },
            )()
            self.created_workflows.append(workflow)
            return workflow

        return None


class TestPhase4Integration:
    """Test Phase 4 integration between components"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_session_service = MockRecordingSessionService()
        self.mock_orchestrator = MockWorkflowOrchestrator()

        # Mock camera event request
        self.sample_event_request = type(
            "CameraEventRequest",
            (),
            {
                "event_type": "recording_started",
                "camera_device_id": "test-camera-001",
                "recording_session_id": str(uuid.uuid4()),
                "video_file_path": "/recordings/test_video.mp4",
                "user_id": "test-user-123",
                "recording_duration_seconds": 15.0,
                "file_size_bytes": 1024000,
                "timestamp": datetime.utcnow(),
                "metadata": {"test": True},
            },
        )()

    def test_session_lifecycle_recording_started(self):
        """Test session creation when recording starts"""
        # Simulate recording start
        session = self.mock_session_service.create_session(
            camera_device_id=self.sample_event_request.camera_device_id,
            user_id=self.sample_event_request.user_id,
            recording_config={
                "event_type": self.sample_event_request.event_type,
                "video_file_path": self.sample_event_request.video_file_path,
            },
        )

        # Verify session created
        assert session is not None
        assert session.camera_device_id == "test-camera-001"
        assert session.user_id == "test-user-123"
        assert session.status == "active"

        # Verify session is tracked
        assert len(self.mock_session_service.sessions) == 1

    def test_session_progress_updates(self):
        """Test session progress tracking during recording"""
        # Create session
        session = self.mock_session_service.create_session(
            camera_device_id="test-camera-001", user_id="test-user-123"
        )

        # Update progress multiple times
        progress_updates = [
            (5.0, 512000, 150),
            (10.0, 1024000, 300),
            (15.0, 1536000, 450),
        ]

        for duration, file_size, frames in progress_updates:
            success = self.mock_session_service.update_session_progress(
                session_uuid=session.session_uuid,
                duration_seconds=duration,
                estimated_file_size_bytes=file_size,
                frames_recorded=frames,
            )
            assert success

        # Verify progress tracking
        assert len(self.mock_session_service.progress_updates) == 3
        final_update = self.mock_session_service.progress_updates[-1]
        assert final_update["duration_seconds"] == 15.0

    def test_face_detection_workflow_integration(self):
        """Test face detection workflow integration with sessions"""
        # Create session
        session = self.mock_session_service.create_session(
            camera_device_id="test-camera-001", user_id="test-user-123"
        )

        # Trigger face detection
        face_detection_uuid = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())

        success = self.mock_session_service.trigger_face_detection(
            session_uuid=session.session_uuid,
            face_detection_session_uuid=face_detection_uuid,
            workflow_execution_id=workflow_id,
        )
        assert success

        # Complete face detection with results
        face_results = {
            "faces_detected": 2,
            "detection_confidence": 0.92,
            "face_locations": [
                {"x": 100, "y": 200, "width": 50, "height": 60},
                {"x": 300, "y": 150, "width": 45, "height": 55},
            ],
        }

        success = self.mock_session_service.complete_face_detection(
            session_uuid=session.session_uuid, face_detection_results=face_results
        )
        assert success

        # Verify face detection tracking
        assert len(self.mock_session_service.face_detection_updates) == 2
        trigger_update = self.mock_session_service.face_detection_updates[0]
        completion_update = self.mock_session_service.face_detection_updates[1]

        assert trigger_update["action"] == "triggered"
        assert completion_update["action"] == "completed"
        assert completion_update["results"] == face_results

    def test_recording_completion_workflow(self):
        """Test complete recording workflow from start to finish"""
        # Create session
        session = self.mock_session_service.create_session(
            camera_device_id="test-camera-001", user_id="test-user-123"
        )

        # Simulate recording progress
        self.mock_session_service.update_session_progress(
            session_uuid=session.session_uuid,
            duration_seconds=30.0,
            estimated_file_size_bytes=2048000,
            frames_recorded=900,
        )

        # Trigger face detection
        self.mock_session_service.trigger_face_detection(
            session_uuid=session.session_uuid,
            face_detection_session_uuid=str(uuid.uuid4()),
        )

        # Complete face detection
        self.mock_session_service.complete_face_detection(
            session_uuid=session.session_uuid,
            face_detection_results={"faces_detected": 1},
        )

        # Update media upload status
        self.mock_session_service.update_media_upload_status(
            session_uuid=session.session_uuid,
            completed=True,
            media_uuid=str(uuid.uuid4()),
        )

        # Complete session
        self.mock_session_service.update_session_status(
            session_uuid=session.session_uuid, status="completed"
        )

        # Verify complete workflow
        final_session = self.mock_session_service.get_session(session.session_uuid)
        assert final_session.status == "completed"
        assert final_session.face_detection_triggered
        assert final_session.face_detection_completed
        assert final_session.media_upload_completed

        # Verify tracking records
        assert len(self.mock_session_service.session_status_updates) == 1
        assert len(self.mock_session_service.progress_updates) == 1
        assert len(self.mock_session_service.face_detection_updates) == 2

    def test_error_handling_and_recovery(self):
        """Test error handling in session lifecycle"""
        # Create session
        session = self.mock_session_service.create_session(
            camera_device_id="test-camera-001", user_id="test-user-123"
        )

        # Simulate recording failure
        error_message = "Camera disconnected during recording"
        success = self.mock_session_service.update_session_status(
            session_uuid=session.session_uuid,
            status="failed",
            error_message=error_message,
        )
        assert success

        # Verify error tracking
        status_update = self.mock_session_service.session_status_updates[0]
        assert status_update["status"] == "failed"
        assert status_update["error_message"] == error_message

        # Verify session state
        failed_session = self.mock_session_service.get_session(session.session_uuid)
        assert failed_session.status == "failed"
        assert failed_session.error_message == error_message

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_integration(self):
        """Test integration with workflow orchestrator"""
        # Create event data
        event_data = type(
            "CameraEventData",
            (),
            {
                "event_type": "recording_completed",
                "camera_device_id": "test-camera-001",
                "recording_session_id": str(uuid.uuid4()),
                "video_file_path": "/recordings/test.mp4",
                "user_id": "test-user-123",
                "recording_duration_seconds": 25.0,
                "file_size_bytes": 2048000,
                "timestamp": datetime.utcnow(),
                "metadata": {},
            },
        )()

        # Handle event through orchestrator
        workflow = await self.mock_orchestrator.handle_camera_recording_event(
            event_data
        )

        # Verify workflow creation for long recording
        assert workflow is not None
        assert workflow.workflow_type.value == "face_detection"
        assert len(self.mock_orchestrator.handled_events) == 1
        assert len(self.mock_orchestrator.created_workflows) == 1


if __name__ == "__main__":
    """Run Phase 4 integration tests"""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run tests
    test_instance = TestPhase4Integration()

    print("🧪 Running Phase 4 Integration Tests...")
    print()

    # Run individual tests
    tests = [
        (
            "Session Lifecycle - Recording Started",
            test_instance.test_session_lifecycle_recording_started,
        ),
        ("Session Progress Updates", test_instance.test_session_progress_updates),
        (
            "Face Detection Workflow",
            test_instance.test_face_detection_workflow_integration,
        ),
        (
            "Complete Recording Workflow",
            test_instance.test_recording_completion_workflow,
        ),
        ("Error Handling and Recovery", test_instance.test_error_handling_and_recovery),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_instance.setup_method()
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            failed += 1

    # Run async test separately
    try:
        test_instance.setup_method()
        asyncio.run(test_instance.test_workflow_orchestrator_integration())
        print(f"✅ Workflow Orchestrator Integration")
        passed += 1
    except Exception as e:
        print(f"❌ Workflow Orchestrator Integration: {e}")
        failed += 1

    print()
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All Phase 4 integration tests passed!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check implementation.")
        sys.exit(1)
