#!/usr/bin/env python3
"""
Debug script to test collection filtering logic
"""
import json

import requests

# Configuration
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU1MTc0NjkzfQ.9zG8KNsfuMj-pfaHILUE3Z8Lh3FfQO18Q0luhbM6eyg"
BASE_URL = "http://localhost:8080"
USER_ID = "4cf362b1-3e05-4e85-81c7-c08a98c7e41b"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def test_collection_filtering():
    print("🔍 Testing Collection Filtering Logic")
    print("=" * 50)

    # 1. Get all collections
    print("\n1. Getting all collections...")
    response = requests.get(
        f"{BASE_URL}/api/v1/media/collections?user_id={USER_ID}", headers=headers
    )
    collections = response.json()
    print(f"Found {len(collections)} collections:")
    for collection in collections:
        print(
            f"  - {collection['name']} (ID: {collection['id']}, UUID: {collection['uuid']})"
        )

    # 2. Test with no filters
    print("\n2. Testing search with no collection filter...")
    response = requests.get(f"{BASE_URL}/api/v1/media/search", headers=headers)
    all_items = response.json()
    print(f"Total items without filter: {len(all_items)}")

    # 3. Test with valid collection UUID
    if collections:
        test_collection = collections[0]
        print(f"\n3. Testing with valid collection UUID: {test_collection['uuid']}")
        response = requests.get(
            f"{BASE_URL}/api/v1/media/search?collection_ids={test_collection['uuid']}",
            headers=headers,
        )
        filtered_items = response.json()
        print(f"Items with collection filter: {len(filtered_items)}")

        # 4. Check what's actually in this collection
        print(f"\n4. Checking items in collection {test_collection['name']}...")
        response = requests.get(
            f"{BASE_URL}/api/v1/media/collections/{test_collection['uuid']}/items?user_id={USER_ID}",
            headers=headers,
        )
        collection_items = response.json()
        print(f"Items directly in collection: {len(collection_items)}")

        if len(filtered_items) != len(collection_items):
            print(
                "❌ MISMATCH: Search filter and direct collection query return different counts!"
            )
        else:
            print("✅ Search filter matches direct collection query")

    # 5. Test with invalid collection UUID
    print("\n5. Testing with invalid collection UUID...")
    response = requests.get(
        f"{BASE_URL}/api/v1/media/search?collection_ids=invalid-uuid-12345",
        headers=headers,
    )
    invalid_items = response.json()
    print(f"Items with invalid collection UUID: {len(invalid_items)}")

    if len(invalid_items) > 0:
        print("❌ PROBLEM: Invalid collection UUID should return 0 items!")
    else:
        print("✅ Invalid collection UUID correctly returns 0 items")

    # 6. Test with multiple collection UUIDs
    if len(collections) >= 2:
        print("\n6. Testing with multiple collection UUIDs...")
        collection_uuids = [collections[0]["uuid"], collections[1]["uuid"]]
        response = requests.get(
            f"{BASE_URL}/api/v1/media/search?collection_ids={','.join(collection_uuids)}",
            headers=headers,
        )
        multi_items = response.json()
        print(f"Items with multiple collection filter: {len(multi_items)}")

        # Check individual collections
        total_expected = 0
        for uuid in collection_uuids:
            response = requests.get(
                f"{BASE_URL}/api/v1/media/collections/{uuid}/items?user_id={USER_ID}",
                headers=headers,
            )
            items = response.json()
            total_expected += len(items)
            print(f"  - Collection {uuid}: {len(items)} items")

        print(f"Expected total (sum): {total_expected}, Actual: {len(multi_items)}")


if __name__ == "__main__":
    test_collection_filtering()
