#!/usr/bin/env python3
"""
Retroactive Pipeline Processing

This script processes existing videos through the complete pipeline:
1. Enhanced Logic V2: Creates person_objects from stored_faces
2. Cross-Video Tracking: Creates individuals/MVR from person_objects

Pipeline Flow:
    Stored Faces (Vision DB)
         ↓
    Enhanced Logic V2 → Person Objects (Orchestrator)
         ↓
    Cross-Video Tracking → Individuals → MVR People (VMeta)
"""

import asyncio
import sys
from datetime import datetime, timedelta
import httpx

# Service URLs
ORCHESTRATOR_URL = "http://localhost:8002"
MEDIA_URL = "http://localhost:8000"
NODE_URL = "http://localhost:8001"
VMETA_URL = "http://localhost:8008"

# User credentials
USER_EMAIL = "fresh.user@example.com"
USER_PASSWORD = "NewPassword234!"


async def get_auth_token():
    """Get JWT authentication token."""
    print("🔐 Getting authentication token...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{NODE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"username={USER_EMAIL}&password={USER_PASSWORD}"
        )
        
        if response.status_code != 200:
            print(f"❌ Authentication failed: {response.status_code}")
            sys.exit(1)
        
        token = response.json().get("access_token")
        print("✅ Authentication successful")
        return token


async def get_videos(token, collection_id="usb_camera_0", hours_back=24):
    """Get videos from collection."""
    print(f"\n📹 Fetching videos from '{collection_id}' (last {hours_back}h)...")
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch videos: {response.status_code}")
            return []
        
        videos = response.json()
        print(f"✅ Found {len(videos)} videos")
        return videos


async def create_person_objects(token, video_uuid):
    """
    Step 1: Call Enhanced Logic V2 to create person_objects from stored_faces.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{ORCHESTRATOR_URL}/api/v1/media/{video_uuid}/faces/enhanced-v2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": result.get("success", False),
                "total_faces": result.get("total_faces", 0),
                "source": result.get("source", "unknown")
            }
        else:
            return {"success": False, "error": response.status_code}


async def process_videos_step1(token, videos):
    """
    Step 1: Process all videos through Enhanced Logic V2.
    This creates person_objects from stored_faces.
    """
    print(f"\n🔧 STEP 1: Creating person_objects from stored_faces...")
    print(f"Processing {len(videos)} videos through Enhanced Logic V2...")
    
    successful = 0
    failed = 0
    
    for i, video in enumerate(videos, 1):
        video_uuid = video.get("uuid")
        if not video_uuid:
            continue
        
        result = await create_person_objects(token, video_uuid)
        
        if result.get("success"):
            faces = result.get("total_faces", 0)
            source = result.get("source", "?")
            print(f"  [{i}/{len(videos)}] ✅ {video_uuid[:8]}... → {faces} faces ({source})")
            successful += 1
        else:
            error = result.get("error", "unknown")
            print(f"  [{i}/{len(videos)}] ❌ {video_uuid[:8]}... → Error: {error}")
            failed += 1
        
        # Rate limiting
        if i % 5 == 0:
            await asyncio.sleep(1)
    
    print(f"\n✅ Step 1 complete: {successful} succeeded, {failed} failed")
    return successful > 0


async def trigger_tracking(token, videos, collection_id="usb_camera_0"):
    """
    Step 2: Trigger cross-video tracking to create individuals/MVR.
    """
    print(f"\n🎯 STEP 2: Creating individuals and MVR people...")
    
    if not videos:
        print("⚠️  No videos to process")
        return None
    
    # Get time range from videos
    start_times = [v.get("start_time") or v.get("created_at") for v in videos]
    end_times = [v.get("end_time") or v.get("updated_at") for v in videos]
    
    valid_starts = [t for t in start_times if t]
    valid_ends = [t for t in end_times if t]
    
    if not valid_starts or not valid_ends:
        print("⚠️  No valid timestamps")
        return None
    
    start_time = min(valid_starts)
    end_time = max(valid_ends)
    
    print(f"Time range: {start_time} to {end_time}")
    print(f"Processing {len(videos)} videos...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions",
            json={
                "collections": [collection_id],
                "start_time": start_time,
                "end_time": end_time,
                "background_processing": False,
                "force_reprocess": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            session_uuid = result.get("session_uuid")
            status = result.get("status")
            
            print(f"\n✅ Tracking session created:")
            print(f"   Session UUID: {session_uuid}")
            print(f"   Status: {status}")
            
            # Wait a bit for processing
            if status != "completed":
                print(f"\n⏳ Waiting for session to complete...")
                await asyncio.sleep(5)
                
                # Check status
                status_response = await client.get(
                    f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    individuals = status_data.get("individuals_found", 0)
                    mvr_count = status_data.get("unique_mvr_people_count", 0)
                    
                    print(f"\n📊 Results:")
                    print(f"   Individuals: {individuals}")
                    print(f"   MVR People: {mvr_count}")
                    print(f"   Status: {status_data.get('status')}")
            
            return result
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text[:300]}")
            return None


async def verify_results(token):
    """Verify results in VMeta."""
    print(f"\n🔍 Verifying final results...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{VMETA_URL}/health",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get("mvr_people", {}).get("statistics", {})
            
            print(f"\n📊 VMeta Statistics:")
            print(f"   Total MVR People: {stats.get('total_mvr_people', 0)}")
            print(f"   Individuals with MVR: {stats.get('individuals_with_mvr', 0)}")


async def main():
    """Main execution."""
    print("=" * 70)
    print("🚀 Retroactive Pipeline Processing")
    print("=" * 70)
    print("\nPipeline: Stored Faces → Person Objects → Individuals → MVR People")
    
    try:
        # Authenticate
        token = await get_auth_token()
        
        # Get videos
        videos = await get_videos(token, hours_back=24)
        
        if not videos:
            print("\n⚠️  No videos found")
            return
        
        print(f"\n📋 Processing {len(videos)} videos through 2-step pipeline")
        
        # Step 1: Create person_objects from stored_faces
        step1_success = await process_videos_step1(token, videos)
        
        if not step1_success:
            print("\n❌ Step 1 failed - cannot proceed to Step 2")
            return
        
        # Step 2: Create individuals/MVR from person_objects
        await trigger_tracking(token, videos)
        
        # Verify
        await verify_results(token)
        
        print("\n" + "=" * 70)
        print("✅ Pipeline processing completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
