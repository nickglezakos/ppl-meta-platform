#!/usr/bin/env python3
"""
Test script for PPL Meta Mini Camera Integration (Upgrade 2)
Tests USB camera detection, recording, and analysis functionality.
"""

import json
import time
import requests
import sys
from typing import Dict, Any


class CameraTestSuite:
    """Test suite for camera functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8004"):
        """
        Initialize the test suite.
        
        Args:
            base_url: Base URL of the PPL Meta Mini service
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30  # 30 second timeout
        
    def test_service_health(self) -> bool:
        """Test if the service is running and healthy."""
        print("🏥 Testing service health...")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Service is healthy: {health_data}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to service: {e}")
            return False
    
    def test_root_endpoint(self) -> bool:
        """Test the root endpoint and check for camera endpoints."""
        print("🔍 Testing root endpoint...")
        
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                root_data = response.json()
                endpoints = root_data.get("endpoints", {})
                
                print(f"✅ Service info: {root_data.get('service', 'Unknown')}")
                print(f"✅ Version: {root_data.get('version', 'Unknown')}")
                
                # Check for camera endpoints
                camera_endpoints = [
                    "camera_detect", "camera_record", "camera_status"
                ]
                
                for endpoint in camera_endpoints:
                    if endpoint in endpoints:
                        print(f"✅ Camera endpoint found: {endpoint}")
                    else:
                        print(f"❌ Camera endpoint missing: {endpoint}")
                        return False
                
                return True
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    def test_camera_status(self) -> Dict[str, Any]:
        """Test camera status endpoint."""
        print("📹 Testing camera status...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/camera/status")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Camera status: {json.dumps(status_data, indent=2)}")
                return status_data
            else:
                print(f"❌ Camera status failed: {response.status_code}")
                print(f"Response: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Camera status error: {e}")
            return {}
    
    def test_camera_detection(self) -> Dict[str, Any]:
        """Test camera detection and connection."""
        print("🔍 Testing camera detection and connection...")
        
        try:
            response = self.session.post(f"{self.base_url}/api/v1/camera/detect-and-connect")
            
            if response.status_code == 200:
                detection_data = response.json()
                print(f"✅ Camera detection result:")
                print(json.dumps(detection_data, indent=2))
                
                if detection_data.get("camera_detected"):
                    print("✅ Camera detected and connection attempted")
                    if detection_data.get("connection_status") == "connected":
                        print("✅ Camera connected successfully")
                    else:
                        print(f"⚠️ Camera connection status: {detection_data.get('connection_status')}")
                else:
                    print("⚠️ No cameras detected")
                
                return detection_data
            else:
                print(f"❌ Camera detection failed: {response.status_code}")
                print(f"Response: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Camera detection error: {e}")
            return {}
    
    def test_camera_recording(self, duration: float = 2.0) -> Dict[str, Any]:
        """Test camera recording and analysis."""
        print(f"🎥 Testing camera recording ({duration}s)...")
        
        try:
            recording_request = {
                "duration": duration,
                "quality": "medium",
                "auto_delete": True
            }
            
            print(f"📤 Sending recording request: {recording_request}")
            
            response = self.session.post(
                f"{self.base_url}/api/v1/camera/record-and-analyze",
                json=recording_request
            )
            
            if response.status_code == 200:
                recording_data = response.json()
                print(f"✅ Recording completed:")
                
                # Print key information
                print(f"📹 Recording status: {recording_data.get('recording_status')}")
                print(f"⏱️ Processing time: {recording_data.get('processing_time_ms')}ms")
                
                # Check video info
                video_info = recording_data.get("video_info", {})
                if video_info:
                    print(f"📹 Video duration: {video_info.get('duration')}s")
                    print(f"📹 File size: {video_info.get('file_size')} bytes")
                    print(f"📹 Quality: {video_info.get('quality')}")
                
                # Check analysis results
                analysis_results = recording_data.get("analysis_results", {})
                if analysis_results:
                    persons = analysis_results.get("persons", {})
                    print(f"👥 Persons detected: {len(persons)}")
                    
                    for person_id, person_data in persons.items():
                        print(f"👤 {person_id}:")
                        print(f"   Age estimate: {person_data.get('age_estimate', 'Unknown')}")
                        print(f"   Unprocessed age: {person_data.get('unprocessed_age', 'Unknown')}")
                        print(f"   Quality score: {person_data.get('quality_score', 'Unknown')}")
                        print(f"   Distance: {person_data.get('distance', 'Unknown')}")
                else:
                    print("⚠️ No analysis results found")
                
                return recording_data
            else:
                print(f"❌ Recording failed: {response.status_code}")
                print(f"Response: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return {}
    
    def test_storage_info(self) -> Dict[str, Any]:
        """Test storage information endpoint."""
        print("💾 Testing storage information...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/camera/storage-info")
            if response.status_code == 200:
                storage_data = response.json()
                print(f"✅ Storage info: {json.dumps(storage_data, indent=2)}")
                return storage_data
            else:
                print(f"❌ Storage info failed: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Storage info error: {e}")
            return {}
    
    def test_cleanup(self) -> bool:
        """Test storage cleanup."""
        print("🧹 Testing storage cleanup...")
        
        try:
            response = self.session.post(f"{self.base_url}/api/v1/camera/cleanup")
            if response.status_code == 200:
                cleanup_data = response.json()
                print(f"✅ Cleanup result: {json.dumps(cleanup_data, indent=2)}")
                return True
            else:
                print(f"❌ Cleanup failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return False
    
    def run_full_test_suite(self) -> bool:
        """Run the complete camera test suite."""
        print("🚀 Starting PPL Meta Mini Camera Test Suite")
        print("=" * 60)
        
        # Test 1: Service Health
        if not self.test_service_health():
            print("❌ Service health test failed. Aborting.")
            return False
        
        print()
        
        # Test 2: Root Endpoint
        if not self.test_root_endpoint():
            print("❌ Root endpoint test failed. Camera endpoints may not be available.")
            return False
        
        print()
        
        # Test 3: Camera Status
        initial_status = self.test_camera_status()
        
        print()
        
        # Test 4: Camera Detection
        detection_result = self.test_camera_detection()
        
        print()
        
        # Test 5: Storage Info
        storage_info = self.test_storage_info()
        
        print()
        
        # Test 6: Camera Recording (only if camera connected)
        if detection_result.get("connection_status") == "connected":
            print("📹 Camera is connected, testing recording...")
            recording_result = self.test_camera_recording(duration=2.0)
            
            print()
            
            # Test 7: Storage cleanup
            self.test_cleanup()
        else:
            print("⚠️ No camera connected, skipping recording tests")
            print("💡 To test recording, connect a USB camera and re-run")
        
        print()
        print("✅ Camera test suite completed!")
        print("=" * 60)
        
        return True


def main():
    """Main test execution."""
    print("PPL Meta Mini Camera Integration Test")
    print("=====================================")
    print()
    
    # Check if service URL is provided
    base_url = "http://localhost:8004"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing service at: {base_url}")
    print()
    
    # Run tests
    test_suite = CameraTestSuite(base_url)
    success = test_suite.run_full_test_suite()
    
    if success:
        print("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()