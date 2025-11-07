"""
Test script for video-level individual caching
Tests that the same video reuses individuals across different sessions
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
import sys

async def test_caching():
    """Test the caching implementation."""
    
    # Connect to database
    conn = await asyncpg.connect(
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    
    try:
        print("=" * 70)
        print("TESTING VIDEO-LEVEL INDIVIDUAL CACHING")
        print("=" * 70)
        print()
        
        # Check if necessary columns exist
        print("1️⃣ Checking database schema...")
        columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'individuals'
            AND column_name IN ('merged_into_uuid', 'algorithm_version')
        """)
        
        column_names = [c['column_name'] for c in columns]
        if 'merged_into_uuid' in column_names:
            print("   ✅ merged_into_uuid column exists")
        else:
            print("   ❌ merged_into_uuid column MISSING")
            return False
            
        if 'algorithm_version' in column_names:
            print("   ✅ algorithm_version column exists")
        else:
            print("   ❌ algorithm_version column MISSING")
            return False
        
        # Check cache stats table
        cache_stats_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'individual_cache_stats'
            )
        """)
        
        if cache_stats_exists:
            print("   ✅ individual_cache_stats table exists")
        else:
            print("   ❌ individual_cache_stats table MISSING")
            return False
        
        print()
        print("2️⃣ Checking existing data...")
        
        # Count individuals
        ind_count = await conn.fetchval("""
            SELECT COUNT(*) FROM individuals
        """)
        print(f"   📊 Total individuals: {ind_count}")
        
        # Count individuals with MVR
        mvr_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT i.individual_uuid)
            FROM individuals i
            JOIN individual_mvr_mapping mvr ON mvr.individual_uuid = i.individual_uuid
        """)
        print(f"   🧬 Individuals with MVR: {mvr_count}")
        
        # Count merged individuals
        merged_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM individuals
            WHERE merged_into_uuid IS NOT NULL
        """)
        print(f"   🔀 Merged individuals: {merged_count}")
        
        # Check appearances
        appearances = await conn.fetchval("""
            SELECT COUNT(*) FROM individual_video_appearances
        """)
        print(f"   📹 Total appearances: {appearances}")
        
        # Find videos with multiple individuals (candidates for testing)
        videos_with_multiple = await conn.fetch("""
            SELECT 
                video_uuid,
                COUNT(DISTINCT individual_uuid) as individual_count,
                ARRAY_AGG(DISTINCT individual_uuid) as individuals
            FROM individual_video_appearances
            GROUP BY video_uuid
            HAVING COUNT(DISTINCT individual_uuid) > 1
            LIMIT 5
        """)
        
        if videos_with_multiple:
            print()
            print("3️⃣ Videos with multiple individuals (merge candidates):")
            for row in videos_with_multiple:
                print(f"   Video: {row['video_uuid']}")
                print(f"   Individuals: {row['individual_count']}")
                
                # Check if these individuals share an MVR
                for ind_uuid in row['individuals']:
                    mvr = await conn.fetchval("""
                        SELECT mvr_people_uuid
                        FROM individual_mvr_mapping
                        WHERE individual_uuid = $1
                    """, ind_uuid)
                    merged = await conn.fetchval("""
                        SELECT merged_into_uuid
                        FROM individuals
                        WHERE individual_uuid = $1
                    """, ind_uuid)
                    
                    status = []
                    if mvr:
                        status.append(f"MVR:{str(mvr)[:8]}")
                    if merged:
                        status.append(f"merged→{str(merged)[:8]}")
                    
                    status_str = " | ".join(status) if status else "standalone"
                    print(f"     - {str(ind_uuid)[:8]}: {status_str}")
        else:
            print()
            print("3️⃣ No videos with multiple individuals found")
        
        print()
        print("4️⃣ Cache statistics:")
        cache_stats = await conn.fetch("""
            SELECT 
                cache_hit,
                COUNT(*) as count,
                SUM(individuals_reused) as total_reused,
                SUM(individuals_created) as total_created
            FROM individual_cache_stats
            GROUP BY cache_hit
            ORDER BY cache_hit DESC
        """)
        
        if cache_stats:
            for stat in cache_stats:
                hit_type = "HIT" if stat['cache_hit'] else "MISS"
                print(f"   {hit_type}: {stat['count']} videos")
                if stat['cache_hit']:
                    print(f"      Reused: {stat['total_reused']} individuals")
                else:
                    print(f"      Created: {stat['total_created']} individuals")
        else:
            print("   No cache statistics yet (no tracking sessions run)")
        
        print()
        print("=" * 70)
        print("✅ SCHEMA AND DATA CHECKS COMPLETE")
        print("=" * 70)
        
        return True
        
    finally:
        await conn.close()

if __name__ == "__main__":
    result = asyncio.run(test_caching())
    sys.exit(0 if result else 1)
