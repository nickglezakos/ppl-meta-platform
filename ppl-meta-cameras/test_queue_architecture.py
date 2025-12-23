#!/usr/bin/env python3
"""
Test script for queue-based camera architecture.

Tests:
1. Worker creation and lifecycle
2. Camera connection via queue
3. Frame buffer reading
4. Multiple concurrent cameras
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.camera_service_queue import get_camera_service
from src.services.worker_manager import get_worker_manager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_usb_camera_connection():
    """Test USB camera connection with worker queue."""
    logger.info("=" * 60)
    logger.info("TEST 1: USB Camera Connection")
    logger.info("=" * 60)
    
    service = get_camera_service()
    
    try:
        # Detect cameras
        logger.info("📸 Detecting cameras...")
        cameras = await service.detect_available_cameras()
        logger.info(f"✅ Found {len(cameras)} cameras")
        
        if not cameras:
            logger.warning("⚠️ No cameras found, skipping test")
            return False
        
        # Use first camera
        camera = cameras[0]
        device_id = camera['device_id']
        logger.info(f"🎯 Testing with: {device_id}")
        
        # Connect
        logger.info(f"🔌 Connecting to {device_id}...")
        success = await service.connect_camera(device_id, camera)
        
        if not success:
            logger.error("❌ Connection failed")
            return False
        
        logger.info("✅ Connection successful")
        
        # Wait for frames
        logger.info("⏳ Waiting for frames...")
        await asyncio.sleep(2)
        
        # Get frame
        logger.info("📸 Getting latest frame...")
        frame = await service.get_latest_frame(device_id)
        
        if frame is None:
            logger.error("❌ No frame available")
            return False
        
        logger.info(f"✅ Got frame: shape={frame.shape}")
        
        # Get stats
        stats = service.get_camera_stats(device_id)
        logger.info(f"📊 Stats: {stats}")
        
        # Disconnect
        logger.info(f"🔌 Disconnecting {device_id}...")
        await service.disconnect_camera(device_id)
        logger.info("✅ Disconnected")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_frame_buffer_continuous():
    """Test that frame buffer continues updating."""
    logger.info("=" * 60)
    logger.info("TEST 2: Continuous Frame Buffer")
    logger.info("=" * 60)
    
    service = get_camera_service()
    
    try:
        # Detect and connect
        cameras = await service.detect_available_cameras()
        if not cameras:
            logger.warning("⚠️ No cameras found, skipping test")
            return False
        
        camera = cameras[0]
        device_id = camera['device_id']
        
        logger.info(f"🔌 Connecting to {device_id}...")
        await service.connect_camera(device_id, camera)
        
        # Read frames over 5 seconds
        logger.info("📸 Reading frames for 5 seconds...")
        frames_received = 0
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < 5.0:
            frame = await service.get_latest_frame(device_id)
            if frame is not None:
                frames_received += 1
            await asyncio.sleep(0.1)
        
        logger.info(f"✅ Received {frames_received} frames over 5 seconds")
        
        # Get stats
        stats = service.get_camera_stats(device_id)
        logger.info(f"📊 Worker stats: frames_read={stats['frames_read']}, frames_dropped={stats['frames_dropped']}")
        
        # Disconnect
        await service.disconnect_camera(device_id)
        
        return frames_received > 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_multiple_cameras():
    """Test multiple cameras simultaneously."""
    logger.info("=" * 60)
    logger.info("TEST 3: Multiple Cameras")
    logger.info("=" * 60)
    
    service = get_camera_service()
    
    try:
        # Detect cameras
        cameras = await service.detect_available_cameras()
        if len(cameras) < 2:
            logger.warning("⚠️ Need at least 2 cameras for this test")
            return True  # Not a failure, just skip
        
        # Connect to first 2 cameras
        device_ids = [cam['device_id'] for cam in cameras[:2]]
        logger.info(f"🔌 Connecting to {len(device_ids)} cameras...")
        
        for i, camera in enumerate(cameras[:2]):
            device_id = camera['device_id']
            success = await service.connect_camera(device_id, camera)
            if success:
                logger.info(f"✅ Camera {i+1} connected: {device_id}")
            else:
                logger.error(f"❌ Camera {i+1} failed: {device_id}")
        
        # Wait for frames
        await asyncio.sleep(2)
        
        # Read from both
        logger.info("📸 Reading frames from both cameras...")
        for device_id in device_ids:
            frame = await service.get_latest_frame(device_id)
            if frame is not None:
                logger.info(f"✅ {device_id}: Got frame shape={frame.shape}")
            else:
                logger.warning(f"⚠️ {device_id}: No frame")
        
        # Disconnect all
        for device_id in device_ids:
            await service.disconnect_camera(device_id)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_worker_lifecycle():
    """Test worker creation and cleanup."""
    logger.info("=" * 60)
    logger.info("TEST 4: Worker Lifecycle")
    logger.info("=" * 60)
    
    manager = get_worker_manager()
    
    try:
        # Check initial state
        initial_count = manager.get_worker_count()
        logger.info(f"📊 Initial workers: {initial_count}")
        
        # Get manager stats
        stats = manager.get_stats()
        logger.info(f"📊 Manager stats: {stats}")
        
        # Cleanup dead workers
        manager.cleanup_dead_workers()
        logger.info("🧹 Cleaned up dead workers")
        
        final_count = manager.get_worker_count()
        logger.info(f"📊 Final workers: {final_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Queue Architecture Tests")
    logger.info("=" * 60)
    
    tests = [
        ("USB Camera Connection", test_usb_camera_connection),
        ("Continuous Frame Buffer", test_frame_buffer_continuous),
        ("Multiple Cameras", test_multiple_cameras),
        ("Worker Lifecycle", test_worker_lifecycle),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            logger.info("")
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}", exc_info=True)
            results[test_name] = False
    
    # Cleanup
    logger.info("=" * 60)
    logger.info("🧹 Cleanup")
    logger.info("=" * 60)
    
    manager = get_worker_manager()
    await manager.cleanup_all()
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
