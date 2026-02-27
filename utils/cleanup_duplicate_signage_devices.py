#!/usr/bin/env python3
"""
Cleanup script to remove duplicate signage devices.

Keeps only the most recent device registration per device name.
"""

import sys
import os
from datetime import datetime
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor


def cleanup_duplicate_devices(dry_run=True):
    """
    Remove duplicate signage device registrations.
    
    Groups devices by device_name and keeps only the most recent registration.
    
    Args:
        dry_run: If True, only print what would be deleted
    """
    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        database="ppl_media_db",
        user="postgres",
        password="postgres"
    )
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all devices
        cur.execute("""
            SELECT uuid, device_id, device_name, device_hostname, ip_address, 
                   last_seen, created_at
            FROM signage_devices
            ORDER BY last_seen DESC NULLS LAST, created_at DESC
        """)
        all_devices = cur.fetchall()
        
        print(f"📊 Found {len(all_devices)} total device registrations")
        
        # Group devices by device_name (the actual unique identifier)
        devices_by_name = defaultdict(list)
        for device in all_devices:
            device_key = device['device_name'] or device['device_id']
            devices_by_name[device_key].append(device)
        
        print(f"📍 Grouped into {len(devices_by_name)} unique device names")
        print()
        
        total_to_delete = 0
        uuids_to_delete = []
        
        # For each device name, keep only the most recent
        for device_key, devices in devices_by_name.items():
            if len(devices) <= 1:
                continue
                
            # Sort by last_seen or created_at (most recent first)
            devices.sort(
                key=lambda d: d['last_seen'] or d['created_at'],
                reverse=True
            )
            
            # Keep the first (most recent), delete the rest
            keep_device = devices[0]
            delete_devices = devices[1:]
            
            print(f"🔍 Device Name: {device_key}")
            print(f"   ✅ KEEP: Device {keep_device['uuid']}")
            print(f"        IP: {keep_device['ip_address']}")
            print(f"        Last seen: {keep_device['last_seen']}")
            
            for device in delete_devices:
                total_to_delete += 1
                uuids_to_delete.append(device['uuid'])
                print(f"   ❌ DELETE: Device {device['uuid']}")
                print(f"        IP: {device['ip_address']}")
                print(f"        Last seen: {device['last_seen']}")
            
            print()
        
        if not dry_run and uuids_to_delete:
            # Delete duplicates - cast strings to UUIDs
            uuid_params = [str(u) for u in uuids_to_delete]
            cur.execute("""
                DELETE FROM signage_devices
                WHERE uuid::text = ANY(%s)
            """, (uuid_params,))
            conn.commit()
            print(f"✅ Deleted {total_to_delete} duplicate device registrations")
        else:
            print(f"🔍 DRY RUN: Would delete {total_to_delete} duplicate device registrations")
            print("\n💡 Run with --execute to actually delete the duplicates")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    
    print("🧹 Signage Device Cleanup Tool")
    print("=" * 60)
    print()
    
    if dry_run:
        print("🔍 Running in DRY RUN mode (no changes will be made)")
    else:
        print("⚠️  EXECUTING - Changes will be made to the database!")
    
    print()
    
    cleanup_duplicate_devices(dry_run=dry_run)
