#!/usr/bin/env python3
"""
Test script for Phase 3: Backend Streaming Implementation

Tests the streaming endpoints:
- POST /api/v1/streaming/{device_id}/start
- GET /api/v1/streaming/{device_id}/video
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


async def start_stream(device_id: str, token: str) -> dict:
    """Start streaming from a camera."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"http://localhost:8005/api/v1/streaming/{device_id}/start",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            stream_url = data.get("stream_url")
            print_success(f"Stream started - URL: {stream_url}")
            return data
        except httpx.HTTPStatusError as e:
            print_error(f"Start stream failed: {e.response.status_code} - {e.response.text}")
            return {}
        except Exception as e:
            print_error(f"Start stream failed: {e}")
            return {}


async def test_stream_frames(device_id: str, token: str, duration: int = 5) -> dict:
    """Test streaming by reading frames for a specified duration."""
    frame_count = 0
    start_time = time.time()
    last_frame_time = start_time
    frame_times = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            url = f"http://localhost:8005/api/v1/streaming/{device_id}/video"
            print_info(f"Connecting to stream: {url}")
            
            async with client.stream(
                "GET",
                url,
                headers={"Authorization": f"Bearer {token}"},
                params={"quality": "medium"}
            ) as response:
                response.raise_for_status()
                
                print_success("Stream connected, reading frames...")
                
                buffer = b""
                async for chunk in response.aiter_bytes():
                    buffer += chunk
                    
                    # Look for JPEG frame boundaries
                    while b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
                        # Find JPEG start and end
                        start = buffer.find(b'\xff\xd8')
                        end = buffer.find(b'\xff\xd9', start) + 2
                        
                        if end > start:
                            # Extract frame
                            frame_data = buffer[start:end]
                            frame_count += 1
                            
                            # Calculate frame time
                            current_time = time.time()
                            frame_times.append(current_time - last_frame_time)
                            last_frame_time = current_time
                            
                            # Log every 10 frames
                            if frame_count % 10 == 0:
                                elapsed = current_time - start_time
                                fps = frame_count / elapsed if elapsed > 0 else 0
                                print_info(f"Frames received: {frame_count} ({fps:.1f} fps)")
                            
                            # Remove processed frame from buffer
                            buffer = buffer[end:]
                        else:
                            break
                    
                    # Check if duration reached
                    if time.time() - start_time >= duration:
                        print_info(f"Duration reached ({duration}s), stopping stream test")
                        break
                        
        except httpx.HTTPStatusError as e:
            print_error(f"Stream HTTP error: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print_error(f"Stream test failed: {e}")
            return {"success": False, "error": str(e)}
    
    elapsed = time.time() - start_time
    avg_fps = frame_count / elapsed if elapsed > 0 else 0
    avg_frame_time = sum(frame_times) / len(frame_times) if frame_times else 0
    
    return {
        "success": True,
        "frame_count": frame_count,
        "duration": elapsed,
        "avg_fps": avg_fps,
        "avg_frame_time": avg_frame_time * 1000,  # Convert to ms
    }


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


async def test_streaming_workflow():
    """Test complete streaming workflow."""
    print_header("Phase 3: Backend Streaming Implementation - Test")
    
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
    
    # Step 4: Start stream
    print_header("Step 4: Start Stream")
    stream_data = await start_stream(device_id, token)
    
    if not stream_data:
        print_error("Failed to start stream")
        return False
    
    # Step 5: Test streaming by reading frames
    print_header("Step 5: Test Streaming (5 seconds)")
    stream_stats = await test_stream_frames(device_id, token, duration=5)
    
    if not stream_stats.get("success"):
        print_error(f"Streaming test failed: {stream_stats.get('error')}")
    else:
        print_success(f"Streaming test completed!")
        print_info(f"Frames received: {stream_stats['frame_count']}")
        print_info(f"Duration: {stream_stats['duration']:.1f}s")
        print_info(f"Average FPS: {stream_stats['avg_fps']:.1f}")
        print_info(f"Average frame time: {stream_stats['avg_frame_time']:.1f}ms")
    
    # Step 6: Disconnect camera
    print_header("Step 6: Disconnect Camera")
    disconnect_success = await disconnect_camera(device_id, token)
    
    if not disconnect_success:
        print_warning("Failed to disconnect camera, but test can continue")
    
    # Summary
    print_header("Test Summary")
    
    if stream_stats.get("success"):
        print_success(f"✨ Streaming workflow test completed!")
        print_info(f"Camera: {device_id}")
        print_info(f"Frames streamed: {stream_stats['frame_count']}")
        print_info(f"Average FPS: {stream_stats['avg_fps']:.1f}")
        print_info(f"Stream quality: medium (640x480)")
        print_info(f"Camera disconnected: {'Yes' if disconnect_success else 'No'}")
        
        # Validate FPS
        if stream_stats['avg_fps'] >= 20:
            print_success("✅ FPS is good (≥20 fps)")
        elif stream_stats['avg_fps'] >= 10:
            print_warning("⚠️ FPS is acceptable but low (10-20 fps)")
        else:
            print_error("❌ FPS is too low (<10 fps)")
        
        return True
    else:
        print_error("Streaming test failed")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_streaming_workflow())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
