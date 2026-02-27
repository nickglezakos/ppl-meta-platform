#!/usr/bin/env python3
"""
Test script for Individual Groups API
Tests the complete API workflow for Phase 1 implementation.
"""

import asyncio
import json
from typing import Dict, Any

import httpx

# Configuration
BASE_URL = "http://localhost:8080/api/v1"  # Gateway
# BASE_URL = "http://localhost:8008/api/v1"  # Direct vmeta

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def print_info(msg: str):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_response(response: httpx.Response):
    """Pretty print response"""
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)


async def test_create_group(client: httpx.AsyncClient) -> str:
    """Test creating a group"""
    print_info("Test 1: Creating individual group...")
    
    payload = {
        "name": "Test VIP Customers",
        "description": "Test group for high-value customers",
        "visibility": "private",
        "tags": ["test", "vip", "automated"],
        "initial_member_ids": []
    }
    
    try:
        response = await client.post(
            f"{BASE_URL}/individual-groups",
            json=payload
        )
        
        if response.status_code == 201:
            data = response.json()
            group_id = data["group"]["id"]
            print_success(f"Group created: {group_id}")
            print_response(response)
            return group_id
        else:
            print_error(f"Failed to create group: {response.status_code}")
            print_response(response)
            return None
            
    except Exception as e:
        print_error(f"Error: {e}")
        return None


async def test_list_groups(client: httpx.AsyncClient):
    """Test listing groups"""
    print_info("Test 2: Listing all groups...")
    
    try:
        response = await client.get(f"{BASE_URL}/individual-groups")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Found {data['total']} groups")
            print(f"Groups: {[g['name'] for g in data['groups']]}")
        else:
            print_error(f"Failed to list groups: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_get_group(client: httpx.AsyncClient, group_id: str):
    """Test getting a single group"""
    print_info(f"Test 3: Getting group {group_id}...")
    
    try:
        response = await client.get(f"{BASE_URL}/individual-groups/{group_id}")
        
        if response.status_code == 200:
            print_success(f"Retrieved group")
            print_response(response)
        else:
            print_error(f"Failed to get group: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_update_group(client: httpx.AsyncClient, group_id: str):
    """Test updating a group"""
    print_info(f"Test 4: Updating group {group_id}...")
    
    payload = {
        "name": "Updated Test VIP Customers",
        "description": "Updated description for testing",
        "tags": ["test", "vip", "updated"]
    }
    
    try:
        response = await client.patch(
            f"{BASE_URL}/individual-groups/{group_id}",
            json=payload
        )
        
        if response.status_code == 200:
            print_success(f"Group updated")
            print_response(response)
        else:
            print_error(f"Failed to update group: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_add_members(client: httpx.AsyncClient, group_id: str):
    """Test adding members to a group"""
    print_info(f"Test 5: Adding members to group {group_id}...")
    
    # These are test IDs - in production they would be actual individual IDs
    payload = {
        "individual_ids": ["test_ind_001", "test_ind_002", "test_ind_003"],
        "notes": "Added via automated test"
    }
    
    try:
        response = await client.post(
            f"{BASE_URL}/individual-groups/{group_id}/members",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Added {data['added_count']} members (skipped {data['skipped_count']})")
            print_response(response)
        else:
            print_error(f"Failed to add members: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_get_members(client: httpx.AsyncClient, group_id: str):
    """Test getting group members"""
    print_info(f"Test 6: Getting members of group {group_id}...")
    
    try:
        response = await client.get(
            f"{BASE_URL}/individual-groups/{group_id}/members",
            params={"limit": 10, "skip": 0}
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Found {data['total']} members")
            print_response(response)
        else:
            print_error(f"Failed to get members: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_remove_members(client: httpx.AsyncClient, group_id: str):
    """Test removing members from a group"""
    print_info(f"Test 7: Removing members from group {group_id}...")
    
    payload = {
        "individual_ids": ["test_ind_001"]
    }
    
    try:
        response = await client.delete(
            f"{BASE_URL}/individual-groups/{group_id}/members",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Removed {data['removed_count']} members")
            print_response(response)
        else:
            print_error(f"Failed to remove members: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_search_groups(client: httpx.AsyncClient):
    """Test searching groups"""
    print_info("Test 8: Searching groups...")
    
    try:
        response = await client.get(
            f"{BASE_URL}/individual-groups",
            params={"search": "VIP", "limit": 10}
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Found {data['total']} matching groups")
            print(f"Groups: {[g['name'] for g in data['groups']]}")
        else:
            print_error(f"Failed to search groups: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_delete_group(client: httpx.AsyncClient, group_id: str):
    """Test deleting a group"""
    print_info(f"Test 9: Deleting group {group_id}...")
    
    try:
        response = await client.delete(
            f"{BASE_URL}/individual-groups/{group_id}",
            params={"remove_members": True}
        )
        
        if response.status_code == 204:
            print_success(f"Group deleted")
        else:
            print_error(f"Failed to delete group: {response.status_code}")
            print_response(response)
            
    except Exception as e:
        print_error(f"Error: {e}")


async def test_thumbnail_endpoints(client: httpx.AsyncClient):
    """Test thumbnail endpoints"""
    print_info("Test 10: Testing thumbnail endpoints...")
    
    individual_id = "test_ind_001"
    
    # Test get thumbnail (should return fallback)
    try:
        response = await client.get(
            f"{BASE_URL}/individuals/{individual_id}/thumbnail",
            params={"size": "medium"}
        )
        
        if response.status_code == 200:
            print_success(f"Got thumbnail (fallback): {len(response.content)} bytes")
        else:
            print_error(f"Failed to get thumbnail: {response.status_code}")
            
    except Exception as e:
        print_error(f"Error: {e}")
    
    # Test get thumbnail URL
    try:
        response = await client.get(
            f"{BASE_URL}/individuals/{individual_id}/thumbnail/url"
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Thumbnail URL retrieved")
            print_response(response)
        else:
            print_error(f"Failed to get thumbnail URL: {response.status_code}")
            
    except Exception as e:
        print_error(f"Error: {e}")


async def run_all_tests():
    """Run all tests in sequence"""
    print(f"\n{BLUE}{'='*60}")
    print("Individual Groups API Test Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"{'='*60}{RESET}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test health endpoint first
        try:
            print_info("Checking service health...")
            if "8080" in BASE_URL:
                health_response = await client.get("http://localhost:8080/health")
            else:
                health_response = await client.get("http://localhost:8008/health")
            
            if health_response.status_code == 200:
                print_success("Service is healthy")
            else:
                print_warning("Service health check returned non-200")
        except Exception as e:
            print_error(f"Cannot connect to service: {e}")
            print_error("Please ensure vmeta service is running")
            return
        
        print()
        
        # Run test workflow
        group_id = await test_create_group(client)
        
        if not group_id:
            print_error("Cannot continue tests without group ID")
            return
        
        print()
        await test_list_groups(client)
        
        print()
        await test_get_group(client, group_id)
        
        print()
        await test_update_group(client, group_id)
        
        print()
        await test_add_members(client, group_id)
        
        print()
        await test_get_members(client, group_id)
        
        print()
        await test_remove_members(client, group_id)
        
        print()
        await test_search_groups(client)
        
        print()
        await test_thumbnail_endpoints(client)
        
        print()
        await test_delete_group(client, group_id)
        
        print(f"\n{BLUE}{'='*60}")
        print("Test Suite Complete!")
        print(f"{'='*60}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
