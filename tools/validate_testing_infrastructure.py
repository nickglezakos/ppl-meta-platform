#!/usr/bin/env python3
"""
🧪 Testing Infrastructure Validation Script
PPL Meta Platform - Cross-Video Individual Tracking

This script validates that the individual_headless_testing.py script
is working correctly by testing its components with mock data.

Usage:
    python validate_testing_infrastructure.py

Author: PPL Meta Platform Team
Date: October 20, 2025
Version: 1.0.0
"""

import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch
import subprocess

# Color constants for console output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    """Print validation script header"""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}=" * 80)
    print("🧪 PPL Meta - Testing Infrastructure Validation")
    print("Cross-Video Individual Tracking Testing Script Validation")
    print(f"Version 1.0.0 | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + f"{Colors.ENDC}\n")

def test_script_executable() -> bool:
    """Test if the individual_headless_testing.py script is executable"""
    print(f"{Colors.OKBLUE}🔍 Testing script executable...{Colors.ENDC}")
    
    try:
        result = subprocess.run([
            "python", "individual_headless_testing.py", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "Individual Cross-Video Tracking" in result.stdout:
            print(f"{Colors.OKGREEN}✅ Script is executable and responds to --help{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}❌ Script failed to execute properly{Colors.ENDC}")
            print(f"Return code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"{Colors.FAIL}❌ Script execution timed out{Colors.ENDC}")
        return False
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error testing script: {str(e)}{Colors.ENDC}")
        return False

def test_imports() -> bool:
    """Test if all required imports are available"""
    print(f"{Colors.OKBLUE}📦 Testing required imports...{Colors.ENDC}")
    
    required_imports = [
        "requests",
        "rich",
        "dateutil"
    ]
    
    missing_imports = []
    
    for module in required_imports:
        try:
            if module == "dateutil":
                import dateutil
            else:
                __import__(module)
            print(f"{Colors.OKGREEN}  ✅ {module} available{Colors.ENDC}")
        except ImportError:
            print(f"{Colors.WARNING}  ⚠️  {module} not available{Colors.ENDC}")
            missing_imports.append(module)
    
    if missing_imports:
        print(f"{Colors.WARNING}📝 Missing imports: {', '.join(missing_imports)}{Colors.ENDC}")
        print(f"{Colors.WARNING}   Run: pip install {' '.join(missing_imports)}{Colors.ENDC}")
        return False
    else:
        print(f"{Colors.OKGREEN}✅ All required imports available{Colors.ENDC}")
        return True

def test_script_components() -> bool:
    """Test individual components of the testing script"""
    print(f"{Colors.OKBLUE}🔧 Testing script components...{Colors.ENDC}")
    
    try:
        # Import the testing script as a module
        sys.path.insert(0, '.')
        import individual_headless_testing as iht
        
        # Test TestConfig dataclass
        config = iht.TestConfig()
        print(f"{Colors.OKGREEN}  ✅ TestConfig class working{Colors.ENDC}")
        
        # Test TrackingRequest dataclass
        request = iht.TrackingRequest(
            collections=["test_collection"],
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        request_dict = request.to_dict()
        print(f"{Colors.OKGREEN}  ✅ TrackingRequest class working{Colors.ENDC}")
        
        # Test ConsoleOutput class
        console = iht.ConsoleOutput()
        print(f"{Colors.OKGREEN}  ✅ ConsoleOutput class working{Colors.ENDC}")
        
        # Test APIClient class (without actual API calls)
        api_client = iht.APIClient(config)
        print(f"{Colors.OKGREEN}  ✅ APIClient class working{Colors.ENDC}")
        
        # Test IndividualTrackingTester class
        tester = iht.IndividualTrackingTester(config)
        print(f"{Colors.OKGREEN}  ✅ IndividualTrackingTester class working{Colors.ENDC}")
        
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error testing components: {str(e)}{Colors.ENDC}")
        return False

def test_mock_api_responses() -> bool:
    """Test script behavior with mock API responses"""
    print(f"{Colors.OKBLUE}🎭 Testing with mock API responses...{Colors.ENDC}")
    
    try:
        sys.path.insert(0, '.')
        import individual_headless_testing as iht
        
        # Mock API responses
        mock_session_response = {
            "session_uuid": "test-session-123",
            "status": "initialized",
            "message": "Session created successfully"
        }
        
        mock_status_response = {
            "session_uuid": "test-session-123",
            "status": "completed",
            "total_videos": 10,
            "processed_videos": 10,
            "failed_videos": [],
            "individuals_found": 5,
            "person_objects_processed": 25,
            "cache_hits": 3,
            "processing_time_seconds": 12.5
        }
        
        mock_results_response = {
            "session": mock_status_response,
            "individuals": [
                {
                    "individual_id": "individual_001",
                    "confidence_score": 0.95,
                    "video_appearances": [
                        {
                            "video_uuid": "video-1",
                            "start_timestamp": "2025-10-20T10:00:00",
                            "end_timestamp": "2025-10-20T10:05:00"
                        }
                    ]
                }
            ]
        }
        
        mock_cache_response = {
            "total_cached_videos": 50,
            "total_individuals": 15,
            "total_sessions": 3,
            "cache_size_mb": 125.7,
            "hit_rate_last_30_days": 0.4,
            "collections_covered": ["test_collection_1", "test_collection_2"]
        }
        
        config = iht.TestConfig()
        tester = iht.IndividualTrackingTester(config)
        
        # Test result display methods with mock data
        tester.display_summary_statistics(mock_results_response)
        print(f"{Colors.OKGREEN}  ✅ Summary statistics display working{Colors.ENDC}")
        
        tester.display_cache_statistics(mock_cache_response)
        print(f"{Colors.OKGREEN}  ✅ Cache statistics display working{Colors.ENDC}")
        
        # Test time formatting methods
        time_span = tester.format_time_span(mock_results_response["individuals"][0]["video_appearances"])
        movement = tester.format_movement_pattern(mock_results_response["individuals"][0]["video_appearances"])
        print(f"{Colors.OKGREEN}  ✅ Time formatting methods working{Colors.ENDC}")
        
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error testing with mock data: {str(e)}{Colors.ENDC}")
        return False

def test_configuration_options() -> bool:
    """Test configuration and command line options"""
    print(f"{Colors.OKBLUE}⚙️  Testing configuration options...{Colors.ENDC}")
    
    try:
        # Test different command line options
        test_commands = [
            ["python", "individual_headless_testing.py", "--help"],
            ["python", "individual_headless_testing.py", "--api-url", "http://test.com", "--help"],
            ["python", "individual_headless_testing.py", "--timeout", "60", "--help"],
            ["python", "individual_headless_testing.py", "--debug", "--help"]
        ]
        
        for cmd in test_commands:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                print(f"{Colors.FAIL}❌ Command failed: {' '.join(cmd)}{Colors.ENDC}")
                return False
        
        print(f"{Colors.OKGREEN}✅ All configuration options working{Colors.ENDC}")
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error testing configuration: {str(e)}{Colors.ENDC}")
        return False

def test_requirements_file() -> bool:
    """Test if requirements.txt is valid"""
    print(f"{Colors.OKBLUE}📋 Testing requirements.txt...{Colors.ENDC}")
    
    try:
        with open("requirements.txt", "r") as f:
            requirements = f.read()
        
        # Check for essential packages
        essential_packages = ["requests", "rich", "python-dateutil"]
        for package in essential_packages:
            if package in requirements:
                print(f"{Colors.OKGREEN}  ✅ {package} in requirements{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}  ⚠️  {package} missing from requirements{Colors.ENDC}")
                return False
        
        print(f"{Colors.OKGREEN}✅ Requirements file is valid{Colors.ENDC}")
        return True
        
    except FileNotFoundError:
        print(f"{Colors.FAIL}❌ requirements.txt not found{Colors.ENDC}")
        return False
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error reading requirements.txt: {str(e)}{Colors.ENDC}")
        return False

def test_setup_script() -> bool:
    """Test if setup_testing.sh exists and is executable"""
    print(f"{Colors.OKBLUE}🔧 Testing setup script...{Colors.ENDC}")
    
    try:
        import os
        if os.path.exists("setup_testing.sh"):
            if os.access("setup_testing.sh", os.X_OK):
                print(f"{Colors.OKGREEN}✅ setup_testing.sh exists and is executable{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}⚠️  setup_testing.sh exists but is not executable{Colors.ENDC}")
                print(f"{Colors.WARNING}   Run: chmod +x setup_testing.sh{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}❌ setup_testing.sh not found{Colors.ENDC}")
            return False
            
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error testing setup script: {str(e)}{Colors.ENDC}")
        return False

def run_validation_suite() -> Dict[str, bool]:
    """Run complete validation suite"""
    print_header()
    
    tests = [
        ("Script Executable", test_script_executable),
        ("Required Imports", test_imports),
        ("Script Components", test_script_components),
        ("Mock API Responses", test_mock_api_responses),
        ("Configuration Options", test_configuration_options),
        ("Requirements File", test_requirements_file),
        ("Setup Script", test_setup_script)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{Colors.HEADER}{'=' * 50}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}Testing: {test_name}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 50}{Colors.ENDC}")
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"{Colors.FAIL}❌ Unexpected error in {test_name}: {str(e)}{Colors.ENDC}")
            results[test_name] = False
    
    return results

def print_summary(results: Dict[str, bool]):
    """Print validation summary"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=" * 80)
    print("🏁 VALIDATION SUMMARY")
    print("=" * 80 + f"{Colors.ENDC}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}" if result else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
        print(f"  {status} {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}The Individual Headless Testing infrastructure is ready for use.{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}Next steps:{Colors.ENDC}")
        print(f"  1. Run: {Colors.BOLD}./setup_testing.sh{Colors.ENDC} (if not done)")
        print(f"  2. Run: {Colors.BOLD}source venv/bin/activate{Colors.ENDC}")
        print(f"  3. Run: {Colors.BOLD}python individual_headless_testing.py{Colors.ENDC}")
        return True
    else:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  SOME TESTS FAILED{Colors.ENDC}")
        print(f"{Colors.WARNING}Please address the failed tests before using the testing infrastructure.{Colors.ENDC}")
        return False

def main():
    """Main validation entry point"""
    try:
        results = run_validation_suite()
        success = print_summary(results)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⚠️  Validation interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Fatal validation error: {str(e)}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()