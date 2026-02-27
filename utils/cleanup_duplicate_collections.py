#!/usr/bin/env python3
"""
Clean up duplicate camera collections - keep only the oldest one.
"""

import requests
import json
from datetime import datetime

MEDIA_SERVICE_URL = "http://localhost:8000"
CAMERA_ID = "usb_camera_0"

# You'll need to provide your auth token
AUTH_TOKEN = input("Enter your auth token (from browser dev tools): ").strip()

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

def get_all_collections():
    """Get all collections for the camera."""
    print(f"🔍 Fetching all collections for {CAMERA_ID}...")
    
    # Search for collections with the camera name
    response = requests.get(
        f"{MEDIA_SERVICE_URL}/api/v1/media/search",
        params={
            "collection_id": CAMERA_ID,
            "page_size": 5000,  # Get all of them
            "order_by": "created_at",
            "order": "asc"  # Oldest first
        },
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch collections: {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    
    # Extract unique collections
    collections = {}
    for item in data.get("items", []):
        collection = item.get("collection")
        if collection:
            coll_id = collection.get("id")
            coll_name = collection.get("name", "")
            
            # Only process collections with the target name
            if CAMERA_ID in coll_name:
                if coll_id not in collections:
                    collections[coll_id] = collection
    
    print(f"📋 Found {len(collections)} unique collections matching '{CAMERA_ID}'")
    return list(collections.values())

def delete_collection(collection_uuid, collection_name):
    """Delete a single collection."""
    print(f"🗑️  Deleting collection: {collection_name} (UUID: {collection_uuid})")
    
    response = requests.delete(
        f"{MEDIA_SERVICE_URL}/api/v1/media/collections/{collection_uuid}",
        headers=headers
    )
    
    if response.status_code in [200, 204]:
        print(f"   ✅ Deleted successfully")
        return True
    else:
        print(f"   ❌ Failed to delete: {response.status_code} - {response.text}")
        return False

def main():
    print(f"🧹 Cleaning up duplicate collections for {CAMERA_ID}")
    print("=" * 60)
    
    # Get all collections
    collections = get_all_collections()
    
    if not collections:
        print("❌ No collections found")
        return
    
    # Sort by created_at to find oldest
    collections.sort(key=lambda x: x.get("created_at", ""))
    
    oldest = collections[0]
    duplicates = collections[1:]
    
    print(f"\n📌 Keeping OLDEST collection:")
    print(f"   Name: {oldest.get('name')}")
    print(f"   UUID: {oldest.get('uuid')}")
    print(f"   Created: {oldest.get('created_at')}")
    print(f"   ID: {oldest.get('id')}")
    
    print(f"\n🗑️  Will delete {len(duplicates)} duplicate collections")
    
    if duplicates:
        confirm = input(f"\n⚠️  Delete {len(duplicates)} collections? (yes/no): ").strip().lower()
        
        if confirm != "yes":
            print("❌ Cancelled")
            return
        
        print(f"\n🔄 Deleting duplicates...")
        deleted_count = 0
        failed_count = 0
        
        for collection in duplicates:
            success = delete_collection(
                collection.get("uuid"),
                collection.get("name")
            )
            
            if success:
                deleted_count += 1
            else:
                failed_count += 1
        
        print(f"\n✅ Cleanup complete!")
        print(f"   Deleted: {deleted_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Kept: 1 (oldest)")
    else:
        print("✅ No duplicates to delete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
