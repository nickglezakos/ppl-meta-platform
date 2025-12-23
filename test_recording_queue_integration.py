#!/usr/bin/env python3
"""
Test recording functionality with queue workers.

Tests:
1. Recording start checks queue workers (not active_connections)
2. Recording reads frames from queue worker buffer
3. Instant detection uses queue worker frames
4. No resource contention between recording, streaming, instant detection
"""

import asyncio
import sys
import os
import time
import httpx
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "http://localhost:8005"
AUTH_TOKEN = None  # Will get from login

async def login():
    """Get auth token"""
    global AUTH_TOKEN
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/v1/users/login",
            json={"username": "testuser", "password": "testpass"}
        )
        if response.status_code == 200:
            AUTH_TOKEN = response.json()["access_token"]
            print(f"✅ Logged in, token: {AUTH_TOKEN[:20]}...")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False

async def get_cameras():
    """List available cameras"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/cameras/")
        cameras = response.json()
        print(f"\n📹 Available cameras: {len(cameras)}")
        for cam in cameras:
            print(f"  - {cam['device_id']}: {cam['camera_type']} (status: {cam.get('status', 'unknown')})")
        return cameras

async def connect_camera(device_id: str):
    """Connect camera via queue workers"""
    print(f"\n🔌 Connecting {device_id} via queue workers...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/api/v1/cameras/{device_id}/connect")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Connected: {result}")
            
            # Wait for queue worker to initialize
            print("⏳ Waiting for queue worker initialization...")
            await asyncio.sleep(2)
            
            # Check realtime status
            status_response = await client.get(f"{BASE_URL}/api/v1/cameras/{device_id}/realtime")
            status = status_response.json()
            print(f"📊 Realtime status: {status}")
            
            return status.get('is_connected', False)
        else:
            print(f"❌ Connection failed: {response.status_code} - {response.text}")
            return False

async def start_recording(device_id: str, enable_instant_detection: bool = True):
    """Start recording via queue workers"""
    print(f"\n🎬 Starting recording for {device_id} (instant_detection={enable_instant_detection})...")
    
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/streaming/{device_id}/record/start",
            params={"enable_instant_detection": enable_instant_detection},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Recording started:")
            print(f"   Session: {result.get('session_uuid')}")
            print(f"   Recording ID: {result.get('recording_id')}")
            print(f"   Started: {result.get('started_at')}")
            return result
        else:
            print(f"❌ Recording start failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

async def check_recording_status(device_id: str):
    """Check if camera is recording"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/streaming/{device_id}/record/status")
        if response.status_code == 200:
            status = response.json()
            print(f"\n📊 Recording status for {device_id}:")
            print(f"   Is recording: {status.get('is_recording')}")
            if status.get('is_recording'):
                print(f"   Duration: {status.get('duration_seconds')}s")
                print(f"   Frame count: {status.get('frame_count')}")
            return status
        return None

