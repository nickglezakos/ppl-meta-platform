#!/usr/bin/env python3
"""
Test script for monitoring dashboard API endpoints.
Run this after starting the orchestrator service.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8002"

def print_section(title):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_summary_endpoint():
    """Test /api/v1/monitoring/summary endpoint."""
    print_section("Testing Monitoring Summary Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/monitoring/summary", timeout=5)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ From Cache: {data.get('from_cache', False)}")
        print(f"\n📊 Low-Level Workflows:")
        for key, value in data.get('low_level_workflows', {}).items():
            print(f"   • {key}: {value}")
        
        print(f"\n📊 High-Level Workflows:")
        for key, value in data.get('high_level_workflows', {}).items():
            print(f"   • {key}: {value}")
        
        print(f"\n🏥 System Health:")
        health = data.get('system_health', {})
        print(f"   • Status: {health.get('status')} ({health.get('color')})")
        print(f"   • Message: {health.get('message')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_low_level_workflows():
    """Test /api/v1/monitoring/workflows/low-level endpoint."""
    print_section("Testing Low-Level Workflows Pagination")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/monitoring/workflows/low-level",
            params={"page": 1, "limit": 5},
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"\n📄 Pagination Info:")
        pagination = data.get('pagination', {})
        print(f"   • Page: {pagination.get('page')}")
        print(f"   • Limit: {pagination.get('limit')}")
        print(f"   • Total: {pagination.get('total')}")
        print(f"   • Pages: {pagination.get('pages')}")
        
        print(f"\n📋 Workflows (showing {len(data.get('workflows', []))}):")
        for workflow in data.get('workflows', [])[:3]:
            print(f"   • {workflow.get('workflow_id')}: {workflow.get('status')}")
            print(f"     Type: {workflow.get('workflow_type')}")
            print(f"     Created: {workflow.get('created_at')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_method_lifecycles():
    """Test /api/v1/monitoring/workflows/methods endpoint."""
    print_section("Testing Method Lifecycles Pagination")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/monitoring/workflows/methods",
            params={"page": 1, "limit": 5},
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"\n📄 Pagination Info:")
        pagination = data.get('pagination', {})
        print(f"   • Page: {pagination.get('page')}")
        print(f"   • Total: {pagination.get('total')}")
        
        print(f"\n🔬 Methods (showing {len(data.get('methods', []))}):")
        for method in data.get('methods', [])[:3]:
            print(f"   • {method.get('method')}: {method.get('status')}")
            print(f"     Media: {method.get('media_id')}")
            if method.get('processing_time_seconds'):
                print(f"     Time: {method.get('processing_time_seconds')}s")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_cache_operations():
    """Test cache operations."""
    print_section("Testing Cache Operations")
    
    # Test 1: Get summary (should cache)
    print("1️⃣ First request (should cache)...")
    response1 = requests.get(f"{BASE_URL}/api/v1/monitoring/summary")
    data1 = response1.json()
    print(f"   From cache: {data1.get('from_cache')}")
    
    # Test 2: Get summary again (should be cached)
    print("\n2️⃣ Second request (should be from cache)...")
    response2 = requests.get(f"{BASE_URL}/api/v1/monitoring/summary")
    data2 = response2.json()
    print(f"   From cache: {data2.get('from_cache')}")
    
    # Test 3: Clear cache
    print("\n3️⃣ Clearing cache...")
    response3 = requests.post(f"{BASE_URL}/api/v1/monitoring/cache/clear")
    print(f"   {response3.json().get('message')}")
    
    # Test 4: Get summary after clear (should not be cached)
    print("\n4️⃣ Request after clear (should not be cached)...")
    response4 = requests.get(f"{BASE_URL}/api/v1/monitoring/summary")
    data4 = response4.json()
    print(f"   From cache: {data4.get('from_cache')}")
    
    return True

def main():
    """Run all tests."""
    print(f"\n{'*'*60}")
    print(f"  MONITORING DASHBOARD API TESTS")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'*'*60}")
    
    results = []
    
    # Run tests
    results.append(("Summary Endpoint", test_summary_endpoint()))
    results.append(("Low-Level Workflows", test_low_level_workflows()))
    results.append(("Method Lifecycles", test_method_lifecycles()))
    results.append(("Cache Operations", test_cache_operations()))
    
    # Print summary
    print_section("Test Results Summary")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n{'='*60}")
    print(f"  Total: {passed_count}/{total_count} tests passed")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
