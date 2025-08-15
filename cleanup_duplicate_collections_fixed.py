#!/usr/bin/env python3
"""
Clean up duplicate collections using the media service API.
This script will keep the earliest created collection for each camera name.
"""

import json
from datetime import datetime

import requests


def login():
    """Get authentication token."""
    login_url = "http://localhost:8001/api/v1/users/login"
    login_data = {"username": "fresh.user@example.com", "password": "NewPassword234!"}

    response = requests.post(
        login_url,
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.text}")
        return None


def get_collections(token):
    """Get all collections."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        "http://localhost:8080/api/v1/media/collections", headers=headers
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get collections: {response.text}")
        return []


def delete_collection_via_node(token, collection_id, user_id="7"):
    """Try to delete collection via node service."""
    headers = {"Authorization": f"Bearer {token}"}

    # Try different approaches
    endpoints_to_try = [
        f"http://localhost:8001/api/v1/collections/{collection_id}",
        f"http://localhost:8001/api/v1/media/collections/{collection_id}",
        f"http://localhost:8080/api/v1/media/collections/{collection_id}",
    ]

    for url in endpoints_to_try:
        try:
            response = requests.delete(url, headers=headers)
            print(f"DELETE {url}: {response.status_code} - {response.text}")
            if response.status_code in [200, 204]:
                return True
        except Exception as e:
            print(f"Error with {url}: {e}")

    return False


def cleanup_duplicates():
    """Main cleanup function."""
    print("🧹 Cleaning up duplicate collections...")

    # Get authentication token
    token = login()
    if not token:
        print("❌ Failed to authenticate")
        return

    print("✅ Authentication successful")

    # Get all collections
    collections = get_collections(token)
    if not collections:
        print("❌ Failed to get collections")
        return

    print(f"📋 Found {len(collections)} collections")

    # Group collections by name
    collections_by_name = {}
    for collection in collections:
        name = collection["name"]
        if name not in collections_by_name:
            collections_by_name[name] = []
        collections_by_name[name].append(collection)

    # Find duplicates and decide which to keep/delete
    to_delete = []
    for name, cols in collections_by_name.items():
        if len(cols) > 1:
            # Sort by creation date to keep the earliest
            cols.sort(key=lambda x: x["created_at"])
            keep = cols[0]
            duplicates = cols[1:]

            print(f"\n🔍 Found {len(duplicates)} duplicates for '{name}':")
            print(f"   ✅ Keeping: ID {keep['id']} (created: {keep['created_at']})")

            for dup in duplicates:
                print(
                    f"   ❌ Will delete: ID {dup['id']} (created: {dup['created_at']})"
                )
                to_delete.append(dup)

    # Attempt to delete duplicates
    if not to_delete:
        print("✅ No duplicates found!")
        return

    print(f"\n🗑️  Attempting to delete {len(to_delete)} duplicate collections...")

    deleted_count = 0
    for collection in to_delete:
        collection_id = collection["id"]
        name = collection["name"]

        print(f"\n🔄 Attempting to delete '{name}' (ID: {collection_id})...")

        if delete_collection_via_node(token, collection_id):
            print(f"✅ Successfully deleted collection {collection_id}")
            deleted_count += 1
        else:
            print(f"❌ Failed to delete collection {collection_id}")

    print(f"\n📊 Summary:")
    print(f"   🎯 Collections to delete: {len(to_delete)}")
    print(f"   ✅ Successfully deleted: {deleted_count}")
    print(f"   ❌ Failed to delete: {len(to_delete) - deleted_count}")

    # Verify cleanup
    if deleted_count > 0:
        print("\n🔍 Verifying cleanup...")
        final_collections = get_collections(token)
        print(f"📋 Collections remaining: {len(final_collections)}")

        # Show final state
        final_by_name = {}
        for collection in final_collections:
            name = collection["name"]
            final_by_name[name] = final_by_name.get(name, 0) + 1

        print("📋 Final collection counts by name:")
        for name, count in final_by_name.items():
            status = "✅" if count == 1 else "⚠️"
            print(f"   {status} {name}: {count}")


if __name__ == "__main__":
    cleanup_duplicates()
