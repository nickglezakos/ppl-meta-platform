"""
Test cross-video tracking with caching
This will run tracking twice with the same videos to verify caching works
"""

import requests
import json
import time
from datetime import datetime, timedelta
import asyncpg
import asyncio

VMETA_URL = "http://localhost:8008"

# Use 4 videos from existing data
TEST_VIDEOS = [
    "27e94b1a-2e15-4a82-9a86-c171b3b4854c",  # Has 16 individuals
    "138224f4-84ac-4490-8d8c-d4939fcd76d5",  # Has 12 individuals
    "04990aac-fc2a-401d-bdb7-290bb9a9c62c",  # Has 17 individuals
    "0500bb77-8ca8-4acb-9b55-e1413b443286",  # Has 16 individuals
]


async def check_cache_stats(session_uuid: str):
    """Check cache statistics for a session."""
    conn = await asyncpg.connect(
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    
    try:
        stats = await conn.fetch("""
            SELECT 
                video_uuid,
                cache_hit,
                individuals_reused,
                individuals_created
            FROM individual_cache_stats
            WHERE session_uuid = $1
            ORDER BY timestamp
        """, session_uuid)
        
        return stats
    finally:
        await conn.close()


def run_tracking_session(session_name: str):
    """Run a cross-video tracking session."""
    print(f"\n{'='*70}")
    print(f"Running tracking session: {session_name}")
    print(f"{'='*70}")
    
    # Create tracking request
    now = datetime.now()
    payload = {
        "collections": ["test_collection"],
        "start_time": (now - timedelta(hours=1)).isoformat(),
        "end_time": now.isoformat(),
        "algorithm_config": {
            "batch_size": 100,
            "is_default": False,
            "config_name": "test_caching",
            "description": "Test video-level caching",
            "iou_threshold": 0.3,
            "max_collections": 10,
            "max_gap_seconds": 3,
            "min_appearances": 1,
            "min_sequence_length": 2,
            "confidence_weight_iou": 0.4,
            "min_overlap_confidence": 0.5,
            "confidence_weight_spatial": 0.3,
            "confidence_weight_temporal": 0.3
        }
    }
    
    print(f"\n📹 Processing {len(TEST_VIDEOS)} videos...")
    print(f"Videos: {TEST_VIDEOS[:2]}... (+{len(TEST_VIDEOS)-2} more)")
    
    # Send request
    response = requests.post(
        f"{VMETA_URL}/api/v1/cross-video/individuals/tracking/sessions",
        json=payload,
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    session_uuid = result.get("session_uuid")
    
    print(f"\n✅ Session completed: {session_uuid}")
    print(f"\nResults:")
    print(f"  Total individuals: {result.get('total_individuals', 'N/A')}")
    print(f"  Processing time: {result.get('processing_time_seconds', 'N/A')}s")
    
    return session_uuid


async def main():
    """Main test function."""
    print("\n" + "="*70)
    print("VIDEO-LEVEL INDIVIDUAL CACHING TEST")
    print("="*70)
    
    print("\n📋 Test Plan:")
    print("  1. Run tracking session #1 (should create new individuals)")
    print("  2. Check cache stats (should show all cache MISSES)")
    print("  3. Run tracking session #2 with same videos")
    print("  4. Check cache stats (should show cache HITS)")
    print("  5. Verify individuals were reused, not duplicated")
    
    # Session 1: First run (no cache)
    print("\n" + "="*70)
    print("SESSION 1: First Run (Expected: Cache MISS)")
    print("="*70)
    session1_uuid = run_tracking_session("Session 1")
    
    if not session1_uuid:
        print("❌ Session 1 failed")
        return
    
    # Check cache stats for session 1
    print("\n📊 Cache Statistics for Session 1:")
    stats1 = await check_cache_stats(session1_uuid)
    
    total_hits = 0
    total_misses = 0
    total_created = 0
    
    for stat in stats1:
        video = str(stat['video_uuid'])[:8]
        if stat['cache_hit']:
            total_hits += 1
            print(f"  Video {video}: HIT (reused {stat['individuals_reused']})")
        else:
            total_misses += 1
            total_created += stat['individuals_created']
            print(f"  Video {video}: MISS (created {stat['individuals_created']})")
    
    print(f"\n  Summary: {total_hits} hits, {total_misses} misses")
    print(f"  Total individuals created: {total_created}")
    
    # Wait a moment
    print("\n⏳ Waiting 2 seconds before Session 2...")
    time.sleep(2)
    
    # Session 2: Second run (should use cache)
    print("\n" + "="*70)
    print("SESSION 2: Second Run (Expected: Cache HIT)")
    print("="*70)
    session2_uuid = run_tracking_session("Session 2")
    
    if not session2_uuid:
        print("❌ Session 2 failed")
        return
    
    # Check cache stats for session 2
    print("\n📊 Cache Statistics for Session 2:")
    stats2 = await check_cache_stats(session2_uuid)
    
    total_hits = 0
    total_misses = 0
    total_reused = 0
    total_created = 0
    
    for stat in stats2:
        video = str(stat['video_uuid'])[:8]
        if stat['cache_hit']:
            total_hits += 1
            total_reused += stat['individuals_reused']
            print(f"  Video {video}: HIT (reused {stat['individuals_reused']})")
        else:
            total_misses += 1
            total_created += stat['individuals_created']
            print(f"  Video {video}: MISS (created {stat['individuals_created']})")
    
    print(f"\n  Summary: {total_hits} hits, {total_misses} misses")
    print(f"  Total individuals reused: {total_reused}")
    print(f"  Total individuals created: {total_created}")
    
    # Final verification
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)
    
    if total_hits == len(TEST_VIDEOS):
        print("✅ SUCCESS: All videos had cache hits!")
    else:
        print(f"⚠️  PARTIAL: {total_hits}/{len(TEST_VIDEOS)} cache hits")
    
    if total_reused > 0:
        print(f"✅ SUCCESS: Reused {total_reused} individuals from cache")
    else:
        print("❌ FAILURE: No individuals were reused")
    
    if total_created == 0:
        print("✅ SUCCESS: No duplicate individuals created")
    else:
        print(f"⚠️  WARNING: {total_created} new individuals created in session 2")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
