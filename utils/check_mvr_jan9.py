import asyncio
import sys
import os
os.chdir('/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src')
sys.path.insert(0, '/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src')

from database import get_db_pool

async def check():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT 
              mp.mvr_people_uuid,
              mp.display_name,
              COUNT(DISTINCT imm.individual_uuid) as individual_count,
              COUNT(DISTINCT iva.video_uuid) as video_count,
              COUNT(DISTINCT iva.appearance_uuid) as appearance_count,
              EXISTS(
                SELECT 1 FROM mvr_merge_hierarchy 
                WHERE super_individual_uuid = mp.mvr_people_uuid
              ) as is_super_individual
            FROM mvr_people mp
            JOIN individual_mvr_mapping imm ON mp.mvr_people_uuid = imm.mvr_people_uuid
            JOIN individual_video_appearances iva ON imm.individual_uuid = iva.individual_uuid
            WHERE iva.video_uuid IN (
              SELECT DISTINCT video_uuid 
              FROM individual_video_appearances
              WHERE start_timestamp >= '2026-01-09'
            )
            GROUP BY mp.mvr_people_uuid
            ORDER BY appearance_count DESC
            LIMIT 10
        ''')
        
        print(f"Found {len(rows)} MVR people:")
        for row in rows:
            print(f"  {row['mvr_people_uuid']}: {row['display_name']} - "
                  f"{row['individual_count']} individuals, {row['video_count']} videos, "
                  f"{row['appearance_count']} appearances, super={row['is_super_individual']}")

asyncio.run(check())
