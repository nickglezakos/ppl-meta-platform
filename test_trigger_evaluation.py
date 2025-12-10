#!/usr/bin/env python3
"""
Test script for trigger evaluation endpoint.

Tests the /api/v1/triggers/evaluate endpoint with mock counter data.
"""

import requests
import json
from uuid import uuid4
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TRIGGERS_URL = f"{BASE_URL}/api/v1/triggers"

# Test data
CAMERA_UUID = str(uuid4())


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def create_test_trigger(name, person_count_op, person_count_val, 
                       age_op=None, age_val=None, gender=None,
                       time_span="any"):
    """Create a test trigger."""
    trigger_data = {
        "name": name,
        "person_count_operator": person_count_op,
        "person_count_value": person_count_val,
        "age_range_operator": age_op or "any",
        "age_range_value": age_val,
        "gender_filter": gender or "any",
        "time_span": time_span,
        "media_source_uuid": CAMERA_UUID,
        "media_source_name": "Test Camera",
        "action": "log",
        "is_active": True,
        "description": f"Test trigger: {name}"
    }
    
    response = requests.post(TRIGGERS_URL, json=trigger_data)
    if response.status_code == 201:
        trigger = response.json()
        print(f"✅ Created trigger: {name}")
        print(f"   UUID: {trigger['uuid']}")
        print(f"   Condition: {person_count_op} {person_count_val} persons")
        if age_op and age_op != "any":
            print(f"   Age filter: {age_op} {age_val}")
        if gender and gender != "any":
            print(f"   Gender filter: {gender}")
        return trigger
    else:
        print(f"❌ Failed to create trigger: {response.status_code}")
        print(f"   {response.text}")
        return None


def evaluate_counter_data(total_count, age_dist=None, gender_dist=None):
    """Send counter data for evaluation."""
    counter_data = {
        "camera_uuid": CAMERA_UUID,
        "total_count": total_count,
        "age_distribution": age_dist or {},
        "gender_distribution": gender_dist or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    evaluate_url = f"{TRIGGERS_URL}/evaluate"
    response = requests.post(evaluate_url, json=counter_data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Evaluation failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def cleanup_triggers():
    """Delete all test triggers."""
    # Get all triggers
    response = requests.get(TRIGGERS_URL)
    if response.status_code == 200:
        triggers = response.json().get("triggers", [])
        for trigger in triggers:
            if trigger["media_source_uuid"] == CAMERA_UUID:
                delete_url = f"{TRIGGERS_URL}/{trigger['uuid']}"
                requests.delete(delete_url)
        print(f"🧹 Cleaned up {len(triggers)} test triggers")


def main():
    """Run trigger evaluation tests."""
    print_section("Trigger Evaluation Test Suite")
    
    print(f"📍 Test Camera UUID: {CAMERA_UUID}")
    print(f"🌐 API Base URL: {BASE_URL}")
    
    # Clean up any existing test triggers
    print_section("Setup")
    cleanup_triggers()
    
    # Create test triggers
    print_section("Creating Test Triggers")
    
    # Trigger 1: High traffic alert (more than 20 people)
    trigger1 = create_test_trigger(
        name="High Traffic Alert",
        person_count_op="more_than",
        person_count_val="20"
    )
    
    # Trigger 2: Low traffic alert (less than 5 people)
    trigger2 = create_test_trigger(
        name="Low Traffic Alert",
        person_count_op="less_than",
        person_count_val="5"
    )
    
    # Trigger 3: Minors detected (any count, age less than 18)
    trigger3 = create_test_trigger(
        name="Minors Detected",
        person_count_op="more_than",
        person_count_val="0",
        age_op="less_than",
        age_val="18"
    )
    
    # Trigger 4: Senior activity (age more than 65)
    trigger4 = create_test_trigger(
        name="Senior Activity",
        person_count_op="more_than",
        person_count_val="0",
        age_op="more_than",
        age_val="65"
    )
    
    # Trigger 5: Gender-specific capacity (more than 15, male filter)
    trigger5 = create_test_trigger(
        name="Male Capacity Alert",
        person_count_op="more_than",
        person_count_val="15",
        gender="male"
    )
    
    # Test Scenario 1: High traffic (25 people)
    print_section("Test 1: High Traffic (25 people)")
    result = evaluate_counter_data(
        total_count=25,
        age_dist={"0-18": 3, "19-30": 10, "31-50": 8, "51-65": 3, "66+": 1},
        gender_dist={"male": 12, "female": 13}
    )
    
    if result:
        print(f"📊 Evaluation Summary:")
        print(f"   Total Count: {result['total_count']}")
        print(f"   Triggers Evaluated: {result['triggers_evaluated']}")
        print(f"   Triggers Passed: {result['triggers_passed']}")
        print(f"\n📋 Results:")
        for r in result['results']:
            status = "✅ PASSED" if r['passed'] else "❌ FAILED"
            print(f"   {status} - {r['trigger_name']}")
            print(f"      Reason: {r['reason']}")
    
    # Test Scenario 2: Low traffic (3 people)
    print_section("Test 2: Low Traffic (3 people)")
    result = evaluate_counter_data(
        total_count=3,
        age_dist={"19-30": 2, "31-50": 1},
        gender_dist={"male": 1, "female": 2}
    )
    
    if result:
        print(f"📊 Evaluation Summary:")
        print(f"   Total Count: {result['total_count']}")
        print(f"   Triggers Evaluated: {result['triggers_evaluated']}")
        print(f"   Triggers Passed: {result['triggers_passed']}")
        print(f"\n📋 Results:")
        for r in result['results']:
            status = "✅ PASSED" if r['passed'] else "❌ FAILED"
            print(f"   {status} - {r['trigger_name']}")
            print(f"      Reason: {r['reason']}")
    
    # Test Scenario 3: Medium traffic with minors (12 people, 4 minors)
    print_section("Test 3: Medium Traffic with Minors (12 people)")
    result = evaluate_counter_data(
        total_count=12,
        age_dist={"0-18": 4, "19-30": 5, "31-50": 3},
        gender_dist={"male": 6, "female": 6}
    )
    
    if result:
        print(f"📊 Evaluation Summary:")
        print(f"   Total Count: {result['total_count']}")
        print(f"   Triggers Evaluated: {result['triggers_evaluated']}")
        print(f"   Triggers Passed: {result['triggers_passed']}")
        print(f"\n📋 Results:")
        for r in result['results']:
            status = "✅ PASSED" if r['passed'] else "❌ FAILED"
            print(f"   {status} - {r['trigger_name']}")
            print(f"      Reason: {r['reason']}")
    
    # Cleanup
    print_section("Cleanup")
    cleanup_triggers()
    
    print_section("Test Complete")
    print("✅ All tests completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        cleanup_triggers()
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
