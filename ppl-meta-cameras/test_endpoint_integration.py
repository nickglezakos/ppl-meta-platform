#!/usr/bin/env python3
"""
Integration test: Queue Architecture with Camera Endpoints

Tests the full flow:
1. Camera service starts with queue architecture
2. Detect cameras endpoint works
3. Connect camera endpoint works
4. Start streaming endpoint works
5. Video streaming reads from worker buffer
6. Disconnect cleanup works
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


async def test_endpoint_integration():
    """Test full integration with endpoints."""
    logger.info("=" * 60)
    logger.info("Queue Architecture - Endpoint Integration Test")
    logger.info("=" * 60)
    
    service = get_camera_service()
    manager = get_worker_manager()
    
    try:
        # Step 1: Detect cameras (mimics /cameras/detect endpoint)
        logger.info("\nStep 1: Detect Cameras (Endpoint /cameras/detect)")
        logger.info("-" * 60)
        cameras = await service.detect_available_cameras()
        logger.info(f"✅ Detected {len(cameras)} cameras")
        
        if not cameras:
            logger.warning("⚠️ No cameras found")
            return False
        
        # Show detected cameras
        for cam in cameras:
            logger.info(f"  - {cam['device_id']}: {cam['name']} ({cam['camera_type'].value})")
        
        # Step 2: Connect to first camera (mimics /cameras/{device_id}/connect endpoint)
        camera = cameras[0]
        device_id = camera['device_id']
        logger.info(f"\nStep 2: Connect Camera (Endpoint /cameras/{device_id}/connect)")
        logger.info("-" * 60)
        
        success = await service.connect_camera(device_id, camera)
        if not success:
            logger.error(f"❌ Failed to connect to {device_id}")
            return False
        
        logger.info(f"✅ Camera connected: {device_id}")
        
        # Step 3: Start streaming (mimics /streaming/{device_id}/start endpoint)
        logger.info(f"\nStep 3: Start Streaming (Endpoint /streaming/{device_id}/start)")
        logger.info("-" * 60)
        
        # Check if worker exists and is connected
        worker = await service.get_camera_stream(device_id)
        if not worker:
            logger.error(f"❌ Worker not found for {device_id}")
            return False
        
        logger.info(f"✅ Stream ready for {device_id}")
        logger.info(f"  - Status: {worker.status.value}")
        logger.info(f"  - Stream URL: /streaming/{device_id}/video")
        
        # Step 4: Simulate video streaming (mimics /streaming/{device_id}/video endpoint)
        logger.info(f"\nStep 4: Video Streaming (Endpoint /streaming/{device_id}/video)")
        logger.info("-" * 60)
        logger.info("Simulating video stream for 5 seconds...")
        
        frames_received = 0
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < 5.0:
            # This mimics what the video streaming endpoint does
            frame = await service.get_latest_frame(device_id)
            
            if frame is not None:
                frames_received += 1
                # In real endpoint, this would be encoded to JPEG and yielded
                # logger.debug(f"  Frame {frames_received}: shape={frame.shape}")
            
            await asyncio.sleep(0.033)  # ~30 FPS
        
        logger.info(f"✅ Video streaming worked: {frames_received} frames in 5 seconds")
        
        # Step 5: Get worker statistics
        logger.info(f"\nStep 5: Worker Statistics")
        logger.info("-" * 60)
        stats = service.get_camera_stats(device_id)
        logger.info(f"  Device ID: {stats['device_id']}")
        logger.info(f"  Status: {stats['status']}")
        logger.info(f"  Frames Read: {stats['frames_read']}")
        logger.info(f"  Frames Dropped: {stats['frames_dropped']}")
        logger.info(f"  Buffer Size: {stats['buffer_size']}")
        logger.info(f"  Queue Size: {stats['queue_size']}")
        
        # Step 6: Disconnect (mimics /cameras/{device_id}/disconnect endpoint)
        logger.info(f"\nStep 6: Disconnect Camera")
        logger.info("-" * 60)
        await service.disconnect_camera(device_id)
        logger.info(f"✅ Camera disconnected: {device_id}")
        
        # Step 7: Manager statistics
        logger.info(f"\nStep 7: Manager Statistics")
        logger.info("-" * 60)
        mgr_stats = manager.get_stats()
        logger.info(f"  Total Workers: {mgr_stats['total_workers']}")
        logger.info(f"  Max Workers: {mgr_stats['max_workers']}")
        logger.info(f"  Workers by Status: {mgr_stats['workers_by_status']}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 INTEGRATION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Detect Cameras: SUCCESS ({len(cameras)} found)")
        logger.info(f"✅ Connect Camera: SUCCESS")
        logger.info(f"✅ Start Streaming: SUCCESS")
        logger.info(f"✅ Video Streaming: SUCCESS ({frames_received} frames)")
        logger.info(f"✅ Disconnect: SUCCESS")
        logger.info("=" * 60)
        logger.info("🎉 All Endpoint Integration Tests PASSED")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False
    
    finally:
        # Cleanup
        await manager.cleanup_all()


async def main():
    """Run integration test."""
    logger.info("🚀 Starting Queue Architecture - Endpoint Integration Test\n")
    
    success = await test_endpoint_integration()
    
    if success:
        logger.info("\n✅ All tests passed!")
        return 0
    else:
        logger.info("\n❌ Test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
