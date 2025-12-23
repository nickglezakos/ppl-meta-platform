#!/usr/bin/env python3
"""
Backend Queue Infrastructure Validation Script

Tests Phase 1: Backend Queue Infrastructure Validation
- Step 1.1: Verify CameraWorker Implementation
- Step 1.2: Verify Worker Manager
- Step 1.3: Verify Non-Blocking Operation
"""

import asyncio
import time
import httpx
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.camera_worker import CameraWorker, CameraStatus, CameraCommand
from src.services.worker_manager import WorkerManager
from src.models.camera import CameraType


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


# =============================================================================
# STEP 1.1: Verify CameraWorker Implementation
# =============================================================================

def test_camera_worker_structure():
    """Test CameraWorker class structure."""
    print_header("Step 1.1: Verify CameraWorker Implementation")
    
    print_info("Testing CameraWorker class structure...")
    
    # Create test camera info
    camera_info = {
        "device_id": "test_camera_0",
        "name": "Test Camera",
        "camera_type": CameraType.USB,
        "connection_string": "/dev/video99",
        "index": 99,
        "resolution_width": 1920,
        "resolution_height": 1080,
        "max_fps": 30
    }
    
    try:
        # Create worker
        worker = CameraWorker(
            device_id="test_camera_0",
            camera_type=CameraType.USB,
            camera_info=camera_info
        )
        
        # Check required attributes
        checks = [
            (hasattr(worker, 'command_queue'), "command_queue attribute"),
            (hasattr(worker, 'frame_buffer'), "frame_buffer attribute"),
            (hasattr(worker, 'status'), "status property"),
            (hasattr(worker, 'status_lock'), "status_lock attribute"),
            (hasattr(worker, 'worker_thread'), "worker_thread attribute"),
            (hasattr(worker, '_worker_loop'), "_worker_loop method"),
            (hasattr(worker, 'start'), "start method"),
            (hasattr(worker, 'stop'), "stop method"),
            (hasattr(worker, 'send_command'), "send_command method"),
            (hasattr(worker, 'get_latest_frame'), "get_latest_frame method"),
        ]
        
        all_passed = True
        for check, name in checks:
            if check:
                print_success(f"{name} exists")
            else:
                print_error(f"{name} missing")
                all_passed = False
        
        # Check status is correct enum
        if worker.status == CameraStatus.DISCONNECTED:
            print_success("Initial status is DISCONNECTED")
        else:
            print_error(f"Initial status should be DISCONNECTED, got {worker.status}")
            all_passed = False
        
        # Check command queue is Queue object
        import queue
        if isinstance(worker.command_queue, queue.Queue):
            print_success("command_queue is queue.Queue instance")
        else:
            print_error(f"command_queue should be Queue, got {type(worker.command_queue)}")
            all_passed = False
        
        # Check frame buffer is deque with maxlen=1
        import collections
        if isinstance(worker.frame_buffer, collections.deque):
            print_success("frame_buffer is deque instance")
            if worker.frame_buffer.maxlen == 1:
                print_success("frame_buffer maxlen is 1 (latest frame only)")
            else:
                print_warning(f"frame_buffer maxlen is {worker.frame_buffer.maxlen}, should be 1")
        else:
            print_error(f"frame_buffer should be deque, got {type(worker.frame_buffer)}")
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_error(f"Failed to create CameraWorker: {e}")
        return False


def test_camera_worker_lifecycle():
    """Test CameraWorker start/stop lifecycle."""
    print_info("\nTesting CameraWorker lifecycle (start/stop)...")
    
    camera_info = {
        "device_id": "test_lifecycle",
        "name": "Test Lifecycle Camera",
        "camera_type": CameraType.USB,
        "connection_string": "/dev/video99",
        "index": 99
    }
    
    try:
        worker = CameraWorker(
            device_id="test_lifecycle",
            camera_type=CameraType.USB,
            camera_info=camera_info
        )
        
        # Start worker
        worker.start()
        time.sleep(0.5)  # Give thread time to start
        
        if worker.worker_thread and worker.worker_thread.is_alive():
            print_success("Worker thread started successfully")
        else:
            print_error("Worker thread failed to start")
            return False
        
        # Stop worker
        worker.stop(timeout=5.0)
        time.sleep(0.5)
        
        if worker.worker_thread and not worker.worker_thread.is_alive():
            print_success("Worker thread stopped successfully")
        else:
            print_error("Worker thread did not stop cleanly")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Lifecycle test failed: {e}")
        return False


# =============================================================================
# STEP 1.2: Verify Worker Manager
# =============================================================================

async def test_worker_manager_structure():
    """Test WorkerManager class structure."""
    print_header("Step 1.2: Verify Worker Manager")
    
    print_info("Testing WorkerManager class structure...")
    
    try:
        manager = WorkerManager(max_workers=5)
        
        # Check required attributes/methods
        checks = [
            (hasattr(manager, 'workers'), "workers dict"),
            (hasattr(manager, 'max_workers'), "max_workers attribute"),
            (hasattr(manager, 'get_or_create_worker'), "get_or_create_worker method"),
            (hasattr(manager, 'get_worker'), "get_worker method"),
            (hasattr(manager, 'remove_worker'), "remove_worker method"),
            (hasattr(manager, 'get_all_workers'), "get_all_workers method"),
        ]
        
        all_passed = True
        for check, name in checks:
            if check:
                print_success(f"{name} exists")
            else:
                print_error(f"{name} missing")
                all_passed = False
        
        # Check workers is dict
        if isinstance(manager.workers, dict):
            print_success("workers is dict instance")
        else:
            print_error(f"workers should be dict, got {type(manager.workers)}")
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_error(f"Failed to create WorkerManager: {e}")
        return False


