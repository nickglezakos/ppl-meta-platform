#!/usr/bin/env python3
"""
Debug script to investigate why search returns only 2 appearances
when 45+ are expected from 55 videos.

Run this to check:
1. How many person objects exist in the 55 videos
2. How many are linked to MVR people
3. What the matching thresholds are filtering out
"""

import asyncio
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src')

from database import get_session
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from models.individuals import Individuals
from models.person_objects import PersonObjects
from models.mvr_people import MVRPeople
from models.videos import Videos

async def debug_search_results():
    """Debug why search only returns 2 appearances."""
    
    # Video UUIDs from the search (first 10 for testing)
    video_uuids = [
        '9a2185e9-1a13-444f-8d88-e64255be61fe',
        'c2e85427-85b1-48d8-8b58-2865673f86f4',
        '7f9a76c5-a9b6-4e00-9256-971afe4cc9d1',
        '8f9db9af-318c-42b7-8e92-2e068e62a69c',
        '25caeb8c-901a-4363-8d31-441d0d4be3f1',
        'ba281b95-d613-4f6c-b107-a0e56bc9c128',
        'f2829c42-a192-42e6-b700-e89632ef955d',
        '4a0bde71-32e9-49f7-9bc4-82db81383193',
        '4a53588d-1d78-4cbc-947f-aec0e95973fd',
        '80f5cf35-8736-404b-ad90-b250fb2bbc91',
    ]
    
    # Date range from search
    start_time = datetime.fromisoformat('2025-12-14T05:48:00')
    end_time = datetime.fromisoformat('2025-12-15T17:48:00')
    
    print(f"\n{'='*80}")
    print(f"DEBUG: Search Results Analysis")
    print(f"{'='*80}\n")
    
    async with get_session() as session:
        # 1. Count person objects in these videos
        print("1. Checking person objects in search videos...")
        person_objects_query = select(func.count(PersonObjects.person_object_uuid)).where(
            and_(
                PersonObjects.video_uuid.in_(video_uuids[:10]),  # First 10 videos
                PersonObjects.created_at >= start_time,
                PersonObjects.created_at <= end_time
            )
        )
        person_objects_count = await session.scalar(person_objects_query)
        print(f"   ✓ Person objects in first 10 videos: {person_objects_count}")
        
        # 2. Count individuals linked to these person objects
        print("\n2. Checking individuals...")
        individuals_query = select(func.count(Individuals.individual_uuid)).where(
            and_(
                Individuals.video_uuid.in_(video_uuids[:10]),
                Individuals.first_seen_timestamp >= start_time,
                Individuals.last_seen_timestamp <= end_time
            )
        )
        individuals_count = await session.scalar(individuals_query)
        print(f"   ✓ Individuals in first 10 videos: {individuals_count}")
        
        # 3. Count MVR people linked to these individuals
        print("\n3. Checking MVR people...")
        mvr_query = select(func.count(func.distinct(MVRPeople.mvr_people_uuid))).join(
            Individuals,
            Individuals.mvr_people_uuid == MVRPeople.mvr_people_uuid
        ).where(
            and_(
                Individuals.video_uuid.in_(video_uuids[:10]),
                Individuals.first_seen_timestamp >= start_time,
                Individuals.last_seen_timestamp <= end_time
            )
        )
        mvr_count = await session.scalar(mvr_query)
        print(f"   ✓ Unique MVR people in first 10 videos: {mvr_count}")
        
        # 4. Get sample data
        print("\n4. Sample MVR people with individual counts...")
        sample_query = select(
            MVRPeople.mvr_people_uuid,
            MVRPeople.confidence_score,
            func.count(Individuals.individual_uuid).label('individual_count')
        ).join(
            Individuals,
            Individuals.mvr_people_uuid == MVRPeople.mvr_people_uuid
        ).where(
            and_(
                Individuals.video_uuid.in_(video_uuids[:10]),
                Individuals.first_seen_timestamp >= start_time,
                Individuals.last_seen_timestamp <= end_time
            )
        ).group_by(
            MVRPeople.mvr_people_uuid,
            MVRPeople.confidence_score
        ).limit(10)
        
        result = await session.execute(sample_query)
        rows = result.all()
        
        for row in rows:
            print(f"   • MVR {row.mvr_people_uuid[:8]}... - "
                  f"Confidence: {row.confidence_score:.3f} - "
                  f"Individuals: {row.individual_count}")
        
        # 5. Check if threshold is filtering
        print("\n5. Checking confidence score distribution...")
        confidence_query = select(
            func.avg(MVRPeople.confidence_score).label('avg'),
            func.min(MVRPeople.confidence_score).label('min'),
            func.max(MVRPeople.confidence_score).label('max')
        ).join(
            Individuals,
            Individuals.mvr_people_uuid == MVRPeople.mvr_people_uuid
        ).where(
            and_(
                Individuals.video_uuid.in_(video_uuids[:10]),
                Individuals.first_seen_timestamp >= start_time,
                Individuals.last_seen_timestamp <= end_time
            )
        )
        
        conf_result = await session.execute(confidence_query)
        conf_row = conf_result.first()
        
        if conf_row:
            print(f"   • Average confidence: {conf_row.avg:.3f}")
            print(f"   • Min confidence: {conf_row.min:.3f}")
            print(f"   • Max confidence: {conf_row.max:.3f}")
            print(f"   • Threshold likely used: 0.75")
            
            # Count how many would pass threshold
            threshold_query = select(func.count(func.distinct(MVRPeople.mvr_people_uuid))).join(
                Individuals,
                Individuals.mvr_people_uuid == MVRPeople.mvr_people_uuid
            ).where(
                and_(
                    Individuals.video_uuid.in_(video_uuids[:10]),
                    Individuals.first_seen_timestamp >= start_time,
                    Individuals.last_seen_timestamp <= end_time,
                    MVRPeople.confidence_score >= 0.75
                )
            )
            threshold_count = await session.scalar(threshold_query)
            print(f"   • MVR people with confidence >= 0.75: {threshold_count}")
        
        print(f"\n{'='*80}")
        print("DIAGNOSIS:")
        print(f"{'='*80}")
        print(f"Expected: 45-48 appearances across 55 videos")
        print(f"Found: 2 appearances in search results")
        print(f"\nPossible issues:")
        print(f"1. If person_objects_count is low → Detection/processing issue")
        print(f"2. If individuals_count is low → Individual creation issue")
        print(f"3. If mvr_count is low → Face matching/MVR linking issue")
        print(f"4. If threshold_count is low → Confidence threshold too high")
        print(f"{'='*80}\n")

if __name__ == '__main__':
    asyncio.run(debug_search_results())
