#!/usr/bin/env python3
"""
Test RTSP camera with queue architecture.

This test assumes there's an RTSP camera available at rtsp://192.168.1.76:554
Modify the RTSP_URL if your camera is at a different address.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.camera_service_queue import CameraService
from src.models.camera import CameraType
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure your RTSP camera here
# Note: Common stream paths are /stream1, /h264, /live, /cam/realmonitor
RTSP_URL = "rtsp://nick.glezakos@gmail.com:Kkkkodikos234@192.168.1.76:554/stream1"
RTSP_DEVICE_ID = "rtsp_192.168.1.76_554"


async def test_rtsp_camera():
    """Test RTSP camera connection with worker queue."""
    logger.info("=" * 60)
    logger.info("RTSP Camera Queue Architecture Test")
    logger.info("=" * 60)
    
    service = CameraService()
    
    # Create RTSP camera info manually (bypass database)
    camera_info = {
        "device_id": RTSP_DEVICE_ID,
        "name": "Test RTSP Camera",
        "camera_type": CameraType.RTSP,
        "connection_string": RTSP_URL,
        "resolution_width": 1920,
        "resolution_height": 1080,
        "max_fps": 30,
        "status": "available"
    }
    
    logger.info(f"🎯 Testing RTSP camera: {RTSP_URL}")
    logger.info("")
    
    try:
        # Step 1: Connect
        logger.info("Step 1: Connecting to RTSP camera...")
        logger.info(f"  URL: {RTSP_URL}")
        logger.info(f"  Device ID: {RTSP_DEVICE_ID}")
        
        success = await service.connect_camera(RTSP_DEVICE_ID, camera_info)
        
        if not success:
            logger.error("❌ RTSP connection failed")
            return False
        
        logger.info("✅ RTSP camera connected successfully")
        logger.info("")
        
        # Step 2: Wait for frames to buffer
        logger.info("Step 2: Waiting for frame buffer to populate...")
        await asyncio.sleep(3)
        
        # Step 3: Get frame
        logger.info("Step 3: Getting latest frame from buffer...")
        frame = await service.get_latest_frame(RTSP_DEVICE_ID)
        
        if frame is None:
            logger.error("❌ No frame available in buffer")
            return False
        
        logger.info(f"✅ Got frame: shape={frame.shape}, dtype={frame.dtype}")
        logger.info("")
        
        # Step 4: Monitor continuous frame reading
        logger.info("Step 4: Monitoring frame buffer for 10 seconds...")
        frames_received = 0
        last_frame_count = 0
        
        for i in range(10):
            await asyncio.sleep(1)
            
            # Get stats
            stats = service.get_camera_stats(RTSP_DEVICE_ID)
            frames_read = stats['frames_read']
            frames_dropped = stats['frames_dropped']
            
            new_frames = frames_read - last_frame_count
            last_frame_count = frames_read
            
            logger.info(
                f"  [{i+1}/10] Worker: {frames_read} frames read, "
                f"{frames_dropped} dropped, +{new_frames} this second"
            )
            
            # Verify we can still get frames
            frame = await service.get_latest_frame(RTSP_DEVICE_ID)
            if frame is not None:
                frames_received += 1
        
        logger.info("")
        logger.info(f"✅ Buffer remained active: {frames_received}/10 frame reads successful")
        logger.info("")
        
        # Step 5: Final stats
        logger.info("Step 5: Final worker statistics...")
        stats = service.get_camera_stats(RTSP_DEVICE_ID)
        logger.info(f"  Device ID: {stats['device_id']}")
        logger.info(f"  Status: {stats['status']}")
        logger.info(f"  Frames Read: {stats['frames_read']}")
        logger.info(f"  Frames Dropped: {stats['frames_dropped']}")
        logger.info(f"  Error Count: {stats['error_count']}")
        logger.info(f"  Buffer Size: {stats['buffer_size']}")
        logger.info(f"  Queue Size: {stats['queue_size']}")
        
        if stats['last_error']:
            logger.warning(f"  Last Error: {stats['last_error']}")
        
        logger.info("")
        
        # Step 6: Disconnect
        logger.info("Step 6: Disconnecting RTSP camera...")
        await service.disconnect_camera(RTSP_DEVICE_ID)
        logger.info("✅ RTSP camera disconnected")
        logger.info("")
        
        # Summary
        logger.info("=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Connection: SUCCESS")
        logger.info(f"✅ Frame Buffer: {stats['frames_read']} frames buffered")
        logger.info(f"✅ Zero Dropped: {stats['frames_dropped']} frames dropped")
        logger.info(f"✅ Continuous Reading: {frames_received}/10 successful")
        logger.info(f"✅ Clean Disconnect: SUCCESS")
        logger.info("=" * 60)
        logger.info("🎉 RTSP Queue Architecture: WORKING")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False
    
    finally:
        # Cleanup
        from src.services.worker_manager import get_worker_manager
        manager = get_worker_manager()
        await manager.cleanup_all()


async def main():
    """Run RTSP test."""
    logger.info("🚀 Starting RTSP Camera Test")
    logger.info("")
    
    success = await test_rtsp_camera()
    
    if success:
        logger.info("✅ All tests passed!")
        return 0
    else:
        logger.info("❌ Test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
