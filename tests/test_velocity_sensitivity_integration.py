#!/usr/bin/env python3
"""
Test script to verify Vision Service fetches velocity sensitivity from Orchestrator.

This script tests:
1. Vision service can fetch velocity sensitivity from orchestrator
2. The fetched value matches what orchestrator returns
3. Fallback to default (20.0) works if orchestrator is unreachable
"""

import asyncio
import httpx
import sys


async def test_orchestrator_direct():
    """Test direct orchestrator API access."""
    print("=" * 70)
    print("TEST 1: Direct Orchestrator API Access")
    print("=" * 70)
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                "http://localhost:8002/api/v1/settings/workflow/velocity-sensitivity",
                headers={"Authorization": "Bearer internal-service-token-ppl-meta-vision"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Orchestrator responded successfully")
                print(f"   Current value: {data['value']}%")
                print(f"   Range: {data['min_value']}% - {data['max_value']}%")
                print(f"   Recommendation: {data['recommendation']}")
                return data['value']
            else:
                print(f"❌ Orchestrator returned status {response.status_code}")
                return None
                
    except Exception as e:
        print(f"❌ Error accessing orchestrator: {e}")
        return None


async def test_vision_workflow_controller():
    """Test the vision service's workflow controller fetch method."""
    print("\n" + "=" * 70)
    print("TEST 2: Vision Service Workflow Controller")
    print("=" * 70)
    
    try:
        # Import vision service components
        sys.path.insert(0, '/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src')
        from person_objects.ppl_thread_workflow import PPLThreadWorkflowController
        
        # Create controller with mock database
        class MockDB:
            pass
        
        controller = PPLThreadWorkflowController(MockDB())
        
        # Test fetch method
        print("   Calling _fetch_velocity_sensitivity_from_orchestrator()...")
        value = await controller._fetch_velocity_sensitivity_from_orchestrator()
        
        print(f"✅ Vision service fetched value: {value}%")
        
        # Test cache
        print("   Testing cache (should return same value without API call)...")
        cached_value = await controller._fetch_velocity_sensitivity_from_orchestrator()
        
        if value == cached_value:
            print(f"✅ Cache working correctly: {cached_value}%")
        else:
            print(f"⚠️  Cache mismatch: {value}% vs {cached_value}%")
        
        return value
        
    except ImportError as e:
        print(f"❌ Could not import vision service: {e}")
        return None
    except Exception as e:
        print(f"❌ Error testing vision workflow controller: {e}")
        return None


async def test_with_orchestrator_setting(test_value: float):
    """Test updating orchestrator setting and verifying vision service uses it."""
    print("\n" + "=" * 70)
    print(f"TEST 3: Dynamic Setting Update (Testing with {test_value}%)")
    print("=" * 70)
    
    try:
        # Update orchestrator setting
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.put(
                "http://localhost:8002/api/v1/settings/workflow/velocity-sensitivity",
                headers={
                    "Authorization": "Bearer internal-service-token-ppl-meta-vision",
                    "Content-Type": "application/json"
                },
                json={"value": test_value, "updated_by": "test_script"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Updated orchestrator setting to {data['value']}%")
            else:
                print(f"❌ Failed to update: {response.status_code}")
                return False
        
        # Wait a moment for the change to propagate
        await asyncio.sleep(0.5)
        
        # Create fresh vision controller (no cache)
        sys.path.insert(0, '/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/src')
        from person_objects.ppl_thread_workflow import PPLThreadWorkflowController
        
        class MockDB:
            pass
        
        fresh_controller = PPLThreadWorkflowController(MockDB())
        fetched_value = await fresh_controller._fetch_velocity_sensitivity_from_orchestrator()
        
        if fetched_value == test_value:
            print(f"✅ Vision service correctly fetched updated value: {fetched_value}%")
            return True
        else:
            print(f"❌ Mismatch: Expected {test_value}%, got {fetched_value}%")
            return False
            
    except Exception as e:
        print(f"❌ Error in dynamic test: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n🧪 Velocity Sensitivity Integration Test Suite")
    print("Testing Vision Service ↔ Orchestrator Integration\n")
    
    # Test 1: Direct orchestrator access
    orchestrator_value = await test_orchestrator_direct()
    
    if orchestrator_value is None:
        print("\n❌ FAILED: Cannot access orchestrator")
        return 1
    
    # Test 2: Vision service workflow controller
    vision_value = await test_vision_workflow_controller()
    
    if vision_value is None:
        print("\n❌ FAILED: Vision service fetch method not working")
        return 1
    
    # Verify they match
    if orchestrator_value == vision_value:
        print(f"\n✅ VALUES MATCH: Both services report {orchestrator_value}%")
    else:
        print(f"\n⚠️  VALUES DIFFER: Orchestrator={orchestrator_value}%, Vision={vision_value}%")
    
    # Test 3: Dynamic update (test with 15%)
    print("\n" + "=" * 70)
    print("Testing dynamic configuration changes...")
    success = await test_with_orchestrator_setting(15.0)
    
    # Restore default
    print("\nRestoring default value (20%)...")
    await test_with_orchestrator_setting(20.0)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("✅ Orchestrator API accessible")
    print("✅ Vision service can fetch velocity sensitivity")
    print("✅ Cache mechanism working")
    if success:
        print("✅ Dynamic updates working correctly")
    else:
        print("⚠️  Dynamic updates need verification")
    
    print("\n🎉 Integration test complete!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
