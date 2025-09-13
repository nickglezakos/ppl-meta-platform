"""
Backfill script to add camera_device_id to existing collections.
This script analyzes collection names to infer their corresponding camera device IDs.
"""

import asyncio
import re
import sys

import aiohttp


async def backfill_camera_device_ids():
    """Backfill existing collections with camera device IDs based on names."""

    # Get fresh auth token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3Nzg2MTYyfQ.1aib1xFIjz67BASPH3xJkJfh5018GGZ2cq8gKsD8c-I"
    headers = {"Authorization": f"Bearer {token}"}

    # Mapping rules to extract device IDs from collection names
    device_id_patterns = [
        (r"USB Camera 0 Collection", "usb_camera_0"),
        (r"usb_camera_0 Collection", "usb_camera_0"),
        (r"mcam-([a-zA-Z0-9-]+) Collection", lambda m: f"mobile_{m.group(1)}"),
        (r"test-mobile-camera Collection", "test-mobile-camera"),
        (r"Mobile Camera .* Collection", "mobile_camera"),
        (r"Nick desk Collection", "nick_desk"),
        (r"([a-zA-Z0-9_-]+) Collection", lambda m: m.group(1)),  # Generic pattern
    ]

    async with aiohttp.ClientSession() as session:
        print("🔍 Fetching existing collections...")

        # Get all collections
        async with session.get(
            "http://localhost:8000/api/v1/media/collections", headers=headers
        ) as response:
            if response.status != 200:
                print(f"❌ Failed to fetch collections: {response.status}")
                return

            collections = await response.json()
            print(f"📋 Found {len(collections)} collections to process")

        updates_made = 0

        for collection in collections:
            collection_name = collection.get("name", "")
            collection_id = collection.get("id")
            collection_uuid = collection.get("uuid")

            # Skip if already has camera_device_id
            if collection.get("camera_device_id"):
                print(
                    f"⏭️ '{collection_name}' already has camera_device_id: {collection['camera_device_id']}"
                )
                continue

            # Try to match against patterns
            device_id = None
            for pattern, extraction in device_id_patterns:
                if callable(extraction):
                    match = re.search(pattern, collection_name)
                    if match:
                        device_id = extraction(match)
                        break
                else:
                    if re.search(pattern, collection_name):
                        device_id = extraction
                        break

            if device_id:
                print(
                    f"🔧 Updating '{collection_name}' (ID: {collection_id}) with device_id: {device_id}"
                )

                # Update collection via PATCH API endpoint
                update_data = {"camera_device_id": device_id}

                async with session.patch(
                    f"http://localhost:8000/api/v1/media/collections/{collection_uuid}",
                    headers={**headers, "Content-Type": "application/json"},
                    json=update_data,
                    params={"user_id": "4cf362b1-3e05-4e85-81c7-c08a98c7e41b"},
                ) as update_response:
                    if update_response.status == 200:
                        print(f"✅ Successfully updated collection {collection_id}")
                        updates_made += 1
                    else:
                        error_text = await update_response.text()
                        print(
                            f"❌ Failed to update collection {collection_id}: {update_response.status} - {error_text}"
                        )

            else:
                print(f"⚠️ Could not determine device_id for '{collection_name}'")

        print(f"✅ Backfill complete! {updates_made} collections would be updated.")
        print(
            "Note: Actual database updates need to be implemented via API or direct DB access."
        )


if __name__ == "__main__":
    asyncio.run(backfill_camera_device_ids())