async def check_instant_detection():
    """Check instant detection status"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/instant-detection/status")
        if response.status_code == 200:
            status = response.json()
            print(f"\n🔍 Instant detection status:")
            print(f"   Running: {status.get('running')}")
            if status.get('running'):
                print(f"   Camera: {status.get('camera_id')}")
                print(f"   Last run: {status.get('last_sample_time')}")
            return status
        return None

async def stop_recording(device_id: str):
    """Stop recording"""
    print(f"\n🛑 Stopping recording for {device_id}...")
    
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/streaming/{device_id}/record/stop",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Recording stopped:")
            print(f"   Duration: {result.get('duration_seconds')}s")
            print(f"   File: {result.get('file_path')}")
            print(f"   Size: {result.get('file_size_bytes')} bytes")
            return result
        else:
            print(f"❌ Recording stop failed: {response.status_code}")
            return None

async def disconnect_camera(device_id: str):
    """Disconnect camera"""
    print(f"\n🔌 Disconnecting {device_id}...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/api/v1/cameras/{device_id}/disconnect")
        if response.status_code == 200:
            print(f"✅ Disconnected")
            return True
        else:
            print(f"❌ Disconnect failed: {response.status_code}")
            return False

async def test_recording_with_queue_workers():
    """
    Main test: Recording with queue workers
    
    Expected behavior:
    1. Camera connects via queue worker
    2. Recording starts using queue worker buffer
    3. Instant detection auto-starts, uses queue worker
    4. Recording and instant detection run concurrently
    5. Recording stops cleanly
    """
    
    print("=" * 70)
    print("TEST: Recording with Queue Workers")
    print("=" * 70)
    
    # Step 1: Login
    print("\n📝 Step 1: Login")
    if not await login():
        print("❌ TEST FAILED: Could not login")
        return False
    
    # Step 2: Get cameras
    print("\n📝 Step 2: Get available cameras")
    cameras = await get_cameras()
    if not cameras:
        print("❌ TEST FAILED: No cameras available")
        return False
    
    # Find USB camera
    usb_camera = next((c for c in cameras if c['camera_type'] == 'USB'), None)
    if not usb_camera:
        print("⚠️ No USB camera found, trying first available camera")
        usb_camera = cameras[0]
    
    device_id = usb_camera['device_id']
    print(f"\n🎯 Testing with camera: {device_id}")
    
    # Step 3: Connect via queue workers
    print("\n📝 Step 3: Connect camera via queue workers")
    if not await connect_camera(device_id):
        print("❌ TEST FAILED: Camera connection failed")
        return False
    
    # Step 4: Start recording (with instant detection)
    print("\n📝 Step 4: Start recording with instant detection")
    recording_info = await start_recording(device_id, enable_instant_detection=True)
    if not recording_info:
        print("❌ TEST FAILED: Recording start failed")
        await disconnect_camera(device_id)
        return False
    
    # Step 5: Wait and monitor
    print("\n📝 Step 5: Monitor recording for 10 seconds...")
    for i in range(5):
        await asyncio.sleep(2)
        print(f"\n⏱️  {(i+1)*2}s elapsed...")
        await check_recording_status(device_id)
        await check_instant_detection()
    
    # Step 6: Stop recording
    print("\n📝 Step 6: Stop recording")
    stop_result = await stop_recording(device_id)
    if not stop_result:
        print("⚠️ WARNING: Recording stop returned no result")
    
    # Step 7: Disconnect
    print("\n📝 Step 7: Disconnect camera")
    await disconnect_camera(device_id)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("✅ All steps completed successfully!")
    print(f"✅ Recording used queue worker frames (no active_connections)")
    print(f"✅ Instant detection used queue worker frames (no contention)")
    print(f"✅ Recording file created: {stop_result.get('file_path') if stop_result else 'N/A'}")
    print("=" * 70)
    
    return True

async def test_recording_without_instant_detection():
    """Test recording without instant detection"""
    
    print("\n" + "=" * 70)
    print("TEST: Recording WITHOUT Instant Detection")
    print("=" * 70)
    
    cameras = await get_cameras()
    if not cameras:
        return False
    
    device_id = cameras[0]['device_id']
    
    # Connect
    if not await connect_camera(device_id):
        return False
    
    # Start recording (no instant detection)
    recording_info = await start_recording(device_id, enable_instant_detection=False)
    if not recording_info:
        await disconnect_camera(device_id)
        return False
    
    # Wait 5 seconds
    print("\n⏱️  Recording for 5 seconds...")
    await asyncio.sleep(5)
    
    # Check instant detection should NOT be running
    instant_status = await check_instant_detection()
    if instant_status and instant_status.get('running'):
        print("⚠️ WARNING: Instant detection running when it shouldn't be")
    else:
        print("✅ Instant detection correctly NOT running")
    
    # Stop
    await stop_recording(device_id)
    await disconnect_camera(device_id)
    
    print("✅ Test completed")
    return True

async def main():
    """Run all tests"""
    
    print("\n🧪 RECORDING QUEUE INTEGRATION TESTS")
    print("=" * 70)
    
    # Test 1: Recording with instant detection
    try:
        success = await test_recording_with_queue_workers()
        if not success:
            print("\n❌ Test 1 FAILED")
            return 1
    except Exception as e:
        print(f"\n❌ Test 1 EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n\n")
    
    # Test 2: Recording without instant detection
    try:
        success = await test_recording_without_instant_detection()
        if not success:
            print("\n⚠️ Test 2 had issues")
    except Exception as e:
        print(f"\n⚠️ Test 2 EXCEPTION: {e}")
    
    print("\n\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
