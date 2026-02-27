#!/usr/bin/env python3
"""
Test concurrent camera connections to verify no blocking.
"""

import asyncio
import httpx
import time
from datetime import datetime

BASE_URL = "http://localhost:8005"

async def connect_camera(device_id: str, camera_name: str):
    """Connect a camera and time it"""
    print(f"🔌 [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Starting connection: {camera_name} ({device_id})")
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/v1/cameras/{device_id}/connect")
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"✅ [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Connected: {camera_name} in {elapsed:.2f}s")
                return True, elapsed
            else:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Failed: {camera_name} - {response.status_code}")
                return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Exception: {camera_name} - {e}")
        return False, elapsed

async def test_concurrent_connections():
    """Test connecting multiple cameras simultaneously"""
    print("\n" + "="*70)
    print("TEST: Concurrent Camera Connections")
    print("="*70)
    
    # Get available cameras
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/cameras/")
        cameras = response.json()
    
    if len(cameras) < 2:
        print("❌ Need at least 2 cameras for concurrent test")
        return
    
    # Find USB and RTSP cameras
    usb_camera = next((c for c in cameras if c['camera_type'] == 'USB'), None)
    rtsp_camera = next((c for c in cameras if c['camera_type'] == 'RTSP'), None)
    
    if not usb_camera or not rtsp_camera:
        print("❌ Need both USB and RTSP camera")
        print(f"   USB: {usb_camera['device_id'] if usb_camera else 'NOT FOUND'}")
        print(f"   RTSP: {rtsp_camera['device_id'] if rtsp_camera else 'NOT FOUND'}")
        return
    
    usb_id = usb_camera['device_id']
    rtsp_id = rtsp_camera['device_id']
    
    print(f"\n📹 Testing cameras:")
    print(f"   USB:  {usb_id}")
    print(f"   RTSP: {rtsp_id}")
    
    # Disconnect both first
    print(f"\n🔌 Disconnecting both cameras...")
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/api/v1/cameras/{usb_id}/disconnect")
        await client.post(f"{BASE_URL}/api/v1/cameras/{rtsp_id}/disconnect")
    await asyncio.sleep(1)
    
    # Test 1: Connect USB first, then RTSP immediately
    print(f"\n📝 Test 1: Connect USB, then RTSP (0.5s delay)")
    print("-" * 70)
    
    start_time = time.time()
    
    # Start USB connection
    usb_task = asyncio.create_task(connect_camera(usb_id, "USB"))
    
    # Wait 0.5 seconds then start RTSP
    await asyncio.sleep(0.5)
    rtsp_task = asyncio.create_task(connect_camera(rtsp_id, "RTSP"))
    
    # Wait for both
    usb_result, rtsp_result = await asyncio.gather(usb_task, rtsp_task)
    
    total_time = time.time() - start_time
    
    print(f"\n📊 Test 1 Results:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   USB:  {'✅' if usb_result[0] else '❌'} ({usb_result[1]:.2f}s)")
    print(f"   RTSP: {'✅' if rtsp_result[0] else '❌'} ({rtsp_result[1]:.2f}s)")
    
    if total_time < 8:
        print("   ✅ PASS: Connections were concurrent (total < 8s)")
    else:
        print("   ❌ FAIL: Connections were serialized (total >= 8s)")
    
    # Disconnect both
    await asyncio.sleep(2)
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/api/v1/cameras/{usb_id}/disconnect")
        await client.post(f"{BASE_URL}/api/v1/cameras/{rtsp_id}/disconnect")
    await asyncio.sleep(1)
    
    # Test 2: Connect both simultaneously
    print(f"\n📝 Test 2: Connect both simultaneously")
    print("-" * 70)
    
    start_time = time.time()
    
    # Start both at the same time
    usb_task = asyncio.create_task(connect_camera(usb_id, "USB"))
    rtsp_task = asyncio.create_task(connect_camera(rtsp_id, "RTSP"))
    
    # Wait for both
    usb_result, rtsp_result = await asyncio.gather(usb_task, rtsp_task)
    
    total_time = time.time() - start_time
    
    print(f"\n📊 Test 2 Results:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   USB:  {'✅' if usb_result[0] else '❌'} ({usb_result[1]:.2f}s)")
    print(f"   RTSP: {'✅' if rtsp_result[0] else '❌'} ({rtsp_result[1]:.2f}s)")
    
    if total_time < 8:
        print("   ✅ PASS: Connections were concurrent (total < 8s)")
    else:
        print("   ❌ FAIL: Connections were serialized (total >= 8s)")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_concurrent_connections())
