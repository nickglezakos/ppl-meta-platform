#!/usr/bin/env python3
"""
Clean up duplicate mobile camera registrations

This script removes duplicate mobile camera registrations, keeping only the latest one
for each unique device (based on the actual device identifier without timestamps).
"""

import json
import sys
from typing import Dict, List

import requests

# Configuration
CAMERAS_SERVICE_URL = "http://localhost:8005"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU2ODU3NjIxfQ.RJIaFDBuOPFL0XqQwIFY7UJnHO0SMz_uXxwM73nKwAw"


def get_auth_headers():
    """Get authentication headers for API requests"""
    return {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_mobile_cameras() -> List[Dict]:
    """Get all mobile cameras from the service"""
    try:
        response = requests.get(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/mobile",
            headers=get_auth_headers(),
            timeout=10,
        )

        if response.status_code == 200:
            cameras = response.json()
            print(f"📱 Retrieved {len(cameras)} mobile cameras")
            return cameras
        else:
            print(f"❌ Failed to get mobile cameras: {response.status_code}")
            print(f"Response: {response.text}")
            return []

    except Exception as e:
        print(f"❌ Error getting mobile cameras: {e}")
        return []


def extract_base_device_id(device_id: str) -> str:
    """Extract the base device ID without mobile_ prefix and timestamp suffix"""
    # Remove mobile_ prefix if present
    if device_id.startswith("mobile_"):
        device_id = device_id[7:]  # Remove 'mobile_' (7 characters)

    # Remove timestamp suffix (last underscore and numbers)
    parts = device_id.split("_")
    if len(parts) > 1 and parts[-1].isdigit():
        # Last part is a timestamp, remove it
        device_id = "_".join(parts[:-1])

    return device_id


def group_cameras_by_device(cameras: List[Dict]) -> Dict[str, List[Dict]]:
    """Group cameras by their base device ID"""
    groups = {}

    for camera in cameras:
        device_id = camera.get("device_id", "")
        base_device_id = extract_base_device_id(device_id)

        if base_device_id not in groups:
            groups[base_device_id] = []
        groups[base_device_id].append(camera)

    return groups


def delete_camera(camera_id: int) -> bool:
    """Delete a camera by ID"""
    try:
        response = requests.delete(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/{camera_id}",
            headers=get_auth_headers(),
            timeout=10,
        )

        if response.status_code in [200, 204]:
            return True
        else:
            print(f"❌ Failed to delete camera {camera_id}: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error deleting camera {camera_id}: {e}")
        return False


def cleanup_duplicates(cameras: List[Dict], dry_run: bool = True):
    """Clean up duplicate cameras, keeping the latest one for each device"""
    print(f"\n🧹 Starting cleanup (dry_run={dry_run})...")

    # Group cameras by base device ID
    groups = group_cameras_by_device(cameras)

    total_deletions = 0

    for base_device_id, camera_group in groups.items():
        if len(camera_group) <= 1:
            print(f"✅ {base_device_id}: Only 1 camera, skipping")
            continue

        print(f"\n🔍 Processing {base_device_id}: {len(camera_group)} cameras found")

        # Sort by created_at timestamp (keep the latest)
        sorted_cameras = sorted(
            camera_group, key=lambda x: x.get("created_at", ""), reverse=True
        )

        # Keep the first (latest) camera, delete the rest
        keep_camera = sorted_cameras[0]
        delete_cameras = sorted_cameras[1:]

        print(
            f'  ✅ Keeping: ID {keep_camera["id"]} - {keep_camera["device_id"]} (created: {keep_camera.get("created_at", "unknown")})'
        )

        for camera in delete_cameras:
            camera_id = camera["id"]
            device_id = camera["device_id"]
            created_at = camera.get("created_at", "unknown")

            if dry_run:
                print(
                    f"  🔴 Would delete: ID {camera_id} - {device_id} (created: {created_at})"
                )
                total_deletions += 1
            else:
                print(
                    f"  🗑️ Deleting: ID {camera_id} - {device_id} (created: {created_at})"
                )
                if delete_camera(camera_id):
                    print(f"    ✅ Successfully deleted camera {camera_id}")
                    total_deletions += 1
                else:
                    print(f"    ❌ Failed to delete camera {camera_id}")

    if dry_run:
        print(
            f"\n📊 Dry run complete: Would delete {total_deletions} duplicate cameras"
        )
        print("💡 Run with --execute to actually perform deletions")
    else:
        print(f"\n✅ Cleanup complete: Deleted {total_deletions} duplicate cameras")


def main():
    """Main function"""
    print("🧹 PPL Meta Mobile Camera Duplicate Cleanup Tool")
    print("=" * 55)

    # Check if we should actually execute deletions
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("🔍 Running in DRY RUN mode (no actual deletions)")
        print("💡 Add --execute flag to perform actual cleanup")
    else:
        print("⚠️  EXECUTION mode - will actually delete duplicates!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Cleanup cancelled")
            return

    # Get all mobile cameras
    cameras = get_mobile_cameras()
    if not cameras:
        print("❌ No mobile cameras found or failed to retrieve them")
        return

    # Show current status
    print(f"\n📋 Current mobile cameras:")
    for i, camera in enumerate(cameras, 1):
        print(
            f'  {i}. ID {camera["id"]}: {camera["name"]} - {camera["device_id"]} (status: {camera["status"]})'
        )

    # Perform cleanup
    cleanup_duplicates(cameras, dry_run=dry_run)


if __name__ == "__main__":
    main()
