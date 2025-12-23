#!/usr/bin/env python3
"""
Test script for Phase 2: Backend Recording Implementation

Tests the recording endpoints:
- POST /api/v1/cameras/{device_id}/recording/start
- POST /api/v1/cameras/{device_id}/recording/stop
- GET /api/v1/cameras/{device_id}/recording/status
- GET /api/v1/recordings/active
"""

import asyncio
import httpx
import sys
import time
from pathlib import Path


class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


async def get_auth_token() -> str:
    """Get authentication token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/v1/users/login",
                data={
                    "username": "fresh.user@example.com",
                    "password": "NewPassword234!"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token = response.json()["access_token"]
            print_success("Authenticated successfully")
            return token
        except Exception as e:
            print_error(f"Authentication failed: {e}")
            print_warning("Make sure node service is running on port 8001")
            sys.exit(1)


async def detect_cameras(token: str) -> list:
    """Detect available cameras."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "http://localhost:8005/api/v1/cameras/detect",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            cameras = response.json().get("cameras", [])
            print_success(f"Detected {len(cameras)} cameras")
            return cameras
        except Exception as e:
            print_error(f"Detection failed: {e}")
            return []


async def connect_camera(device_id: str, token: str) -> bool:
    """Connect to a camera."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"http://localhost:8005/api/v1/cameras/{device_id}/connect",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "unknown")
            print_success(f"Camera {device_id} connection initiated (status: {status})")
            
            # If RTSP, wait for connection
            if status == "connecting":
                print_info("Waiting for RTSP camera to connect...")
                await asyncio.sleep(5)
            
            return True
        except Exception as e:
            print_error(f"Connection failed: {e}")
            return False


async def disconnect_camera(device_id: str, token: str) -> bool:
    """Disconnect from a camera."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"http://localhost:8005/api/v1/cameras/{device_id}/disconnect",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            print_success(f"Camera {device_id} disconnected successfully")
            return True
        except Exception as e:
            print_error(f"Disconnect failed: {e}")
            return False


async def start_recording(device_id: str, token: str) -> dict:
    """Start recording on a camera."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"http://localhost:8005/api/v1/cameras/{device_id}/recording/start",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            session_id = data.get("session_id")
            print_success(f"Recording started - Session: {session_id}")
            return data
        except httpx.HTTPStatusError as e:
            print_error(f"Start recording failed: {e.response.status_code} - {e.response.text}")
            return {}
        except Exception as e:
            print_error(f"Start recording failed: {e}")
            return {}


async def get_recording_status(device_id: str, token: str) -> dict:
    """Get recording status for a camera."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"http://localhost:8005/api/v1/cameras/{device_id}/recording/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print_error(f"Status check failed: {e}")
            return {}


async def stop_recording(device_id: str, token: str) -> dict:
    """Stop recording on a camera."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"http://localhost:8005/api/v1/cameras/{device_id}/recording/stop",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            duration = data.get("duration", 0)
            frame_count = data.get("frame_count", 0)
            file_path = data.get("file_path", "unknown")
            print_success(f"Recording stopped - Duration: {duration:.1f}s, Frames: {frame_count}")
            print_info(f"File: {file_path}")
            return data
        except Exception as e:
            print_error(f"Stop recording failed: {e}")
            return {}


async def list_active_recordings(token: str) -> dict:
    """List all active recordings."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "http://localhost:8005/api/v1/cameras/recordings/active",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print_error(f"List active recordings failed: {e}")
            return {}


async def check_video_file(file_path: str) -> bool:
    """Check if video file exists and has content."""
    path = Path(file_path)
    if not path.exists():
        print_error(f"Video file not found: {file_path}")
        return False
    
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb < 0.1:
        print_warning(f"Video file is very small: {size_mb:.2f} MB")
    else:
        print_success(f"Video file created: {size_mb:.2f} MB")
    
    return True


async def test_recording_workflow():
    """Test complete recording workflow."""
    print_header("Phase 2: Backend Recording Implementation - Test")
    
    # Step 1: Authentication
    print_header("Step 1: Authentication")
    token = await get_auth_token()
    
    # Step 2: Detect cameras
    print_header("Step 2: Detect Cameras")
    cameras = await detect_cameras(token)
    
    if not cameras:
        print_error("No cameras detected. Make sure at least one camera is available.")
        return False
    
    # Use first camera
    camera = cameras[0]
    device_id = camera['device_id']
    print_info(f"Using camera: {device_id}")
    
    # Step 3: Connect to camera (if not already connected)
    print_header("Step 3: Connect to Camera")
    status = camera.get('status', 'unknown')
    if status != 'connected':
        await connect_camera(device_id, token)
        await asyncio.sleep(2)  # Wait for connection
    else:
        print_success(f"Camera {device_id} already connected")
    
    # Step 4: Start recording
    print_header("Step 4: Start Recording")
    recording_data = await start_recording(device_id, token)
    
    if not recording_data:
        print_error("Failed to start recording")
        return False
    
    session_id = recording_data.get('session_id')
    
    # Step 5: Check status while recording
    print_header("Step 5: Monitor Recording Status")
    
    for i in range(3):
        await asyncio.sleep(3)
        status = await get_recording_status(device_id, token)
        
        if status.get('is_recording'):
            duration = status.get('duration', 0)
            frame_count = status.get('frame_count', 0)
            print_info(f"Recording... Duration: {duration:.1f}s, Frames: {frame_count}")
        else:
            print_warning("Recording stopped unexpectedly")
            break
    
    # Step 6: List active recordings
    print_header("Step 6: List Active Recordings")
    active = await list_active_recordings(token)
    active_count = active.get('active_count', 0)
    print_info(f"Active recordings: {active_count}")
    
    for session in active.get('sessions', []):
        print_info(f"  - Session {session['session_id']}: {session['device_id']} ({session['duration']:.1f}s, {session['frame_count']} frames)")
    
    # Step 7: Stop recording
    print_header("Step 7: Stop Recording")
    stop_data = await stop_recording(device_id, token)
    
    if not stop_data:
        print_error("Failed to stop recording")
        return False
    
    # Step 8: Verify video file
    print_header("Step 8: Verify Video File")
    file_path = stop_data.get('file_path')
    
    if file_path:
        # Make path relative to cameras directory
        full_path = Path(__file__).parent.parent / file_path
        await check_video_file(str(full_path))
    else:
        print_warning("No file path returned")
    
    # Step 9: Verify recording stopped
    print_header("Step 9: Verify Recording Stopped")
    final_status = await get_recording_status(device_id, token)
    
    if not final_status.get('is_recording'):
        print_success("Recording confirmed stopped")
    else:
        print_warning("Recording still appears active")
    
    # Step 10: Disconnect camera
    print_header("Step 10: Disconnect Camera")
    disconnect_success = await disconnect_camera(device_id, token)
    
    if not disconnect_success:
        print_warning("Failed to disconnect camera, but test can continue")
    
    # Summary
    print_header("Test Summary")
    print_success(f"✨ Recording workflow test completed!")
    print_info(f"Session ID: {session_id}")
    print_info(f"Duration: {stop_data.get('duration', 0):.1f}s")
    print_info(f"Frames: {stop_data.get('frame_count', 0)}")
    print_info(f"File: {file_path}")
    print_info(f"Camera disconnected: {'Yes' if disconnect_success else 'No'}")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_recording_workflow())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
