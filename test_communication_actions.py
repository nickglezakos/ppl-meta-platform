#!/usr/bin/env python3
"""
Test script for Communications Service integration with Trigger Actions

This script tests the new email, webhook, and log action types that use
the Communications Service.

Prerequisites:
- Media Service running on port 8000
- Communications Service running on port 8009
- Both services healthy

Usage:
    python test_communication_actions.py
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any


# Configuration
MEDIA_SERVICE_URL = "http://localhost:8000"
COMMUNICATIONS_SERVICE_URL = "http://localhost:8009"


def check_services() -> bool:
    """Check if required services are running"""
    print("🔍 Checking service health...\n")
    
    services = {
        "Media Service": f"{MEDIA_SERVICE_URL}/health",
        "Communications Service": f"{COMMUNICATIONS_SERVICE_URL}/health"
    }
    
    all_healthy = True
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"  ✅ {name}: healthy")
            else:
                print(f"  ❌ {name}: unhealthy (status {response.status_code})")
                all_healthy = False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {name}: not responding ({e})")
            all_healthy = False
    
    print()
    return all_healthy


def create_action(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a trigger action via Media Service API"""
    url = f"{MEDIA_SERVICE_URL}/api/v1/user-actions/"
    
    try:
        response = requests.post(url, json=action_data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Failed to create action: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"     Response: {e.response.text}")
        return None


def test_email_action():
    """Test creating an email action"""
    print("📧 Testing Email Action Creation")
    print("-" * 50)
    
    action_config = {
        "recipients": ["admin@example.com", "alerts@example.com"],
        "subject": "PPL Meta Alert: {trigger_name}",
        "body": "Trigger '{trigger_name}' (ID: {trigger_id}) was fired. Please check the system."
    }
    
    action_data = {
        "name": "Test Email Alert",
        "description": "Sends email notifications when trigger fires",
        "action_type": "email",
        "action_config": json.dumps(action_config),
        "is_active": True,
        "created_by": "test_script"
    }
    
    print(f"  Action Config:")
    print(f"    Recipients: {action_config['recipients']}")
    print(f"    Subject: {action_config['subject']}")
    
    result = create_action(action_data)
    if result:
        print(f"  ✅ Email action created successfully!")
        print(f"     UUID: {result['uuid']}")
        print(f"     Name: {result['name']}")
        return result['uuid']
    
    return None


def test_webhook_action():
    """Test creating a webhook action"""
    print("\n🔗 Testing Webhook Action Creation")
    print("-" * 50)
    
    action_config = {
        "url": "https://webhook.site/unique-url-here",
        "method": "POST",
        "payload_data": {
            "source": "ppl-meta-platform",
            "event_category": "trigger_fired"
        }
    }
    
    action_data = {
        "name": "Test Webhook Notification",
        "description": "Sends webhook when trigger fires",
        "action_type": "webhook",
        "action_config": json.dumps(action_config),
        "is_active": True,
        "created_by": "test_script"
    }
    
    print(f"  Action Config:")
    print(f"    URL: {action_config['url']}")
    print(f"    Method: {action_config['method']}")
    
    result = create_action(action_data)
    if result:
        print(f"  ✅ Webhook action created successfully!")
        print(f"     UUID: {result['uuid']}")
        print(f"     Name: {result['name']}")
        return result['uuid']
    
    return None


def test_log_action():
    """Test creating an audit log action"""
    print("\n📋 Testing Audit Log Action Creation")
    print("-" * 50)
    
    action_config = {
        "severity": "info",
        "data": {
            "category": "trigger_events",
            "tags": ["test", "demo", "automated"],
            "environment": "development"
        }
    }
    
    action_data = {
        "name": "Test Audit Logger",
        "description": "Logs trigger events to Communications Service",
        "action_type": "log",
        "action_config": json.dumps(action_config),
        "is_active": True,
        "created_by": "test_script"
    }
    
    print(f"  Action Config:")
    print(f"    Severity: {action_config['severity']}")
    print(f"    Category: {action_config['data']['category']}")
    print(f"    Tags: {action_config['data']['tags']}")
    
    result = create_action(action_data)
    if result:
        print(f"  ✅ Audit log action created successfully!")
        print(f"     UUID: {result['uuid']}")
        print(f"     Name: {result['name']}")
        return result['uuid']
    
    return None


def list_actions():
    """List all created actions"""
    print("\n📋 Listing All Actions")
    print("-" * 50)
    
    url = f"{MEDIA_SERVICE_URL}/api/v1/user-actions/?page=1&page_size=50"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"  Total actions: {data['total']}")
        print(f"\n  Recent actions:")
        for action in data['actions'][:10]:
            print(f"    - {action['name']} ({action['action_type']}) - UUID: {action['uuid']}")
    
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Failed to list actions: {e}")


def query_communication_logs():
    """Query Communications Service for recent logs"""
    print("\n📊 Querying Communication Logs")
    print("-" * 50)
    
    url = f"{COMMUNICATIONS_SERVICE_URL}/api/v1/audit/logs?page=1&page_size=10"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('logs'):
            print(f"  Found {len(data['logs'])} recent logs:")
            for log in data['logs']:
                print(f"    - {log.get('type', 'unknown')} | {log.get('status', 'unknown')} | {log.get('created_at', 'N/A')}")
        else:
            print(f"  No logs found yet (this is normal for a fresh installation)")
    
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Failed to query logs: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"     Response: {e.response.text}")


def main():
    """Run all tests"""
    print("=" * 50)
    print("  Communications Service Integration Tests")
    print("=" * 50)
    print()
    
    # Check services
    if not check_services():
        print("❌ One or more services are not healthy. Please start them and try again.")
        sys.exit(1)
    
    # Create test actions
    created_uuids = []
    
    email_uuid = test_email_action()
    if email_uuid:
        created_uuids.append(("email", email_uuid))
    
    webhook_uuid = test_webhook_action()
    if webhook_uuid:
        created_uuids.append(("webhook", webhook_uuid))
    
    log_uuid = test_log_action()
    if log_uuid:
        created_uuids.append(("log", log_uuid))
    
    # List all actions
    list_actions()
    
    # Query communication logs
    query_communication_logs()
    
    # Summary
    print("\n" + "=" * 50)
    print("  Test Summary")
    print("=" * 50)
    print(f"  Actions created: {len(created_uuids)}")
    for action_type, uuid in created_uuids:
        print(f"    - {action_type}: {uuid}")
    
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("  1. Link these actions to triggers via the API")
    print("  2. Fire triggers to test actual communication delivery")
    print("  3. Check Communications Service logs at:")
    print(f"     {COMMUNICATIONS_SERVICE_URL}/api/v1/audit/logs")
    print()


if __name__ == "__main__":
    main()
