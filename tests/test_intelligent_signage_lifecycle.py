#!/usr/bin/env python3
"""
Test script for Intelligent Signage Lifecycle - Webhook Flow

Tests the complete flow from camera instant detection to signage playlist switching:
1. Configure webhook in camera service
2. Create demographic trigger in media service  
3. Simulate webhook POST from camera
4. Verify trigger evaluation and action execution

Usage:
    python test_intelligent_signage_lifecycle.py
"""

import json
import requests
import time
from datetime import datetime

# Service URLs
CAMERA_SERVICE = "http://localhost:8005"
MEDIA_SERVICE = "http://localhost:8000"

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_step(step_num, description):
    """Print test step header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Step {step_num}: {description}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")


def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")


def test_step_1_configure_webhook():
    """Step 1: Configure webhook in camera service"""
    print_step(1, "Configure Webhook in Camera Service")
    
    webhook_config = {
        "url": f"{MEDIA_SERVICE}/api/v1/triggers/instant-detection",
        "enabled": True
    }
    
    print_info(f"Configuring webhook: {webhook_config['url']}")
    
    try:
        response = requests.post(
            f"{CAMERA_SERVICE}/api/v1/instant-detection/webhook/configure",
            json=webhook_config,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Webhook configured successfully")
            print(f"   URL: {result.get('webhook_url')}")
            print(f"   Enabled: {result.get('enabled')}")
            return True
        else:
            print_error(f"Failed to configure webhook: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error configuring webhook: {e}")
        return False


def test_step_2_create_trigger():
    """Step 2: Create demographic trigger in media service"""
    print_step(2, "Create Demographic Trigger in Media Service")
    
    trigger_config = {
        "name": "test_male_dominant_audience",
        "description": "Test trigger for male dominant audience",
        "camera_ids": ["usb_camera_0", "test_camera"],
        "conditions": [
            {
                "field": "percent_male",
                "operator": "gte",
                "value": 60
            },
            {
                "field": "people_count",
                "operator": "gte",
                "value": 2
            }
        ],
        "actions": [
            {
                "type": "signage_playback",
                "device_ids": ["test-device-uuid-1234"],
                "video_list_id": "test-playlist-uuid-5678",
                "start_index": 0,
                "volume": 80,
                "transition_mode": "after_current",
                "fade_duration_ms": 2000
            }
        ],
        "enabled": True,
        "cooldown_seconds": 10  # Short cooldown for testing
    }
    
    print_info("Creating trigger: test_male_dominant_audience")
    print(f"   Conditions: percent_male >= 60 AND people_count >= 2")
    print(f"   Cooldown: 10 seconds")
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE}/api/v1/triggers/demographic",
            json=trigger_config,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            print_success("Trigger created successfully")
            print(f"   Name: {result['trigger']['name']}")
            print(f"   Enabled: {result['trigger']['enabled']}")
            return True
        else:
            print_error(f"Failed to create trigger: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error creating trigger: {e}")
        return False


def test_step_3_simulate_webhook_match():
    """Step 3: Simulate webhook POST with matching demographics"""
    print_step(3, "Simulate Webhook POST (Matching Demographics)")
    
    webhook_payload = {
        "camera_id": "test_camera",
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": 3,
        "demographics": {
            "total_male": 2,
            "total_female": 1,
            "total_young": 0,
            "total_adult": 3,
            "percent_male": 67,  # MATCHES: >= 60
            "percent_female": 33,
            "percent_young": 0,
            "percent_adult": 100
        },
        "metadata": {
            "processing_time": 2.5,
            "total_faces": 3
        }
    }
    
    print_info("Sending webhook with demographics:")
    print(f"   Camera: {webhook_payload['camera_id']}")
    print(f"   People: {webhook_payload['people_count']}")
    print(f"   Male: {webhook_payload['demographics']['percent_male']}%")
    print(f"   Female: {webhook_payload['demographics']['percent_female']}%")
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE}/api/v1/triggers/instant-detection",
            json=webhook_payload,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Webhook processed successfully")
            print(f"   Triggers Evaluated: {result['triggers_evaluated']}")
            print(f"   Triggers Fired: {result['triggers_fired']}")
            print(f"   Fired Triggers: {result['fired_triggers']}")
            
            if result['triggers_fired'] > 0:
                print_success("✨ TRIGGER FIRED! Demographics matched conditions")
                return True
            else:
                print_error("Trigger did not fire (conditions not met or cooldown active)")
                return False
        else:
            print_error(f"Failed to process webhook: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error sending webhook: {e}")
        return False


def test_step_4_simulate_webhook_no_match():
    """Step 4: Simulate webhook POST with non-matching demographics"""
    print_step(4, "Simulate Webhook POST (Non-Matching Demographics)")
    
    webhook_payload = {
        "camera_id": "test_camera",
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": 2,
        "demographics": {
            "total_male": 1,
            "total_female": 1,
            "total_young": 0,
            "total_adult": 2,
            "percent_male": 50,  # DOES NOT MATCH: < 60
            "percent_female": 50,
            "percent_young": 0,
            "percent_adult": 100
        },
        "metadata": {
            "processing_time": 2.2,
            "total_faces": 2
        }
    }
    
    print_info("Sending webhook with demographics:")
    print(f"   Camera: {webhook_payload['camera_id']}")
    print(f"   People: {webhook_payload['people_count']}")
    print(f"   Male: {webhook_payload['demographics']['percent_male']}%")
    print(f"   Female: {webhook_payload['demographics']['percent_female']}%")
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE}/api/v1/triggers/instant-detection",
            json=webhook_payload,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Webhook processed successfully")
            print(f"   Triggers Evaluated: {result['triggers_evaluated']}")
            print(f"   Triggers Fired: {result['triggers_fired']}")
            
            if result['triggers_fired'] == 0:
                print_success("✅ Correctly skipped (conditions not met)")
                return True
            else:
                print_error("Trigger fired when it shouldn't have!")
                return False
        else:
            print_error(f"Failed to process webhook: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error sending webhook: {e}")
        return False


def test_step_5_verify_cooldown():
    """Step 5: Verify cooldown prevents immediate re-triggering"""
    print_step(5, "Verify Cooldown Prevention")
    
    print_info("Sending matching demographics again immediately...")
    print_info("Expected: Should be skipped due to cooldown")
    
    webhook_payload = {
        "camera_id": "test_camera",
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": 3,
        "demographics": {
            "total_male": 2,
            "total_female": 1,
            "percent_male": 67,  # MATCHES
            "percent_female": 33,
            "percent_young": 0,
            "percent_adult": 100
        }
    }
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE}/api/v1/triggers/instant-detection",
            json=webhook_payload,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result['triggers_fired'] == 0:
                print_success("✅ Correctly prevented by cooldown")
                return True
            else:
                print_error("Trigger fired during cooldown period!")
                return False
        else:
            print_error(f"Failed to process webhook: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error sending webhook: {e}")
        return False


def test_step_6_list_triggers():
    """Step 6: List all triggers and verify status"""
    print_step(6, "List All Triggers and Status")
    
    try:
        response = requests.get(
            f"{MEDIA_SERVICE}/api/v1/triggers/demographic",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Found {result['total']} trigger(s)")
            
            for trigger_info in result['triggers']:
                trigger = trigger_info['trigger']
                cooldown_status = trigger_info['cooldown_status']
                
                print(f"\n   Trigger: {trigger['name']}")
                print(f"   Enabled: {trigger['enabled']}")
                print(f"   Conditions: {len(trigger['conditions'])}")
                print(f"   Actions: {len(trigger['actions'])}")
                
                for camera_id, status in cooldown_status.items():
                    print(f"\n   Camera: {camera_id}")
                    if status['last_fired']:
                        print(f"      Last Fired: {status['last_fired']}")
                        print(f"      Elapsed: {status['elapsed_seconds']}s")
                        print(f"      Cooldown Remaining: {status['cooldown_remaining']}s")
                        print(f"      Can Fire: {status['can_fire']}")
                    else:
                        print(f"      Status: Never fired")
            
            return True
        else:
            print_error(f"Failed to list triggers: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error listing triggers: {e}")
        return False


def test_step_7_cleanup():
    """Step 7: Cleanup test trigger"""
    print_step(7, "Cleanup Test Trigger")
    
    try:
        response = requests.delete(
            f"{MEDIA_SERVICE}/api/v1/triggers/demographic/test_male_dominant_audience",
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("Test trigger deleted successfully")
            return True
        else:
            print_error(f"Failed to delete trigger: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error deleting trigger: {e}")
        return False


def main():
    """Run all test steps"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🧪 Intelligent Signage Lifecycle - Integration Test{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    print_info(f"Camera Service: {CAMERA_SERVICE}")
    print_info(f"Media Service: {MEDIA_SERVICE}")
    
    results = []
    
    # Run test steps
    results.append(("Configure Webhook", test_step_1_configure_webhook()))
    results.append(("Create Trigger", test_step_2_create_trigger()))
    results.append(("Test Matching Demographics", test_step_3_simulate_webhook_match()))
    results.append(("Test Non-Matching Demographics", test_step_4_simulate_webhook_no_match()))
    results.append(("Test Cooldown Prevention", test_step_5_verify_cooldown()))
    results.append(("List Triggers Status", test_step_6_list_triggers()))
    results.append(("Cleanup", test_step_7_cleanup()))
    
    # Print summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for step_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"   {step_name}: {status}")
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    if passed == total:
        print(f"{GREEN}✅ ALL TESTS PASSED ({passed}/{total}){RESET}")
    else:
        print(f"{RED}❌ SOME TESTS FAILED ({passed}/{total}){RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
