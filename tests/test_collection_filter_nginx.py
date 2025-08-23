#!/usr/bin/env python3

import json

import requests

# Authentication token from login
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU1MTc2MDQ0fQ._YdzH_fjIgUTiBl1Thph7njQeC1wy7wt0kiRUFeV9SI"

# Headers for authenticated requests
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Base URL through nginx proxy
base_url = "http://localhost"


def test_collection_filtering_via_nginx():
    print("🧪 Testing Collection Filtering via Nginx Proxy")
    print("=" * 60)

    # Test 1: Get all collections first
    print("\n1️⃣ Getting all collections...")
    collections_response = requests.get(
        f"{base_url}/api/v1/media/collections", headers=headers
    )
    if collections_response.status_code == 200:
        collections = collections_response.json()
        print(f"   Found {len(collections)} collections")
        for i, collection in enumerate(collections[:3]):  # Show first 3
            # Show both ID and UUID if available
            collection_id = collection.get("id", "N/A")
            collection_uuid = collection.get("uuid", "N/A")
            print(
                f"   Collection {i+1}: {collection['name']} (ID: {collection_id}, UUID: {collection_uuid})"
            )
    else:
        print(f"   ❌ Failed to get collections: {collections_response.status_code}")
        return

    # Test 2: Get all media without filter
    print("\n2️⃣ Getting all media (no filter)...")
    all_media_response = requests.get(
        f"{base_url}/api/v1/media/search", headers=headers
    )
    if all_media_response.status_code == 200:
        all_media = all_media_response.json()
        # Handle both list and dict response formats
        if isinstance(all_media, list):
            total_count = len(all_media)
        else:
            total_count = len(all_media.get("items", []))
        print(f"   Total media items: {total_count}")
    else:
        print(f"   ❌ Failed to get all media: {all_media_response.status_code}")
        return

    # Test 3: Filter by single collection
    if collections:
        # Use UUID if available, otherwise use ID
        test_collection = collections[0]
        test_collection_id = test_collection.get("uuid") or test_collection.get("id")
        print(f"\n3️⃣ Testing single collection filter (ID: {test_collection_id})...")

        filtered_response = requests.get(
            f"{base_url}/api/v1/media/search",
            headers=headers,
            params={"collection_ids": str(test_collection_id)},
        )

        if filtered_response.status_code == 200:
            filtered_media = filtered_response.json()
            # Handle both list and dict response formats
            if isinstance(filtered_media, list):
                filtered_count = len(filtered_media)
            else:
                filtered_count = len(filtered_media.get("items", []))
            print(f"   ✅ Filtered media items: {filtered_count}")

            # Compare with direct collection query
            direct_response = requests.get(
                f"{base_url}/api/v1/media/collections/{test_collection_id}/items",
                headers=headers,
            )
            if direct_response.status_code == 200:
                direct_media = direct_response.json()
                # Handle both list and dict response formats
                if isinstance(direct_media, list):
                    direct_count = len(direct_media)
                else:
                    direct_count = len(direct_media.get("items", []))
                print(f"   ✅ Direct collection query: {direct_count}")

                if filtered_count == direct_count:
                    print("   🎉 MATCH! Filtering works correctly via nginx!")
                else:
                    print(
                        f"   ❌ MISMATCH! Filter: {filtered_count}, Direct: {direct_count}"
                    )
            else:
                print(
                    f"   ❌ Direct collection query failed: {direct_response.status_code}"
                )
        else:
            print(f"   ❌ Filtered search failed: {filtered_response.status_code}")

    # Test 4: Multiple collections
    if len(collections) >= 2:
        # Use UUIDs if available, otherwise use IDs
        collection_ids = []
        for collection in collections[:2]:
            coll_id = collection.get("uuid") or collection.get("id")
            collection_ids.append(str(coll_id))
        print(f"\n4️⃣ Testing multiple collection filter...")
        print(f"   Collections: {collection_ids}")

        multi_response = requests.get(
            f"{base_url}/api/v1/media/search",
            headers=headers,
            params={"collection_ids": ",".join(collection_ids)},
        )

        if multi_response.status_code == 200:
            multi_media = multi_response.json()
            # Handle both list and dict response formats
            if isinstance(multi_media, list):
                multi_count = len(multi_media)
            else:
                multi_count = len(multi_media.get("items", []))
            print(f"   ✅ Multi-collection filter: {multi_count} items")

            # Verify it's less than or equal to total
            if multi_count <= total_count:
                print("   ✅ Count is reasonable (≤ total)")
            else:
                print(f"   ❌ Count exceeds total! {multi_count} > {total_count}")
        else:
            print(f"   ❌ Multi-collection search failed: {multi_response.status_code}")


if __name__ == "__main__":
    test_collection_filtering_via_nginx()
