#!/usr/bin/env python3
"""
Test Integrated Demographic Triggers System

Tests the integration of demographic triggers into the existing triggers infrastructure:
1. Configure webhook in camera service
2. Create trigger with demographic conditions using existing API
3. Simulate webhook POST from camera
4. Verify trigger evaluation and signage action

Usage:
    python test_integrated_demographic_triggers.py
"""

import json
import requests
import time
from datetime import datetime

# Service URLs
CAMERA_SERVICE = "http://localhost:8005"
MEDIA_SERVICE = "http://localhost:8000"  # Direct media service (has signage API)

# ANSI colors
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
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message):
    print(f"{RED}❌ {message}{RESET}")


def print_info(message):
    print(f"{YELLOW}ℹ️  {message}{RESET}")


def test_step_1_configure_webhook():
    """Configure webhook in camera service"""
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
            print_success("Webhook configured successfully")
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


def test_step_2_create_integrated_trigger():
    """Create trigger using existing triggers API with demographic fields"""
    print_step(2, "Create Trigger with Demographic Conditions")
    
    # Demographic conditions as JSON string
    demographic_conditions = json.dumps([
        {"field": "percent_male", "operator": "gte", "value": 60},
        {"field": "people_count", "operator": "gte", "value": 2}
    ])
    
    # Signage device IDs as JSON string
    signage_device_ids = json.dumps(["test-device-uuid-1234"])
    
    trigger_config = {
        # Existing fields (required but not used for demographic evaluation)
        "person_count_operator": "more_than",
        "person_count_value": "0",
        "age_range": "any",
        "gender_filter": "any",
        "camera_device_id": "test_camera",
        "time_span": "",
        "action": "log",
        "is_active": True,
        
        # New demographic fields
        "enable_demographic_conditions": True,
        "demographic_conditions": demographic_conditions,
        "signage_device_ids": signage_device_ids,
        "signage_playlist_id": "test-playlist-uuid-5678",
        "signage_transition_mode": "after_current",
        "signage_fade_duration_ms": 2000,
        "cooldown_seconds": 10,  # Short cooldown for testing
        
        # Metadata
        "name": "Test Male Dominant Audience",
        "description": "Test trigger for demographic-based signage control"
    }
    
    print_info("Creating trigger with demographic conditions:")
    print(f"   Name: {trigger_config['name']}")
    print(f"   Camera: {trigger_config['camera_device_id']}")
    print(f"   Conditions: percent_male >= 60 AND people_count >= 2")
    print(f"   Signage Playlist: {trigger_config['signage_playlist_id']}")
    print(f"   Transition Mode: {trigger_config['signage_transition_mode']}")
    print(f"   Cooldown: {trigger_config['cooldown_seconds']}s")
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE}/api/v1/triggers",
            json=trigger_config,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            print_success("Trigger created successfully")
            print(f"   UUID: {result['uuid']}")
            print(f"   Name: {result['name']}")
            print(f"   Demographic Enabled: {result['enable_demographic_conditions']}")
            return result['uuid']
        else:
            print_error(f"Failed to create trigger: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Error creating trigger: {e}")
        return None


