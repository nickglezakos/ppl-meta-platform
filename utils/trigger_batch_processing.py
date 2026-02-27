#!/usr/bin/env python3
"""
Manual Batch Processing Trigger

This script triggers the continuous individuals and MVR pipeline for existing videos
that have face detection completed but haven't been processed yet.

Use this when:
- Videos have stored_faces but no individuals/MVR people created
- Polling manager marked old videos as "processed" on startup
- You want to retroactively process existing recordings
"""

import asyncio
import sys
from datetime import datetime, timedelta
import httpx

# Service URLs
MEDIA_URL = "http://localhost:8000"
NODE_URL = "http://localhost:8001"
VMETA_URL = "http://localhost:8008"

# User credentials
USER_EMAIL = "fresh.user@example.com"
USER_PASSWORD = "NewPassword234!"


async def get_auth_token():
    """Get JWT authentication token from Node service."""
    print("🔐 Getting authentication token...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{NODE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"username={USER_EMAIL}&password={USER_PASSWORD}"
        )
        
        if response.status_code != 200:
            print(f"❌ Authentication failed: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        data = response.json()
        token = data.get("access_token")
        print("✅ Authentication successful")
        return token


async def get_videos_with_faces(token, collection_id="usb_camera_0", hours_back=24):
    """Get videos from collection that have face detection completed."""
    print(f"\n📹 Fetching videos from collection '{collection_id}' (last {hours_back} hours)...")
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Search for videos in time range
        response = await client.get(
            f"{MEDIA_URL}/api/v1/media/search",
            params={
                "collection_id": collection_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "page_size": 100,
                "order_by": "created_at",
                "order": "asc"
            },
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch videos: {response.status_code}")
            print(response.text)
            return []
        
        videos = response.json()
        print(f"✅ Found {len(videos)} videos in time range")
        
        # Filter videos with face detection
        videos_with_faces = []
        for video in videos:
            video_uuid = video.get("uuid")
            if not video_uuid:
                continue
            
            # Check if video has stored faces (quick check via metadata)
            # For now, assume all videos should be processed
            videos_with_faces.append(video)
        
        print(f"📊 {len(videos_with_faces)} videos ready for processing")
        return videos_with_faces


async def trigger_tracking_session(token, videos, collection_id="usb_camera_0"):
    """Trigger cross-video individual tracking session for videos."""
    print(f"\n🎯 Triggering tracking session for {len(videos)} videos...")
    
    if not videos:
        print("⚠️  No videos to process")
        return None
    
    # Take videos in batches of 5 (as per pipeline design)
    batch_size = 5
    all_results = []
    
    for i in range(0, len(videos), batch_size):
        batch_videos = videos[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(videos) + batch_size - 1) // batch_size
        
        # Calculate time range for this batch
        start_times = [v.get("start_time") or v.get("created_at") for v in batch_videos]
        end_times = [v.get("end_time") or v.get("updated_at") for v in batch_videos]
        
        # Filter out None values and find min/max
        valid_starts = [t for t in start_times if t]
        valid_ends = [t for t in end_times if t]
        
        if not valid_starts or not valid_ends:
            print(f"⚠️  Batch {batch_num}: No valid timestamps, skipping")
            continue
        
        batch_start = min(valid_starts)
        batch_end = max(valid_ends)
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch_videos)} videos)...")
        print(f"   Time range: {batch_start} to {batch_end}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await client.post(
                f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions",
                json={
                    "collections": [collection_id],
                    "start_time": batch_start,
                    "end_time": batch_end,
                    "background_processing": False,
                    "force_reprocess": False
                },
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Debug: Print full response to understand structure
                print(f"   Response keys: {list(result.keys())}")
                
                # Try different possible response structures
                session_uuid = (
                    result.get("session_uuid") or 
                    result.get("session_info", {}).get("session_uuid")
                )
                
                # Check for individuals/MVR in different locations
                individuals_count = (
                    result.get("individuals_found", 0) or
                    result.get("results", {}).get("total_individuals", 0)
                )
                
                mvr_count = (
                    result.get("unique_mvr_people_count", 0) or
                    result.get("results", {}).get("mvr_people_created", 0)
                )
                
                status = result.get("status", "unknown")
                
                print(f"✅ Batch {batch_num} completed:")
                print(f"   Session UUID: {session_uuid}")
                print(f"   Status: {status}")
                print(f"   Individuals: {individuals_count}")
                print(f"   MVR People: {mvr_count}")
                
                # If background processing, show message
                if result.get("message"):
                    print(f"   Message: {result.get('message')}")
                
                all_results.append(result)
            else:
                print(f"❌ Batch {batch_num} failed: {response.status_code}")
                print(f"   {response.text[:300]}")
        
        # Small delay between batches
        if i + batch_size < len(videos):
            await asyncio.sleep(2)
    
    return all_results


async def verify_results(token):
    """Verify individuals and MVR people were created."""
    print(f"\n🔍 Verifying results...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check VMeta health for statistics
        response = await client.get(f"{VMETA_URL}/health", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get("mvr_people", {}).get("statistics", {})
            
            print(f"\n📊 VMeta Statistics:")
            print(f"   Total MVR People: {stats.get('total_mvr_people', 0)}")
            print(f"   Individuals with MVR: {stats.get('individuals_with_mvr', 0)}")
        else:
            print(f"⚠️  Could not fetch statistics: {response.status_code}")


async def main():
    """Main execution flow."""
    print("=" * 60)
    print("🚀 Manual Batch Processing Trigger")
    print("=" * 60)
    
    try:
        # Step 1: Authenticate
        token = await get_auth_token()
        
        # Step 2: Get videos with face detection
        videos = await get_videos_with_faces(token, hours_back=24)
        
        if not videos:
            print("\n⚠️  No videos found to process")
            return
        
        print(f"\n📋 Summary:")
        print(f"   Videos to process: {len(videos)}")
        print(f"   Collection: usb_camera_0")
        print(f"   Batch size: 5 videos")
        
        # Step 3: Trigger tracking sessions (pass full video objects)
        results = await trigger_tracking_session(token, videos)
        
        # Step 4: Verify results
        await verify_results(token)
        
        print("\n" + "=" * 60)
        print("✅ Batch processing completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
