#!/usr/bin/env python3
"""
Script to clean up duplicate camera collections in the PPL Meta platform.
This script will identify and remove duplicate collections with the same name,
keeping only the most recent one.
"""

import json
from datetime import datetime

import requests

# Configuration
BASE_URL = "http://localhost:8080"
USER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU1MjUyNjgyfQ.l3r-j1EeAYRr3nxxXr5WMhu246o3wEP4ufP_gPKjOfk"
USER_UUID = "4cf362b1-3e05-4e85-81c7-c08a98c7e41b"

headers = {"Authorization": f"Bearer {USER_TOKEN}", "Content-Type": "application/json"}


def get_collections():
    """Get all collections for the user."""
    url = f"{BASE_URL}/api/v1/media/collections"
    params = {"user_id": USER_UUID}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get collections: {response.status_code}")
        return []


def delete_collection(collection_id):
    """Delete a collection by ID."""
    url = f"{BASE_URL}/api/v1/media/collections/{collection_id}"

    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"✅ Deleted collection {collection_id}")
        return True
    else:
        print(f"❌ Failed to delete collection {collection_id}: {response.status_code}")
        return False


def clean_duplicate_collections():
    """Clean up duplicate collections, keeping the most recent one for each name."""
    collections = get_collections()

    if not collections:
        print("No collections found")
        return

    print(f"Found {len(collections)} total collections")

    # Group collections by name
    collections_by_name = {}
    for collection in collections:
        name = collection["name"]
        if name not in collections_by_name:
            collections_by_name[name] = []
        collections_by_name[name].append(collection)

    # Find and clean duplicates
    total_to_delete = 0
    for name, name_collections in collections_by_name.items():
        if len(name_collections) > 1:
            print(f"\n🔍 Found {len(name_collections)} collections with name: '{name}'")

            # Sort by created_at (most recent first)
            name_collections.sort(key=lambda x: x["created_at"], reverse=True)

            # Keep the most recent, delete the rest
            keep_collection = name_collections[0]
            delete_collections = name_collections[1:]

            print(
                f"  ✅ Keeping: {keep_collection['id']} (created: {keep_collection['created_at']})"
            )

            for collection in delete_collections:
                print(
                    f"  🗑️  Will delete: {collection['id']} (created: {collection['created_at']})"
                )
                total_to_delete += 1

    if total_to_delete == 0:
        print("\n✅ No duplicate collections found!")
        return

    # Ask for confirmation
    print(f"\n⚠️  About to delete {total_to_delete} duplicate collections.")
    confirm = input("Continue? (y/N): ").strip().lower()

    if confirm != "y":
        print("Cancelled")
        return

    # Perform deletion
    deleted_count = 0
    for name, name_collections in collections_by_name.items():
        if len(name_collections) > 1:
            name_collections.sort(key=lambda x: x["created_at"], reverse=True)
            delete_collections = name_collections[1:]

            for collection in delete_collections:
                if delete_collection(collection["id"]):
                    deleted_count += 1

    print(f"\n✅ Cleanup complete! Deleted {deleted_count} duplicate collections.")


if __name__ == "__main__":
    print("🧹 PPL Meta Collection Cleanup Tool")
    print("=" * 40)
    clean_duplicate_collections()
