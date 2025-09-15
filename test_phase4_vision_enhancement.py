#!/usr/bin/env python3
"""
PPL Meta Vision Service - Phase 4 Integration Tests
Vision Service Enhancement & Storage Optimization Test Suite

This comprehensive test suite validates Phase 4 implementation including:
- Enhanced face storage with session context
- Processing status management
- Frame-indexed face retrieval
- Session analytics
- Cross-service integration
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
import pytest


class Phase4VisionIntegrationTest:
    """Comprehensive test suite for Phase 4 Vision Service enhancements."""

    def __init__(self):
        self.vision_service_url = "http://localhost:8003"
        self.media_service_url = "http://localhost:8080"  # Via gateway
        self.test_session = None
        self.test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": [],
            "start_time": None,
            "end_time": None,
        }

    async def run_all_tests(self):
        """Execute complete Phase 4 test suite."""
        print("🧪 Starting Phase 4 Vision Service Enhancement Tests")
        print("=" * 60)

        self.test_results["start_time"] = datetime.now(timezone.utc)

        try:
            # Initialize test session
            async with aiohttp.ClientSession() as session:
                self.test_session = session

                # Test 1: Service Health and Availability
                await self._test_service_health()

                # Test 2: Session Management Integration
                await self._test_session_management()

                # Test 3: Enhanced Face Storage with Session Context
                await self._test_enhanced_face_storage()

                # Test 4: Processing Status Management
                await self._test_processing_status_management()

                # Test 5: Frame-Indexed Face Retrieval
                await self._test_frame_indexed_retrieval()

                # Test 6: Session Analytics
                await self._test_session_analytics()

                # Test 7: Cross-Service Integration
                await self._test_cross_service_integration()

                # Test 8: Error Handling and Edge Cases
                await self._test_error_handling()

        except Exception as e:
            await self._record_failure("Test Suite Execution", str(e))

        finally:
            self.test_results["end_time"] = datetime.now(timezone.utc)
            await self._print_test_summary()

    async def _test_service_health(self):
        """Test 1: Verify Vision service health and API availability."""
        test_name = "Service Health Check"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            # Check basic health endpoint
            async with self.test_session.get(
                f"{self.vision_service_url}/health"
            ) as response:
                assert response.status == 200, f"Health check failed: {response.status}"
                health_data = await response.json()

                assert "status" in health_data, "Health response missing status"
                print(f"   ✅ Health endpoint: {health_data.get('status')}")

            # Check API documentation endpoint
            async with self.test_session.get(
                f"{self.vision_service_url}/docs"
            ) as response:
                assert response.status == 200, "API docs not accessible"
                print("   ✅ API documentation accessible")

            # Check new Phase 4 endpoints are registered
            endpoints_to_check = [
                "/faces/store",
                "/processing-status/test-media",
                "/faces/media/test-media/frames",
                "/faces/session/test-session/analytics",
            ]

            for endpoint in endpoints_to_check:
                async with self.test_session.get(
                    f"{self.vision_service_url}{endpoint}"
                ) as response:
                    # Should not be 404 (endpoint exists), but may be 400, 422 (bad params)
                    assert response.status != 404, f"Endpoint {endpoint} not found"
                    print(f"   ✅ Endpoint exists: {endpoint}")

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_session_management(self):
        """Test 2: Verify session creation and management functionality."""
        test_name = "Session Management"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            # Create a test session
            media_uuid = str(uuid.uuid4())
            camera_uuid = str(uuid.uuid4())

            session_request = {
                "media_uuid": media_uuid,
                "camera_device_uuid": camera_uuid,
                "session_type": "streaming",
                "metadata": {
                    "test_phase": "phase4",
                    "test_purpose": "integration_testing",
                },
            }

            async with self.test_session.post(
                f"{self.vision_service_url}/sessions/start", json=session_request
            ) as response:
                assert (
                    response.status == 200
                ), f"Session creation failed: {response.status}"
                session_data = await response.json()

                assert "session" in session_data, "Session data missing"
                session_uuid = session_data["session"]["session_uuid"]
                print(f"   ✅ Session created: {session_uuid}")

            # Verify session status
            async with self.test_session.get(
                f"{self.vision_service_url}/sessions/{session_uuid}/status"
            ) as response:
                assert (
                    response.status == 200
                ), f"Session status check failed: {response.status}"
                status_data = await response.json()

                assert status_data["session"]["processing_status"] == "active"
                print(
                    f"   ✅ Session active: {status_data['session']['processing_status']}"
                )

            # Store session UUID for later tests
            self.test_session_uuid = session_uuid
            self.test_media_uuid = media_uuid

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_enhanced_face_storage(self):
        """Test 3: Test enhanced face storage with session context."""
        test_name = "Enhanced Face Storage"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            if not hasattr(self, "test_session_uuid"):
                raise Exception(
                    "No test session available (depends on session management test)"
                )

            # Store multiple face detections with session context
            face_detections = [
                {
                    "session_uuid": self.test_session_uuid,
                    "frame_number": 1,
                    "timestamp": 0.033,
                    "bbox": [100, 100, 200, 200],
                    "confidence": 0.95,
                    "method": "two_stage_enhanced",
                },
                {
                    "session_uuid": self.test_session_uuid,
                    "frame_number": 15,
                    "timestamp": 0.5,
                    "bbox": [300, 150, 400, 250],
                    "confidence": 0.87,
                    "method": "two_stage_enhanced",
                },
                {
                    "session_uuid": self.test_session_uuid,
                    "frame_number": 30,
                    "timestamp": 1.0,
                    "bbox": [150, 200, 250, 300],
                    "confidence": 0.92,
                    "method": "two_stage_enhanced",
                },
            ]

            stored_faces = []
            for face_data in face_detections:
                async with self.test_session.post(
                    f"{self.vision_service_url}/faces/store", json=face_data
                ) as response:
                    assert (
                        response.status == 200
                    ), f"Face storage failed: {response.status}"
                    stored_face = await response.json()

                    assert "face_id" in stored_face, "Face ID missing from response"
                    assert stored_face["session_uuid"] == self.test_session_uuid
                    stored_faces.append(stored_face)

                    print(
                        f"   ✅ Face stored: {stored_face['face_id']} (frame {face_data['frame_number']})"
                    )

            # Verify session face count was updated
            async with self.test_session.get(
                f"{self.vision_service_url}/sessions/{self.test_session_uuid}/status"
            ) as response:
                assert response.status == 200
                status_data = await response.json()

                face_count = status_data["session"]["total_faces_detected"]
                assert face_count == len(
                    face_detections
                ), f"Expected {len(face_detections)} faces, got {face_count}"
                print(f"   ✅ Session face count updated: {face_count}")

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_processing_status_management(self):
        """Test 4: Test media processing status tracking."""
        test_name = "Processing Status Management"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            if not hasattr(self, "test_media_uuid"):
                raise Exception("No test media UUID available")

            # Check initial processing status (should be unprocessed)
            async with self.test_session.get(
                f"{self.vision_service_url}/processing-status/{self.test_media_uuid}"
            ) as response:
                assert response.status == 200
                status_data = await response.json()

                # Initially should be unprocessed or in progress
                print(f"   ✅ Initial status: {status_data.get('status')}")

            # Mark media as fully processed
            complete_request = {
                "session_uuid": self.test_session_uuid,
                "total_frames": 100,
                "total_faces": 3,
                "method": "two_stage_enhanced",
            }

            async with self.test_session.post(
                f"{self.vision_service_url}/processing-status/{self.test_media_uuid}/complete",
                json=complete_request,
            ) as response:
                assert response.status == 200
                completion_data = await response.json()

                assert completion_data["status"] == "marked_as_processed"
                print(
                    f"   ✅ Media marked as processed: {completion_data['media_uuid']}"
                )

            # Verify processing status was updated
            async with self.test_session.get(
                f"{self.vision_service_url}/processing-status/{self.test_media_uuid}"
            ) as response:
                assert response.status == 200
                status_data = await response.json()

                assert status_data["face_detection_processed"] == True
                assert status_data["total_faces_detected"] == 3
                assert (
                    status_data["face_detection_session_uuid"] == self.test_session_uuid
                )
                print(
                    f"   ✅ Status verified: processed={status_data['face_detection_processed']}"
                )

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_frame_indexed_retrieval(self):
        """Test 5: Test frame-indexed face data retrieval."""
        test_name = "Frame-Indexed Face Retrieval"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            if not hasattr(self, "test_media_uuid"):
                raise Exception("No test media UUID available")

            # Test 1: Retrieve all face data for media
            async with self.test_session.get(
                f"{self.vision_service_url}/faces/media/{self.test_media_uuid}/frames"
            ) as response:
                assert response.status == 200
                face_data = await response.json()

                assert "face_data" in face_data
                assert "total_frames" in face_data
                assert len(face_data["face_data"]) > 0, "No face data retrieved"
                print(
                    f"   ✅ All frames retrieved: {len(face_data['face_data'])} frames"
                )

            # Test 2: Frame range filtering
            async with self.test_session.get(
                f"{self.vision_service_url}/faces/media/{self.test_media_uuid}/frames?frame_start=10&frame_end=20"
            ) as response:
                assert response.status == 200
                range_data = await response.json()

                # Should only return frames in range 10-20
                for frame_num_str in range_data["face_data"].keys():
                    frame_num = int(frame_num_str)
                    assert (
                        10 <= frame_num <= 20
                    ), f"Frame {frame_num} outside requested range"
                print(
                    f"   ✅ Frame range filtering: {len(range_data['face_data'])} frames"
                )

            # Test 3: Confidence threshold filtering
            async with self.test_session.get(
                f"{self.vision_service_url}/faces/media/{self.test_media_uuid}/frames?confidence_threshold=0.9"
            ) as response:
                assert response.status == 200
                conf_data = await response.json()

                # Check that all returned faces meet confidence threshold
                for frame_faces in conf_data["face_data"].values():
                    for face in frame_faces:
                        assert (
                            face["confidence"] >= 0.9
                        ), f"Face confidence {face['confidence']} below threshold"
                print(
                    f"   ✅ Confidence filtering: {len(conf_data['face_data'])} frames"
                )

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_session_analytics(self):
        """Test 6: Test session analytics functionality."""
        test_name = "Session Analytics"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            if not hasattr(self, "test_session_uuid"):
                raise Exception("No test session UUID available")

            # Get session analytics
            async with self.test_session.get(
                f"{self.vision_service_url}/faces/session/{self.test_session_uuid}/analytics"
            ) as response:
                assert response.status == 200
                analytics_data = await response.json()

                # Verify analytics data structure
                required_fields = [
                    "session_uuid",
                    "media_uuid",
                    "total_faces",
                    "avg_confidence",
                    "faces_per_frame",
                    "detection_methods",
                ]

                for field in required_fields:
                    assert field in analytics_data, f"Missing analytics field: {field}"

                assert analytics_data["session_uuid"] == self.test_session_uuid
                assert analytics_data["total_faces"] > 0
                assert 0.0 <= analytics_data["avg_confidence"] <= 1.0

                print(f"   ✅ Session analytics retrieved:")
                print(f"      - Total faces: {analytics_data['total_faces']}")
                print(f"      - Avg confidence: {analytics_data['avg_confidence']:.3f}")
                print(
                    f"      - Frames with faces: {len(analytics_data['faces_per_frame'])}"
                )
                print(
                    f"      - Detection methods: {list(analytics_data['detection_methods'].keys())}"
                )

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_cross_service_integration(self):
        """Test 7: Test integration between Vision and Media services."""
        test_name = "Cross-Service Integration"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            # This would test calling Media service endpoints that interact with Vision service
            # For now, we'll test that the Vision service can handle requests that would
            # come from the Media service during streaming

            # Test session creation as would be called by Media service
            integration_media_uuid = str(uuid.uuid4())
            integration_camera_uuid = str(uuid.uuid4())

            session_request = {
                "media_uuid": integration_media_uuid,
                "camera_device_uuid": integration_camera_uuid,
                "session_type": "streaming",
                "metadata": {"source": "media_service", "streaming_type": "websocket"},
            }

            async with self.test_session.post(
                f"{self.vision_service_url}/sessions/start", json=session_request
            ) as response:
                assert response.status == 200
                session_data = await response.json()
                integration_session_uuid = session_data["session"]["session_uuid"]
                print(
                    f"   ✅ Cross-service session created: {integration_session_uuid}"
                )

            # Test rapid face storage (simulating streaming)
            faces_to_store = 10
            start_time = time.time()

            for i in range(faces_to_store):
                face_data = {
                    "session_uuid": integration_session_uuid,
                    "frame_number": i + 1,
                    "timestamp": (i + 1) * 0.033,  # 30 FPS
                    "bbox": [100 + i * 10, 100, 200 + i * 10, 200],
                    "confidence": 0.8 + (i % 3) * 0.05,
                    "method": "streaming_detector",
                }

                async with self.test_session.post(
                    f"{self.vision_service_url}/faces/store", json=face_data
                ) as response:
                    assert response.status == 200

            storage_time = time.time() - start_time
            storage_rate = faces_to_store / storage_time

            print(
                f"   ✅ Streaming simulation: {faces_to_store} faces in {storage_time:.3f}s"
            )
            print(f"      Storage rate: {storage_rate:.1f} faces/second")

            # Performance check - should handle at least 10 faces/second for real-time streaming
            assert (
                storage_rate > 10
            ), f"Storage rate too slow: {storage_rate:.1f} faces/second"

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _test_error_handling(self):
        """Test 8: Test error handling and edge cases."""
        test_name = "Error Handling"
        print(f"\n🔍 {test_name}")

        try:
            self.test_results["tests_run"] += 1

            # Test 1: Invalid session UUID format
            async with self.test_session.post(
                f"{self.vision_service_url}/faces/store",
                json={
                    "session_uuid": "invalid-uuid",
                    "bbox": [100, 100, 200, 200],
                    "confidence": 0.95,
                    "method": "test",
                },
            ) as response:
                assert response.status == 400, "Should reject invalid UUID format"
                print("   ✅ Invalid UUID format rejected")

            # Test 2: Non-existent session
            fake_session_uuid = str(uuid.uuid4())
            async with self.test_session.post(
                f"{self.vision_service_url}/faces/store",
                json={
                    "session_uuid": fake_session_uuid,
                    "bbox": [100, 100, 200, 200],
                    "confidence": 0.95,
                    "method": "test",
                },
            ) as response:
                assert response.status == 404, "Should reject non-existent session"
                print("   ✅ Non-existent session rejected")

            # Test 3: Invalid bounding box
            async with self.test_session.post(
                f"{self.vision_service_url}/faces/store",
                json={
                    "session_uuid": self.test_session_uuid,
                    "bbox": [200, 200, 100, 100],  # Invalid: x2 < x1, y2 < y1
                    "confidence": 0.95,
                    "method": "test",
                },
            ) as response:
                assert response.status == 400, "Should reject invalid bounding box"
                print("   ✅ Invalid bounding box rejected")

            # Test 4: Invalid confidence value
            async with self.test_session.post(
                f"{self.vision_service_url}/faces/store",
                json={
                    "session_uuid": self.test_session_uuid,
                    "bbox": [100, 100, 200, 200],
                    "confidence": 1.5,  # Invalid: > 1.0
                    "method": "test",
                },
            ) as response:
                assert response.status == 400, "Should reject invalid confidence"
                print("   ✅ Invalid confidence rejected")

            # Test 5: Invalid media UUID format for processing status
            async with self.test_session.get(
                f"{self.vision_service_url}/processing-status/invalid-uuid"
            ) as response:
                assert response.status == 400, "Should reject invalid media UUID"
                print("   ✅ Invalid media UUID rejected")

            await self._record_success(test_name)

        except Exception as e:
            await self._record_failure(test_name, str(e))

    async def _record_success(self, test_name: str):
        """Record a successful test."""
        self.test_results["tests_passed"] += 1
        print(f"   ✅ {test_name} PASSED")

    async def _record_failure(self, test_name: str, error_message: str):
        """Record a failed test."""
        self.test_results["tests_failed"] += 1
        self.test_results["failures"].append(
            {
                "test": test_name,
                "error": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        print(f"   ❌ {test_name} FAILED: {error_message}")

    async def _print_test_summary(self):
        """Print comprehensive test results summary."""
        duration = None
        if self.test_results["start_time"] and self.test_results["end_time"]:
            duration = (
                self.test_results["end_time"] - self.test_results["start_time"]
            ).total_seconds()

        print("\n" + "=" * 60)
        print("🎯 PHASE 4 VISION SERVICE ENHANCEMENT - TEST RESULTS")
        print("=" * 60)

        print(f"📊 Tests Run: {self.test_results['tests_run']}")
        print(f"✅ Tests Passed: {self.test_results['tests_passed']}")
        print(f"❌ Tests Failed: {self.test_results['tests_failed']}")

        if duration:
            print(f"⏱️  Duration: {duration:.2f} seconds")

        success_rate = (
            (self.test_results["tests_passed"] / self.test_results["tests_run"] * 100)
            if self.test_results["tests_run"] > 0
            else 0
        )
        print(f"📈 Success Rate: {success_rate:.1f}%")

        if self.test_results["failures"]:
            print(f"\n❌ Failed Tests:")
            for failure in self.test_results["failures"]:
                print(f"   • {failure['test']}: {failure['error']}")

        print(
            f"\n🎯 PHASE 4 STATUS: {'✅ PASSED' if self.test_results['tests_failed'] == 0 else '❌ FAILED'}"
        )

        if self.test_results["tests_failed"] == 0:
            print("\n🚀 Phase 4 Vision Service Enhancement is fully operational!")
            print("   • Enhanced face storage with session context ✅")
            print("   • Processing status management ✅")
            print("   • Frame-indexed face retrieval ✅")
            print("   • Session analytics ✅")
            print("   • Cross-service integration ✅")
            print("   • Error handling and validation ✅")


async def main():
    """Main test execution function."""
    print("🧪 PPL Meta Platform - Phase 4 Vision Enhancement Integration Tests")
    print("Testing Vision Service Enhancement & Storage Optimization")
    print(f"⏰ Test started at: {datetime.now(timezone.utc).isoformat()}")

    tester = Phase4VisionIntegrationTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
