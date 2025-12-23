"""
Worker Manager - Manages all camera worker instances.

This module provides centralized management for camera workers:
- Create and start workers
- Track active workers
- Handle worker lifecycle (cleanup, restart)
- Provide worker access for endpoints
"""

import logging
from typing import Dict, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.services.camera_worker import CameraWorker, CameraStatus
from src.models.camera import CameraType

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages all camera worker instances.
    
    Provides centralized control for:
    - Creating workers for cameras
    - Starting/stopping workers
    - Accessing workers from async endpoints
    - Cleaning up inactive workers
    
    Usage:
        manager = WorkerManager()
        
        # Get or create worker
        worker = await manager.get_or_create_worker(
            device_id="usb_camera_0",
            camera_type=CameraType.USB,
            camera_info={...}
        )
        
        # Get existing worker
        worker = manager.get_worker("usb_camera_0")
        
        # Remove worker
        await manager.remove_worker("usb_camera_0")
        
        # Cleanup all
        await manager.cleanup_all()
    """
    
    def __init__(self, max_workers: int = 10):
        """
        Initialize worker manager.
        
        Args:
            max_workers: Maximum number of concurrent camera workers
        """
        self.workers: Dict[str, CameraWorker] = {}
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        logger.info(f"✅ WorkerManager initialized (max_workers={max_workers})")
    
    async def get_or_create_worker(
        self,
        device_id: str,
        camera_type: CameraType,
        camera_info: Dict
    ) -> CameraWorker:
        """
        Get existing worker or create new one.
        
        Args:
            device_id: Unique camera identifier
            camera_type: Type of camera
            camera_info: Camera configuration dict
            
        Returns:
            CameraWorker instance
            
        Raises:
            RuntimeError: If max workers limit reached
        """
        # Check if worker already exists
        if device_id in self.workers:
            worker = self.workers[device_id]
            
            # If worker thread is dead, remove and recreate
            if worker.worker_thread and not worker.worker_thread.is_alive():
                logger.warning(f"⚠️ Worker thread dead for {device_id}, recreating")
                await self.remove_worker(device_id)
            else:
                logger.debug(f"♻️ Reusing existing worker for {device_id}")
                return worker
        
        # Check max workers limit
        if len(self.workers) >= self.max_workers:
            raise RuntimeError(
                f"Maximum number of workers ({self.max_workers}) reached. "
                f"Remove inactive workers first."
            )
        
        # Create new worker
        logger.info(f"🆕 Creating new worker for {device_id} ({camera_type})")
        worker = CameraWorker(
            device_id=device_id,
            camera_type=camera_type,
            camera_info=camera_info
        )
        
        # Start worker thread
        worker.start()
        
        # Store worker
        self.workers[device_id] = worker
        
        logger.info(f"✅ Worker created and started for {device_id} ({len(self.workers)}/{self.max_workers} active)")
        return worker
    
    def get_worker(self, device_id: str) -> Optional[CameraWorker]:
        """
        Get existing worker by device ID.
        
        Args:
            device_id: Camera identifier
            
        Returns:
            CameraWorker if exists, None otherwise
        """
        return self.workers.get(device_id)
    
    async def remove_worker(self, device_id: str, timeout: float = 5.0) -> bool:
        """
        Remove and cleanup worker.
        
        Args:
            device_id: Camera identifier
            timeout: Max seconds to wait for worker to stop
            
        Returns:
            True if worker was removed, False if not found
        """
        if device_id not in self.workers:
            logger.warning(f"⚠️ Worker not found: {device_id}")
            return False
        
        worker = self.workers[device_id]
        
        logger.info(f"🗑️ Removing worker for {device_id}")
        
        # Stop worker (blocking operation, run in executor)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, worker.stop, timeout)
        
        # Remove from dict
        del self.workers[device_id]
        
        logger.info(f"✅ Worker removed for {device_id} ({len(self.workers)} remaining)")
        return True
    
    async def cleanup_all(self, timeout: float = 10.0):
        """
        Stop and cleanup all workers.
        
        Args:
            timeout: Max seconds to wait for each worker
        """
        logger.info(f"🧹 Cleaning up all workers ({len(self.workers)} active)")
        
        device_ids = list(self.workers.keys())
        
        for device_id in device_ids:
            try:
                await self.remove_worker(device_id, timeout=timeout)
            except Exception as e:
                logger.error(f"❌ Error removing worker {device_id}: {e}")
        
        logger.info("✅ All workers cleaned up")
    
    def get_all_workers(self) -> Dict[str, CameraWorker]:
        """
        Get all active workers.
        
        Returns:
            Dict of device_id -> CameraWorker
        """
        return self.workers.copy()
    
    def get_worker_count(self) -> int:
        """Get number of active workers."""
        return len(self.workers)
    
    def get_connected_workers(self) -> List[CameraWorker]:
        """
        Get list of workers with connected cameras.
        
        Returns:
            List of CameraWorker instances with status CONNECTED
        """
        return [
            worker for worker in self.workers.values()
            if worker.status == CameraStatus.CONNECTED
        ]
    
    def get_stats(self) -> Dict:
        """
        Get manager statistics.
        
        Returns:
            Dict with worker stats
        """
        workers_by_status = {}
        for worker in self.workers.values():
            status = worker.status.value
            workers_by_status[status] = workers_by_status.get(status, 0) + 1
        
        return {
            'total_workers': len(self.workers),
            'max_workers': self.max_workers,
            'workers_by_status': workers_by_status,
            'worker_stats': {
                device_id: worker.get_stats()
                for device_id, worker in self.workers.items()
            }
        }
    
    async def reconnect_worker(self, device_id: str, timeout: float = 15.0) -> bool:
        """
        Reconnect a worker (disconnect + connect).
        
        Args:
            device_id: Camera identifier
            timeout: Max seconds for reconnection
            
        Returns:
            True if reconnection successful
        """
        worker = self.get_worker(device_id)
        if not worker:
            logger.error(f"❌ Worker not found for reconnection: {device_id}")
            return False
        
        logger.info(f"🔄 Reconnecting worker {device_id}")
        
        try:
            # Send disconnect command
            cmd_id = worker.send_command({'action': 'disconnect'})
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                worker.wait_for_result,
                cmd_id,
                5.0
            )
            
            # Send connect command
            cmd_id = worker.send_command({
                'action': 'connect',
                'connection_string': worker.camera_info.get('connection_string')
            })
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                worker.wait_for_result,
                cmd_id,
                timeout
            )
            
            if result.get('success'):
                logger.info(f"✅ Worker reconnected: {device_id}")
                return True
            else:
                logger.error(f"❌ Reconnection failed: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error reconnecting worker {device_id}: {e}")
            return False
    
    def cleanup_dead_workers(self):
        """Remove workers with dead threads."""
        dead_workers = []
        
        for device_id, worker in self.workers.items():
            if worker.worker_thread and not worker.worker_thread.is_alive():
                dead_workers.append(device_id)
        
        for device_id in dead_workers:
            logger.warning(f"⚠️ Removing dead worker: {device_id}")
            del self.workers[device_id]
        
        if dead_workers:
            logger.info(f"🧹 Removed {len(dead_workers)} dead workers")


# Global worker manager instance
_worker_manager: Optional[WorkerManager] = None


def get_worker_manager() -> WorkerManager:
    """
    Get global worker manager instance (singleton).
    
    Returns:
        WorkerManager instance
    """
    global _worker_manager
    
    if _worker_manager is None:
        _worker_manager = WorkerManager(max_workers=10)
    
    return _worker_manager


async def cleanup_worker_manager():
    """Cleanup global worker manager on shutdown."""
    global _worker_manager
    
    if _worker_manager:
        await _worker_manager.cleanup_all()
        _worker_manager = None
