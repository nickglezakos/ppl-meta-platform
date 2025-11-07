"""
Test video-level individual caching with REAL DATA from November 5, 2025

This test uses actual session data from production:
- Session: 792517a3-9f86-4626-9134-1ec3d31ba128
- Collection: usb_camera_0
- Time: 08:40 - 10:49
- Videos: 4
- Individual: ind_e147b0a0 (appears in all 4 videos)
"""

import asyncio
import asyncpg
from datetime import datetime

# Real session data
ORIGINAL_SESSION_UUID = "792517a3-9f86-4626-9134-1ec3d31ba128"
TEST_INDIVIDUAL_UUID = "e147b0a0-9090-4a78-b0d1-2e939e7d282d"
TEST_INDIVIDUAL_ID = "ind_e147b0a0"

TEST_VIDEOS = [
    "38bf1f11-17b7-475b-9cc3-4ebfdef2b39a",
    "40f2d732-b266-4cc8-b779-00092c2eba11",
    "a9ca2222-8d9a-4a90-b6fe-4da234cd6839",
    "bf0a70e4-f841-48e0-a931-5cbdc7cec6a7"
]


async def check_original_session():
    """Verify the original session data."""
    conn = await asyncpg.connect(
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    
    try:
        print("="*70)
        print("CHECKING ORIGINAL SESSION DATA")
        print("="*70)
        
        # Check session
        session = await conn.fetchrow("""
            SELECT 
                session_uuid,
                status,
                total_videos,
                individuals_found,
                cache_hits,
                start_time,
                end_time
            FROM tracking_sessions
            WHERE session_uuid = $1
        """, ORIGINAL_SESSION_UUID)
        
        if not session:
            print(f"❌ Session {ORIGINAL_SESSION_UUID} not found!")
            return False
        
        print(f"\n✅ Session found:")
        print(f"   Status: {session['status']}")
        print(f"   Videos: {session['total_videos']}")
        print(f"   Individuals: {session['individuals_found']}")
        print(f"   Cache hits: {session['cache_hits']}")
        print(f"   Time: {session['start_time']} - {session['end_time']}")
        
        # Check individual
        individual = await conn.fetchrow("""
            SELECT 
                individual_uuid,
                individual_id,
                created_at
            FROM individuals
            WHERE individual_uuid = $1
        """, TEST_INDIVIDUAL_UUID)
        
        if not individual:
            print(f"\n❌ Individual {TEST_INDIVIDUAL_ID} not found!")
            return False
        
        print(f"\n✅ Individual found:")
        print(f"   UUID: {individual['individual_uuid']}")
        print(f"   ID: {individual['individual_id']}")
        print(f"   Created: {individual['created_at']}")
        
        # Check video appearances
        appearances = await conn.fetch("""
            SELECT video_uuid
            FROM individual_video_appearances
            WHERE individual_uuid = $1
            ORDER BY video_uuid
        """, TEST_INDIVIDUAL_UUID)
        
        print(f"\n✅ Appearances in {len(appearances)} videos:")
        for i, app in enumerate(appearances, 1):
            video_short = str(app['video_uuid'])[:8]
            print(f"   {i}. {video_short}...")
        
        # Verify all test videos are present
        appearance_videos = [str(a['video_uuid']) for a in appearances]
        missing = set(TEST_VIDEOS) - set(appearance_videos)
        if missing:
            print(f"\n⚠️  Missing videos: {missing}")
            return False
        
        print(f"\n✅ All {len(TEST_VIDEOS)} test videos confirmed!")
        
        # Check MVR mapping
        mvr = await conn.fetchrow("""
            SELECT mvr_people_uuid, is_representative
            FROM individual_mvr_mapping
            WHERE individual_uuid = $1
        """, TEST_INDIVIDUAL_UUID)
        
        if mvr:
            print(f"\n✅ MVR-People mapping exists:")
            print(f"   MVR UUID: {str(mvr['mvr_people_uuid'])[:8]}...")
            print(f"   Representative: {mvr['is_representative']}")
        else:
            print(f"\n⚠️  No MVR-People mapping (caching will still work)")
        
        print("\n" + "="*70)
        return True
        
    finally:
        await conn.close()


async def test_video_caching():
    """
    Test that processing the same videos again will use caching.
    
    This simulates reprocessing the EXACT same 4 videos.
    """
    print("\n" + "="*70)
    print("TESTING VIDEO-LEVEL CACHING")
    print("="*70)
    
    conn = await asyncpg.connect(
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    
    try:
        print("\n📊 Current state:")
        
        # Count existing individuals
        ind_count_before = await conn.fetchval("""
            SELECT COUNT(*) FROM individuals
        """)
        print(f"   Total individuals: {ind_count_before}")
        
        # Check if cache stats table exists
        has_cache_stats = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'individual_cache_stats'
            )
        """)
        
        if has_cache_stats:
            print("   ✅ individual_cache_stats table exists")
        else:
            print("   ❌ individual_cache_stats table MISSING")
            print("   → Run the migration: add_individual_caching_support.sql")
            return False
        
        # Check for existing cache stats for our videos
        for video in TEST_VIDEOS:
            cache_stats = await conn.fetch("""
                SELECT 
                    session_uuid,
                    cache_hit,
                    individuals_reused,
                    individuals_created
                FROM individual_cache_stats
                WHERE video_uuid = $1
            """, video)
            
            video_short = video[:8]
            if cache_stats:
                print(f"\n   Video {video_short}: {len(cache_stats)} cache entries")
                for stat in cache_stats[:2]:  # Show first 2
                    hit_type = "HIT" if stat['cache_hit'] else "MISS"
                    session_short = str(stat['session_uuid'])[:8]
                    print(f"      {hit_type} in {session_short}... "
                          f"(reused: {stat['individuals_reused']}, "
                          f"created: {stat['individuals_created']})")
            else:
                print(f"   Video {video_short}: No cache stats yet")
        
        print("\n" + "="*70)
        print("TEST SCENARIO: Reprocess same 4 videos")
        print("="*70)
        
        print("\n🔍 Without caching (current behavior):")
        print("   • Would create 4+ new individuals")
        print("   • Would duplicate ind_e147b0a0")
        print(f"   • Total individuals: {ind_count_before} → "
              f"{ind_count_before + 4}+")
        
        print("\n✅ With caching (after implementation):")
        print("   • Finds ind_e147b0a0 in all 4 videos")
        print("   • Reuses existing individual")
        print("   • Creates session link with processing_type='cached'")
        print(f"   • Total individuals: {ind_count_before} → "
              f"{ind_count_before} (unchanged)")
        
        print("\n💡 To test caching implementation:")
        print("   1. Ensure migration is applied")
        print("   2. Restart vmeta service with new code")
        print("   3. Create new session with same collection/time range:")
        print("      curl -X POST http://localhost:8008/api/v1/cross-video/"
              "individuals/tracking/sessions \\")
        print("           -H 'Content-Type: application/json' \\")
        print("           -d '{")
        print("             \"collections\": [\"usb_camera_0\"],")
        print("             \"start_time\": \"2025-11-05T08:40:00\",")
        print("             \"end_time\": \"2025-11-05T10:49:00\",")
        print("             \"algorithm_config\": { ... }")
        print("           }'")
        print("   4. Check cache_hits in response")
        print("   5. Query individual_cache_stats for the new session")
        
        return True
        
    finally:
        await conn.close()


async def verify_schema_requirements():
    """Check if database has required columns/tables for caching."""
    print("\n" + "="*70)
    print("VERIFYING SCHEMA REQUIREMENTS")
    print("="*70)
    
    conn = await asyncpg.connect(
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    
    try:
        requirements = []
        
        # Check for merged_into_uuid column
        has_merged_into = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'individuals'
                AND column_name = 'merged_into_uuid'
            )
        """)
        
        requirements.append({
            "name": "individuals.merged_into_uuid column",
            "exists": has_merged_into,
            "required": True
        })
        
        # Check for algorithm_version column
        has_algo_version = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'individuals'
                AND column_name = 'algorithm_version'
            )
        """)
        
        requirements.append({
            "name": "individuals.algorithm_version column",
            "exists": has_algo_version,
            "required": True
        })
        
        # Check for cache stats table
        has_cache_stats = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'individual_cache_stats'
            )
        """)
        
        requirements.append({
            "name": "individual_cache_stats table",
            "exists": has_cache_stats,
            "required": True
        })
        
        print("\n📋 Requirements:")
        all_met = True
        for req in requirements:
            status = "✅" if req['exists'] else "❌"
            print(f"   {status} {req['name']}")
            if req['required'] and not req['exists']:
                all_met = False
        
        if all_met:
            print("\n✅ All requirements met! Ready for caching implementation.")
        else:
            print("\n❌ Missing requirements. Run migration:")
            print("   psql -U postgres -d ppl_meta_vmeta -f "
                  "migrations/add_individual_caching_support.sql")
        
        return all_met
        
    finally:
        await conn.close()


async def main():
    """Run all checks."""
    print("\n" + "="*70)
    print("VIDEO-LEVEL INDIVIDUAL CACHING TEST")
    print("Real Data from November 5, 2025")
    print("="*70)
    
    # Step 1: Verify original session
    if not await check_original_session():
        print("\n❌ Original session verification failed!")
        return
    
    # Step 2: Check schema
    if not await verify_schema_requirements():
        print("\n⚠️  Schema requirements not met!")
        print("   Caching will not work until migration is applied.")
    
    # Step 3: Test caching scenario
    await test_video_caching()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. ✅ Migration applied (if schema check passed)")
    print("2. 🔨 Implement caching code in cross_video_tracking_simple.py")
    print("3. 🧪 Create new session with same videos to test cache hits")
    print("4. 📊 Verify cache statistics are recorded")
    print("5. ✅ Confirm no duplicate individuals created")


if __name__ == "__main__":
    asyncio.run(main())
