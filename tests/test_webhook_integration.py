#!/usr/bin/env python3
"""
Webhook Integration Test Script
Purpose: Test webhook action creation and execution
Version: 1.0.0
Created: 2025-01-15
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Service URLs
MEDIA_SERVICE_URL = "http://localhost:8001"
COMMS_SERVICE_URL = "http://localhost:8004"
GATEWAY_URL = "http://localhost:8003"

# Test webhook URL (replace with your webhook.site URL)
WEBHOOK_TEST_URL = "https://webhook.site/unique-uuid-here"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_header(message: str):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{message:^60}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {message}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.YELLOW}{message}{Colors.NC}")


def check_service_health(url: str, name: str) -> bool:
    """Check if a service is healthy"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"{name} is healthy")
            return True
        else:
            print_error(f"{name} returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"{name} is not responding: {e}")
        return False


def create_webhook_action(webhook_url: str) -> Optional[str]:
    """Create a webhook action and return its UUID"""
    print_info("Step 1: Creating webhook action...")
    
    webhook_config = {
        "url": webhook_url,
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "X-Custom-Header": "PPL-Meta-Test"
        },
        "payload_data": {
            "source": "ppl-meta-platform",
            "test": True
        }
    }
    
    action_data = {
        "name": "Test Webhook Action",
        "description": "Integration test webhook",
        "action_type": "webhook",
        "action_config": json.dumps(webhook_config),
        "is_active": True
    }
    
    try:
        response = requests.post(
            f"{MEDIA_SERVICE_URL}/api/v1/user-actions",
            json=action_data,
            timeout=10
        )
        response.raise_for_status()
        
        action_uuid = response.json().get("uuid")
        if action_uuid:
            print_success(f"Webhook action created with UUID: {action_uuid}")
            return action_uuid
        else:
            print_error("No UUID in response")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to create webhook action: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None


def send_test_webhook(webhook_url: str, action_uuid: str) -> Optional[Dict[str, Any]]:
    """Send a test webhook and return the response"""
    print_info("Step 2: Sending test webhook...")
    
    webhook_payload = {
        "event": "test_webhook",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "message": "Webhook integration test",
            "action_uuid": action_uuid
        }
    }
    
    webhook_request = {
        "url": webhook_url,
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "X-Test-Header": "Integration-Test"
        },
        "payload": webhook_payload,
        "trigger_id": f"test-trigger-{int(time.time())}",
        "tenant_name": "test-tenant"
    }
    
    try:
        response = requests.post(
            f"{COMMS_SERVICE_URL}/api/v1/webhook/send",
            json=webhook_request,
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        status = result.get("status")
        
        if status in ["delivered", "sent"]:
            print_success(f"Webhook sent successfully with status: {status}")
            comm_log_id = result.get("communication_log_id")
            if comm_log_id:
                print(f"   Communication Log ID: {comm_log_id}")
            return result
        else:
            print_error(f"Unexpected webhook status: {status}")
            print(f"Response: {json.dumps(result, indent=2)}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to send webhook: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None


def verify_communication_logs() -> int:
    """Verify webhook logs were created and return count"""
    print_info("Step 3: Verifying communication logs...")
    
    time.sleep(1)  # Wait for logs to be written
    
    try:
        response = requests.get(
            f"{COMMS_SERVICE_URL}/api/v1/audit/logs",
            params={"type": "webhook", "page": 1, "page_size": 5},
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        total = result.get("total", 0)
        
        if total > 0:
            print_success(f"Found {total} webhook log(s)")
            
            # Display latest log
            if result.get("logs"):
                latest_log = result["logs"][0]
                print(f"\n{Colors.BLUE}Latest Webhook Log:{Colors.NC}")
                print(json.dumps({
                    "id": latest_log.get("id"),
                    "type": latest_log.get("type"),
                    "status": latest_log.get("status"),
                    "trigger_id": latest_log.get("trigger_id"),
                    "created_at": latest_log.get("created_at"),
                    "response_data": latest_log.get("response_data")
                }, indent=2))
            
            return total
        else:
            print_warning("No webhook logs found (this might be expected if logs are async)")
            return 0
            
    except requests.exceptions.RequestException as e:
        print_warning(f"Could not verify logs: {e}")
        return 0


def delete_webhook_action(action_uuid: str) -> bool:
    """Delete the test webhook action"""
    print_info("Step 4: Cleaning up test resources...")
    
    try:
        response = requests.delete(
            f"{MEDIA_SERVICE_URL}/api/v1/user-actions/{action_uuid}",
            timeout=10
        )
        response.raise_for_status()
        
        print_success("Test webhook action deleted")
        return True
        
    except requests.exceptions.RequestException as e:
        print_warning(f"Could not delete test action: {e}")
        return False


def main():
    """Main test execution"""
    print_header("Webhook Integration Test Suite")
    
    # Step 0: Health checks
    print_info("Step 0: Verifying service health...")
    services_healthy = all([
        check_service_health(MEDIA_SERVICE_URL, "Media Service"),
        check_service_health(COMMS_SERVICE_URL, "Communications Service"),
        check_service_health(GATEWAY_URL, "Gateway")
    ])
    
    if not services_healthy:
        print_error("\nSome services are not healthy. Aborting tests.")
        return False
    
    print()
    
    # Create webhook action
    action_uuid = create_webhook_action(WEBHOOK_TEST_URL)
    if not action_uuid:
        print_error("\nFailed to create webhook action. Aborting tests.")
        return False
    
    print()
    
    # Send test webhook
    webhook_result = send_test_webhook(WEBHOOK_TEST_URL, action_uuid)
    if not webhook_result:
        print_error("\nFailed to send test webhook.")
        # Continue to cleanup
    
    print()
    
    # Verify logs
    log_count = verify_communication_logs()
    
    print()
    
    # Cleanup
    delete_webhook_action(action_uuid)
    
    # Summary
    print_header("Test Summary")
    
    if webhook_result and log_count > 0:
        print_success("All webhook integration tests passed!")
        print("\nNext steps:")
        print("  1. Check webhook.site for received webhooks")
        print("  2. Verify frontend displays webhook actions correctly")
        print("  3. Test webhook actions with real triggers")
        print()
        return True
    else:
        print_warning("Some tests did not complete successfully.")
        print("Review the output above for details.")
        print()
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        exit(1)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