async def test_worker_manager_operations():
    """Test WorkerManager create/get/remove operations."""
    print_info("\nTesting WorkerManager operations...")
    
    try:
        manager = WorkerManager(max_workers=5)
        
        # Test create worker
        camera_info = {
            "device_id": "test_manager_cam",
            "name": "Test Manager Camera",
            "camera_type": CameraType.USB,
            "connection_string": "/dev/video98",
            "index": 98
        }
        
        worker = await manager.get_or_create_worker(
            device_id="test_manager_cam",
            camera_type=CameraType.USB,
            camera_info=camera_info
        )
        
        if worker:
            print_success("Worker created via manager")
        else:
            print_error("Failed to create worker")
            return False
        
        # Test get worker
        retrieved = manager.get_worker("test_manager_cam")
        if retrieved is worker:
            print_success("Worker retrieved successfully")
        else:
            print_error("Failed to retrieve worker")
            return False
        
        # Test get_all_workers
        all_workers = manager.get_all_workers()
        if "test_manager_cam" in all_workers:
            print_success("Worker appears in get_all_workers()")
        else:
            print_error("Worker missing from get_all_workers()")
            return False
        
        # Test remove worker
        removed = await manager.remove_worker("test_manager_cam")
        if removed:
            print_success("Worker removed successfully")
        else:
            print_error("Failed to remove worker")
            return False
        
        # Verify removed
        retrieved = manager.get_worker("test_manager_cam")
        if retrieved is None:
            print_success("Worker confirmed removed")
        else:
            print_error("Worker still exists after removal")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Manager operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# STEP 1.3: Verify Non-Blocking Operation
# =============================================================================

async def test_nonblocking_api_calls():
    """Test that API calls are non-blocking."""
    print_header("Step 1.3: Verify Non-Blocking Operation")
    
    print_info("Testing non-blocking API behavior...")
    print_info("This will attempt to detect cameras and verify response times...")
    
    try:
        # Get auth token
        camera_base_url = "http://localhost:8005"
        auth_base_url = "http://localhost:8001"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login
            try:
                login_resp = await client.post(
                    f"{auth_base_url}/api/v1/users/login",
                    data={
                        "username": "fresh.user@example.com",
                        "password": "NewPassword234!"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                token = login_resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                print_success("Authenticated successfully")
            except Exception as e:
                print_error(f"Authentication failed: {e}")
                print_warning("Make sure node service is running on port 8001!")
                return False
            
            # Test detection endpoint (should be fast)
            print_info("\nTesting camera detection endpoint...")
            start_time = time.time()
            
            try:
                detect_resp = await client.post(
                    f"{camera_base_url}/api/v1/cameras/detect",
                    headers=headers
                )
                elapsed = time.time() - start_time
                
                if detect_resp.status_code == 200:
                    data = detect_resp.json()
                    num_cameras = len(data.get("cameras", []))
                    print_success(f"Detection completed in {elapsed:.2f}s")
                    print_info(f"Found {num_cameras} cameras")
                    
                    # Show camera details
                    for cam in data.get("cameras", []):
                        device_id = cam.get("device_id", "unknown")
                        status = cam.get("status", "unknown")
                        resolution = f"{cam.get('resolution_width', 0)}x{cam.get('resolution_height', 0)}"
                        print_info(f"  - {device_id}: {status} ({resolution})")
                    
                    if elapsed < 5.0:
                        print_success("Detection is reasonably fast (< 5 seconds)")
                    else:
                        print_warning(f"Detection took {elapsed:.2f}s, consider optimization")
                else:
                    print_error(f"Detection failed with status {detect_resp.status_code}")
                    print_error(detect_resp.text)
                    return False
                    
            except Exception as e:
                print_error(f"Detection request failed: {e}")
                return False
            
            # Test rapid sequential calls (should not block each other)
            print_info("\nTesting rapid sequential API calls...")
            
            call_times = []
            for i in range(3):
                start = time.time()
                try:
                    resp = await client.get(
                        f"{camera_base_url}/api/v1/cameras",
                        headers=headers
                    )
                    elapsed = time.time() - start
                    call_times.append(elapsed)
                    print_info(f"  Call {i+1}: {elapsed:.3f}s")
                except Exception as e:
                    print_error(f"Call {i+1} failed: {e}")
            
            avg_time = sum(call_times) / len(call_times)
            if avg_time < 1.0:
                print_success(f"Average API response time: {avg_time:.3f}s (non-blocking)")
            else:
                print_warning(f"Average API response time: {avg_time:.3f}s (may be blocking)")
            
            return True
            
    except Exception as e:
        print_error(f"Non-blocking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_all_tests():
    """Run all validation tests."""
    print_header("Backend Queue Infrastructure Validation")
    print_info("Running comprehensive validation tests...")
    
    results = {}
    
    # Step 1.1: CameraWorker tests
    results["worker_structure"] = test_camera_worker_structure()
    results["worker_lifecycle"] = test_camera_worker_lifecycle()
    
    # Step 1.2: WorkerManager tests
    results["manager_structure"] = await test_worker_manager_structure()
    results["manager_operations"] = await test_worker_manager_operations()
    
    # Step 1.3: Non-blocking tests
    results["nonblocking_api"] = await test_nonblocking_api_calls()
    
    # Summary
    print_header("Validation Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        color = Colors.OKGREEN if result else Colors.FAIL
        print(f"{color}{status:6}{Colors.ENDC} - {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    if failed > 0:
        print_error(f"{failed} tests failed")
        return False
    else:
        print_success("All validation tests passed! ✨")
        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
