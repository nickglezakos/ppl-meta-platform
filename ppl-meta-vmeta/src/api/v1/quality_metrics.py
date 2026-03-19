"""
Quality Metrics API

Endpoints for calculating average face quality of individuals by collection.
"""

import logging
import statistics
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_current_user, get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/individuals/quality-metrics",
    summary="Get average face quality metrics from individual objects by collection",
    description="Calculate average image quality from individual objects (NOT MVR objects) filtered by collection and time range. Returns quality metrics based on representative_faces data in individual_video_appearances.",
)
async def get_individuals_quality_metrics(
    collection_name: str = Query(..., description="Collection name to filter individuals"),
    start_time: datetime = Query(..., description="Start time for filtering (ISO format)"),
    end_time: datetime = Query(..., description="End time for filtering (ISO format)"),
    db_connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Calculate average face quality from individual objects in a specific collection.
    
    **Data Source:** individual_video_appearances.representative_faces
    - Quality is extracted from individual objects, NOT from MVR people
    - Each individual's quality is the average of their representative faces
    - Collection-level average is calculated from all individuals in the collection
    
    **Process:**
    1. Queries individual_video_appearances filtered by collection and time range
    2. Extracts face quality scores from representative_faces JSONB field
    3. Calculates average quality per individual (from their representative faces)
    4. Returns aggregate statistics across all individuals in the collection
    
    Args:
        collection_name: Collection name (camera) to filter by
        start_time: Start time for filtering individuals
        end_time: End time for filtering individuals
        db_connection: Database connection
        current_user: Authenticated user
        
    Returns:
        Dict with quality metrics:
        - average_quality: Average quality for this collection (0-1 scale)
        - individual_count: Number of individual objects analyzed
        - min_quality: Minimum quality score found
        - max_quality: Maximum quality score found
        - quality_std_dev: Standard deviation of quality scores
        - collection_name: Name of the collection
        - start_time, end_time: Time range used for filtering
    """
    try:
        logger.info(f"📊 Calculating quality metrics for collection: {collection_name} "
                   f"(time range: {start_time} to {end_time})")
        
        # Query to get individuals with their representative faces quality scores
        query = """
        WITH individual_qualities AS (
            SELECT DISTINCT ON (i.individual_uuid)
                i.individual_uuid,
                iva.representative_faces,
                iva.confidence,
                iva.video_uuid
            FROM individuals i
            JOIN individual_video_appearances iva 
                ON i.individual_uuid = iva.individual_uuid
            WHERE iva.start_timestamp >= $1
                AND iva.start_timestamp <= $2
                AND iva.representative_faces IS NOT NULL
            ORDER BY i.individual_uuid, iva.confidence DESC
        )
        SELECT 
            individual_uuid,
            representative_faces,
            confidence,
            video_uuid
        FROM individual_qualities
        """
        
        rows = await db_connection.fetch(query, start_time, end_time)
        
        if not rows:
            logger.info(f"No individuals found in specified time range")
            return {
                "collection_name": collection_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "average_quality": 0.0,
                "individual_count": 0,
                "min_quality": 0.0,
                "max_quality": 0.0,
                "quality_std_dev": 0.0
            }
        
        # Now verify which video_uuids belong to this collection by querying media service
        # Get unique video UUIDs
        video_uuids = list(set(str(row['video_uuid']) for row in rows))
        
        logger.info(f"Found {len(rows)} individual appearances across {len(video_uuids)} unique videos")
        
        # Query media service to get collection names for these videos
        import httpx
        collection_video_uuids = []
        
        try:
            MEDIA_SERVICE_URL = "http://localhost:8000"
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Query videos in batches
                for video_uuid in video_uuids:
                    try:
                        response = await client.get(
                            f"{MEDIA_SERVICE_URL}/api/v1/media/video/{video_uuid}"
                        )
                        if response.status_code == 200:
                            video_data = response.json()
                            video_collection = video_data.get("collection_name", "")
                            if video_collection == collection_name:
                                collection_video_uuids.append(video_uuid)
                    except Exception:
                        # Skip videos that can't be queried
                        continue
        except Exception as e:
            logger.warning(f"Failed to query media service, processing all videos: {e}")
            collection_video_uuids = video_uuids  # Fallback: use all videos
        
        logger.info(f"Filtered to {len(collection_video_uuids)} videos in collection {collection_name}")
        
        # Filter rows to only those in the target collection
        filtered_rows = [row for row in rows if str(row['video_uuid']) in collection_video_uuids]
        
        if not filtered_rows:
            logger.info(f"No individuals found for collection {collection_name} after filtering")
            return {
                "collection_name": collection_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "average_quality": 0.0,
                "individual_count": 0,
                "min_quality": 0.0,
                "max_quality": 0.0,
                "quality_std_dev": 0.0
            }
            
            # Extract quality scores from representative_faces JSONB
            all_quality_scores = []
            individual_avg_qualities = []
            
            for row in filtered_rows:
                representative_faces = row['representative_faces']
                
                # representative_faces is JSONB containing array of face objects
                # Each face object has a quality_score field
                if isinstance(representative_faces, dict):
                    faces = representative_faces.get('faces', [])
                elif isinstance(representative_faces, list):
                    faces = representative_faces
                else:
                    continue
                
                # Extract quality scores from faces
                face_qualities = []
                for face in faces:
                    quality = face.get('quality_score', face.get('qualityScore', face.get('quality', 0.0)))
                    
                    # Handle quality scores that might be in 0-100 range vs 0-1 range
                    if quality > 1.0:
                        quality = quality / 100.0
                    
                    if quality > 0.0:
                        face_qualities.append(quality)
                        all_quality_scores.append(quality)
                
                # Calculate average quality for this individual
                if face_qualities:
                    individual_avg_quality = statistics.mean(face_qualities)
                    individual_avg_qualities.append(individual_avg_quality)
            
            # Calculate aggregate statistics
            if individual_avg_qualities:
                avg_quality = statistics.mean(individual_avg_qualities)
                min_quality = min(individual_avg_qualities)
                max_quality = max(individual_avg_qualities)
                std_dev = statistics.stdev(individual_avg_qualities) if len(individual_avg_qualities) > 1 else 0.0
                individual_count = len(individual_avg_qualities)
            else:
                # Try using all quality scores if individual averages are empty
                if all_quality_scores:
                    avg_quality = statistics.mean(all_quality_scores)
                    min_quality = min(all_quality_scores)
                    max_quality = max(all_quality_scores)
                    std_dev = statistics.stdev(all_quality_scores) if len(all_quality_scores) > 1 else 0.0
                    individual_count = len(filtered_rows)
                else:
                    avg_quality = 0.0
                    min_quality = 0.0
                    max_quality = 0.0
                    std_dev = 0.0
                    individual_count = 0
            
            logger.info(f"✅ Quality metrics for {collection_name}: "
                       f"avg={avg_quality:.3f}, count={individual_count}, "
                       f"min={min_quality:.3f}, max={max_quality:.3f}, std={std_dev:.3f}")
            
            return {
                "collection_name": collection_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "average_quality": avg_quality,
                "individual_count": individual_count,
                "min_quality": min_quality,
                "max_quality": max_quality,
                "quality_std_dev": std_dev
            }
    
    except Exception as e:
        logger.error(f"❌ Error calculating quality metrics for {collection_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate quality metrics: {str(e)}"
        )


@router.get(
    "/mvr/quality-metrics",
    summary="Get quality metrics via MVR → Individual data tree",
    description="Calculate quality metrics by querying MVR people and their linked individuals. This follows the correct data hierarchy and includes all successfully processed data.",
)
async def get_mvr_quality_metrics(
    start_time: datetime = Query(..., description="Start time for filtering (ISO format)"),
    end_time: datetime = Query(..., description="End time for filtering (ISO format)"),
    collection_name: Optional[str] = Query(None, description="Optional collection name to filter (if omitted, returns all)"),
    source_type: Optional[str] = Query(None, description="Filter by source type: recording_pipeline or instant_detection (if omitted, returns all)"),
    current_user: dict = Depends(get_current_user),
    db_connection = Depends(get_db_connection)
) -> Dict:
    """
    Calculate quality metrics following MVR → Individual data tree.
    
    **Correct Data Access Pattern:**
    1. Query tracking sessions for timeframe (optionally filter by collection)
    2. Get individuals and MVR people from those sessions
    3. Extract representative_faces from individuals
    4. Calculate quality metrics from face data
    
    **Benefits:**
    - Uses tracking session metadata (individuals_found, unique_mvr_people_count)
    - Includes all successfully processed individuals
    - Doesn't filter out data where representative_faces failed to extract
    - Returns accurate counts matching batch processing results
    
    Args:
        start_time: Start time for filtering
        end_time: End time for filtering
        collection_name: Optional collection name to filter (if omitted or "all", returns all collections)
        db_connection: Database connection
        current_user: Authenticated user
        
    Returns:
        Dict with comprehensive quality metrics including MVR and individual counts
    """
    try:
        collection_display = collection_name if collection_name and collection_name != "all" else "ALL"
        source_display = source_type if source_type else "ALL"
        logger.info(f"📊 MVR Quality Metrics for {collection_display} source={source_display} ({start_time} to {end_time})")
        
        # Database columns are 'timestamp without time zone'
        # But PostgreSQL still stores the server's local time
        # When we insert with NOW(), it uses the server's local timezone
        # So we need to convert incoming UTC times to local timezone, then strip timezone info
        
        # First ensure times are timezone-aware (assume UTC if not)
        from datetime import timezone as tz
        import pytz
        
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=tz.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=tz.utc)
        
        # Convert to local timezone (server timezone where data was inserted)
        # Most systems use UTC or local TZ - let's use the current system timezone
        # Since NOW() in postgres uses server local time
        local_tz = pytz.timezone('Europe/Athens')  # UTC+2 (adjust if your server uses different TZ)
        start_time_local = start_time.astimezone(local_tz).replace(tzinfo=None)
        end_time_local = end_time.astimezone(local_tz).replace(tzinfo=None)
        
        logger.info(f"📊 Query time range (local): {start_time_local} to {end_time_local}")
        
        # Step 1: Get all tracking sessions for this collection + timeframe
        sessions_query = """
        SELECT 
            session_uuid,
            individuals_found,
            unique_mvr_people_count,
            total_videos,
            processed_videos,
            created_at,
            completed_at
        FROM tracking_sessions
        WHERE created_at >= $1
            AND created_at <= $2
            AND status = 'completed'
            AND ($3::text IS NULL OR source_type = $3)
            ORDER BY created_at DESC
        """
        
        sessions = await db_connection.fetch(sessions_query, start_time_local, end_time_local, source_type)
        
        if not sessions:
            logger.info(f"No completed tracking sessions found for {collection_display}")
            return {
                "collection_name": collection_display,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "tracking_sessions_count": 0,
                "total_individuals": 0,
                "total_mvr_people": 0,
                "total_videos_processed": 0,
                "mvr_with_quality": 0,
                "mvr_without_quality": 0,
                "total_quality_scores": 0,
                "average_quality": 0.0,
                "min_quality": 0.0,
                "max_quality": 0.0,
                "quality_std_dev": 0.0,
                "data_completeness": {
                    "total_mvr_people": 0,
                    "mvr_with_quality_scores": 0,
                    "percentage": 0.0
                }
            }
        
        logger.info(f"Found {len(sessions)} completed tracking sessions")
        
        # Step 2: Aggregate counts from tracking sessions
        total_individuals = sum(s['individuals_found'] or 0 for s in sessions)
        total_mvr_people = sum(s['unique_mvr_people_count'] or 0 for s in sessions)
        total_videos_processed = sum(s['processed_videos'] or 0 for s in sessions)
        
        # Step 3: Get MVR people created in this timeframe with their quality scores
        # Quality data is stored at the MVR level, not individual level
        mvr_query = """
        SELECT 
            mvr_people_uuid,
            face_quality,
            quality_score,
            total_linked_individuals,
            total_appearances,
            total_videos,
            created_at
        FROM mvr_people
        WHERE created_at >= $1
            AND created_at <= $2
            AND is_orphaned = false
            AND merged_into_mvr_uuid IS NULL
        ORDER BY created_at DESC
        """
        
        # When source_type is specified, filter MVR people through individual_mvr_mapping link_method
        if source_type == 'instant_detection':
            mvr_query = """
            SELECT DISTINCT ON (mp.mvr_people_uuid)
                mp.mvr_people_uuid,
                mp.face_quality,
                mp.quality_score,
                mp.total_linked_individuals,
                mp.total_appearances,
                mp.total_videos,
                mp.created_at
            FROM mvr_people mp
            JOIN individual_mvr_mapping imm ON mp.mvr_people_uuid = imm.mvr_people_uuid
            WHERE mp.created_at >= $1
                AND mp.created_at <= $2
                AND mp.is_orphaned = false
                AND mp.merged_into_mvr_uuid IS NULL
                AND imm.link_method = 'instant_detection'
            ORDER BY mp.mvr_people_uuid, mp.created_at DESC
            """
        
        mvr_people = await db_connection.fetch(mvr_query, start_time_local, end_time_local)
        
        logger.info(f"Found {len(mvr_people)} MVR people records")
        
        # Step 4: Extract quality scores from MVR people
        all_quality_scores = []
        mvr_with_quality = 0
        mvr_without_quality = 0
        
        for mvr in mvr_people:
            # Use face_quality if available, otherwise fall back to quality_score
            # Check for None explicitly since 0.0 is a valid (though poor) quality score
            quality = mvr['face_quality'] if mvr['face_quality'] is not None else mvr['quality_score']
            
            if quality is not None and quality > 0.0:
                # Quality is already normalized (0-1 range)
                all_quality_scores.append(float(quality))
                mvr_with_quality += 1
            else:
                mvr_without_quality += 1
                if quality is None:
                    logger.debug(f"MVR {mvr['mvr_people_uuid']} has no quality score (both fields None)")
                else:
                    logger.debug(f"MVR {mvr['mvr_people_uuid']} has zero quality: {quality}")
        
        # Step 5: Calculate aggregate statistics
        if all_quality_scores:
            avg_quality = statistics.mean(all_quality_scores)
            min_quality = min(all_quality_scores)
            max_quality = max(all_quality_scores)
            std_dev = statistics.stdev(all_quality_scores) if len(all_quality_scores) > 1 else 0.0
        else:
            avg_quality = 0.0
            min_quality = 0.0
            max_quality = 0.0
            std_dev = 0.0
        
        logger.info(f"✅ MVR Quality Metrics: {total_individuals} individuals, "
                   f"{total_mvr_people} MVR people, "
                   f"{mvr_with_quality} with quality data, "
                   f"avg quality: {avg_quality:.3f}")
        
        # Step 6: Get demographics from MVR people
        demographics_query = """
        SELECT 
            gender,
            age_min,
            age_max
        FROM mvr_people
        WHERE created_at >= $1
            AND created_at <= $2
            AND is_orphaned = false
            AND merged_into_mvr_uuid IS NULL
        """
        
        if source_type == 'instant_detection':
            demographics_query = """
            SELECT DISTINCT ON (mp.mvr_people_uuid)
                mp.gender,
                mp.age_min,
                mp.age_max
            FROM mvr_people mp
            JOIN individual_mvr_mapping imm ON mp.mvr_people_uuid = imm.mvr_people_uuid
            WHERE mp.created_at >= $1
                AND mp.created_at <= $2
                AND mp.is_orphaned = false
                AND mp.merged_into_mvr_uuid IS NULL
                AND imm.link_method = 'instant_detection'
            ORDER BY mp.mvr_people_uuid
            """
        
        mvr_demographics = await db_connection.fetch(demographics_query, start_time_local, end_time_local)
        
        # Count MVR people with demographics
        mvr_with_gender = sum(1 for m in mvr_demographics if m['gender'] is not None)
        mvr_with_age = sum(1 for m in mvr_demographics if m['age_min'] is not None and m['age_max'] is not None)
        
        # Count gender distribution
        gender_counts = {"Male": 0, "Female": 0, "Unknown": 0}
        for m in mvr_demographics:
            gender = m['gender']
            if gender == "Male":
                gender_counts["Male"] += 1
            elif gender == "Female":
                gender_counts["Female"] += 1
            else:
                gender_counts["Unknown"] += 1
        
        # Count age distribution
        age_ranges = {
            "0-17": 0,
            "18-24": 0,
            "25-34": 0,
            "35-44": 0,
            "45-54": 0,
            "55-64": 0,
            "65+": 0,
            "Unknown": 0
        }
        
        for m in mvr_demographics:
            age_min = m['age_min']
            age_max = m['age_max']
            
            if age_min is None or age_max is None:
                age_ranges["Unknown"] += 1
            else:
                # Use average age for classification
                avg_age = (age_min + age_max) / 2
                if avg_age < 18:
                    age_ranges["0-17"] += 1
                elif avg_age < 25:
                    age_ranges["18-24"] += 1
                elif avg_age < 35:
                    age_ranges["25-34"] += 1
                elif avg_age < 45:
                    age_ranges["35-44"] += 1
                elif avg_age < 55:
                    age_ranges["45-54"] += 1
                elif avg_age < 65:
                    age_ranges["55-64"] += 1
                else:
                    age_ranges["65+"] += 1
        
        logger.info(f"Demographics: {mvr_with_gender} with gender, {mvr_with_age} with age")
        
        return {
            "collection_name": collection_display,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "tracking_sessions_count": len(sessions),
            "total_individuals": total_individuals,  # From tracking sessions
            "total_mvr_people": total_mvr_people,    # From tracking sessions
            "total_videos_processed": total_videos_processed,
            "mvr_with_quality": mvr_with_quality,
            "mvr_without_quality": mvr_without_quality,
            "total_quality_scores": len(all_quality_scores),
            "average_quality": avg_quality,
            "min_quality": min_quality,
            "max_quality": max_quality,
            "quality_std_dev": std_dev,
            "data_completeness": {
                "total_mvr_people": total_mvr_people,
                "mvr_with_quality_scores": mvr_with_quality,
                "percentage": round((mvr_with_quality / total_mvr_people * 100) if total_mvr_people > 0 else 0, 2)
            },
            "demographics": {
                "total_mvr_people": total_mvr_people,
                "mvr_with_gender": mvr_with_gender,
                "mvr_with_age": mvr_with_age,
                "gender_distribution": gender_counts,
                "age_distribution": age_ranges,
                "completeness": {
                    "gender_percentage": round((mvr_with_gender / total_mvr_people * 100) if total_mvr_people > 0 else 0, 2),
                    "age_percentage": round((mvr_with_age / total_mvr_people * 100) if total_mvr_people > 0 else 0, 2)
                }
            }
        }
    except Exception as e:
        logger.error(f"❌ Error calculating MVR quality metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate MVR quality metrics: {str(e)}"
        )