def test_step_3_simulate_webhook_match(trigger_uuid):
    """Simulate webhook POST with matching demographics"""
    print_step(3, "Simulate Webhook POST (Matching Demographics)")
    
    webhook_payload = {
        "camera_id": "test_camera",
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": 3,
        "demographics": {
            "total_male": 2,
            "total_female": 1,
            "percent_male": 67,  # MATCHES: >= 60
            "percent_female": 33,
            "age_distribution": {
                "18-25": 1,
                "26-40": 2
            },
            "gender_distribution": {
                "male": 2,
                "female": 1
            }
        },
        "metadata": {}
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
            print(f"   Camera: {result['camera_id']}")
            print(f"   Timestamp: {result['timestamp']}")
            print(f"   People Count: {result['people_count']}")
            print(f"   Triggers Evaluated: {result['triggers_evaluated']}")
            print(f"   Triggers Fired: {result['triggers_fired']}")
            
            # Print detailed results
            if result.get('results'):
                print("\n   Evaluation Results:")
                for eval_result in result['results']:
                    status = "✅ PASSED" if eval_result['passed'] else "❌ FAILED"
                    print(f"      {status} - {eval_result['trigger_name']}: {eval_result['reason']}")
            
            if result['triggers_fired'] > 0:
                print_success("✨ TRIGGER FIRED! Demographics matched conditions")
                return True
            else:
                print_error("Trigger did not fire")
                return False
        else:
            print_error(f"Webhook failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error sending webhook: {e}")
        return False


def test_step_4_simulate_webhook_no_match(trigger_uuid):
    """Simulate webhook POST with non-matching demographics"""
    print_step(4, "Simulate Webhook POST (Non-Matching Demographics)")
    
    webhook_payload = {
        "camera_id": "test_camera",
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": 3,
        "demographics": {
            "total_male": 1,
            "total_female": 2,
            "percent_male": 33,  # DOES NOT MATCH: < 60
            "percent_female": 67,
            "age_distribution": {
                "18-25": 1,
                "26-40": 2
            },
            "gender_distribution": {
                "male": 1,
                "female": 2
            }
        },
        "metadata": {}
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
            
            if result.get('results'):
                print("\n   Evaluation Results:")
                for eval_result in result['results']:
                    status = "✅ PASSED" if eval_result['passed'] else "❌ FAILED"
                    print(f"      {status} - {eval_result['trigger_name']}: {eval_result['reason']}")
            
            if result['triggers_fired'] == 0:
                print_success("✅ Trigger correctly did NOT fire (conditions not met)")
                return True
            else:
                print_error("Trigger should not have fired!")
                return False
        else:
            print_error(f"Webhook failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error sending webhook: {e}")
        return False


def test_step_5_test_cooldown(trigger_uuid):
    """Test cooldown mechanism"""
    print_step(5, "Test Cooldown Mechanism")
    
    webhook_payload = {
        "camera_id": "test_camera",
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": 3,
        "demographics": {
            "percent_male": 67,
            "percent_female": 33
        },
        "metadata": {}
    }
    
    print_info("Sending webhook immediately after previous trigger...")
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE}/api/v1/triggers/instant-detection",
            json=webhook_payload,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('results'):
                for eval_result in result['results']:
                    if 'cooldown' in eval_result['reason'].lower():
                        print_success("✅ Cooldown is working! Trigger blocked")
                        print(f"      Reason: {eval_result['reason']}")
                        return True
            
            if result['triggers_fired'] == 0:
                print_success("✅ Cooldown prevented trigger from firing")
                return True
            else:
                print_error("Trigger fired despite cooldown!")
                return False
        else:
            print_error(f"Webhook failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error sending webhook: {e}")
        return False


def test_step_6_verify_trigger_in_list(trigger_uuid):
    """Verify trigger appears in triggers list"""
    print_step(6, "Verify Trigger in List")
    
    print_info("Fetching triggers list...")
    
    try:
        response = requests.get(
            f"{MEDIA_SERVICE}/api/v1/triggers",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            triggers = result.get('triggers', [])
            
            print_info(f"Found {len(triggers)} total triggers")
            
            # Find our trigger
            our_trigger = None
            for trigger in triggers:
                if trigger['uuid'] == trigger_uuid:
                    our_trigger = trigger
                    break
            
            if our_trigger:
                print_success("✅ Trigger found in list")
                print(f"   UUID: {our_trigger['uuid']}")
                print(f"   Name: {our_trigger['name']}")
                print(f"   Active: {our_trigger['is_active']}")
                print(f"   Demographic Enabled: {our_trigger.get('enable_demographic_conditions')}")
                print(f"   Signage Playlist: {our_trigger.get('signage_playlist_id')}")
                return True
            else:
                print_error("Trigger not found in list!")
                return False
        else:
            print_error(f"Failed to fetch triggers: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error fetching triggers: {e}")
        return False


def main():
    """Run all test steps"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Integrated Demographic Triggers - Test Suite{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    results = {
        "passed": 0,
        "failed": 0
    }
    
    # Step 1: Configure webhook
    if test_step_1_configure_webhook():
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot proceed without webhook configuration")
        return
    
    # Step 2: Create trigger
    trigger_uuid = test_step_2_create_integrated_trigger()
    if trigger_uuid:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Cannot proceed without trigger creation")
        return
    
    # Small delay to ensure trigger is ready
    time.sleep(1)
    
    # Step 3: Test matching demographics
    if test_step_3_simulate_webhook_match(trigger_uuid):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Small delay between webhooks
    time.sleep(1)
    
    # Step 4: Test non-matching demographics
    if test_step_4_simulate_webhook_no_match(trigger_uuid):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Step 5: Test cooldown
    if test_step_5_test_cooldown(trigger_uuid):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Step 6: Verify in list
    if test_step_6_verify_trigger_in_list(trigger_uuid):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Print summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    print(f"{GREEN}Passed: {results['passed']}{RESET}")
    print(f"{RED}Failed: {results['failed']}{RESET}")
    print(f"\n{BLUE}{'='*70}{RESET}\n")
    
    if results["failed"] == 0:
        print_success("🎉 ALL TESTS PASSED! Integration successful!")
    else:
        print_error(f"Some tests failed. Please review the output above.")


if __name__ == "__main__":
    main()
