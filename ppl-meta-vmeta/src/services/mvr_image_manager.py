"""
MVR Image Manager Service
Retrieves best quality face and frame images for MVRpeople.

CORRECTED IMPLEMENTATION (Dec 18, 2025):
- Uses video-based Orchestrator endpoint, not person_object endpoint
- Queries video_uuid from database
- Groups by video to minimize API calls
- Extracts representative_faces from Orchestrator response
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import UUID
import httpx

from database.mvr_repository import MVRRepository

logger = logging.getLogger(__name__)


class BestFaceData:
    """Best quality face data."""
    def __init__(
        self,
        image_url: str,
        quality_score: float,
        person_object_uuid: str,
        video_uuid: str,
        timestamp: str,
        source_mvr_uuid: str,
        bbox: Optional[List[int]] = None,
        face_data: Optional[Dict[str, Any]] = None
    ):
        self.image_url = image_url
        self.quality_score = quality_score
        self.person_object_uuid = person_object_uuid
        self.video_uuid = video_uuid
        self.timestamp = timestamp
        self.source_mvr_uuid = source_mvr_uuid
        self.bbox = bbox  # [x1, y1, x2, y2] for client-side cropping
        self.face_data = face_data  # Full face_data object for client rendering
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'image_url': self.image_url,
            'quality_score': self.quality_score,
            'person_object_uuid': self.person_object_uuid,
            'video_uuid': self.video_uuid,
            'timestamp': self.timestamp,
            'source_mvr_uuid': self.source_mvr_uuid
        }
        if self.bbox:
            result['bbox'] = self.bbox
        if self.face_data:
            result['face_data'] = self.face_data
        return result


class FrameImageData:
    """Frame image data."""
    def __init__(
        self,
        image_url: str,
        person_object_uuid: str,
        video_uuid: str,
        timestamp: str
    ):
        self.image_url = image_url
        self.person_object_uuid = person_object_uuid
        self.video_uuid = video_uuid
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'image_url': self.image_url,
            'person_object_uuid': self.person_object_uuid,
            'video_uuid': self.video_uuid,
            'timestamp': self.timestamp
        }


class BestImageResponse:
    """Response containing best face and frame images."""
    def __init__(
        self,
        mvr_people_uuid: str,
        is_super_individual: bool,
        best_face: Optional[BestFaceData],
        frame_image: Optional[FrameImageData],
        metadata: Dict[str, Any]
    ):
        self.mvr_people_uuid = mvr_people_uuid
        self.is_super_individual = is_super_individual
        self.best_face = best_face
        self.frame_image = frame_image
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'mvr_people_uuid': self.mvr_people_uuid,
            'is_super_individual': self.is_super_individual,
            'best_face': self.best_face.to_dict() if self.best_face else None,
            'frame_image': self.frame_image.to_dict() if self.frame_image else None,
            'metadata': self.metadata
        }


class MVRImageManager:
    """Manages best image retrieval for MVRpeople."""
    
    def __init__(
        self,
        mvr_repo: MVRRepository,
        orchestrator_url: str,
        service_token: Optional[str] = None
    ):
        self.mvr_repo = mvr_repo
        self.orchestrator_url = orchestrator_url
        self.service_token = service_token
        logger.info(f"MVRImageManager initialized (Orchestrator: {orchestrator_url})")
    
    async def get_best_images_for_mvr(
        self,
        mvr_uuid: str,
        include_merged: bool = False,
        use_cache: bool = True
    ) -> BestImageResponse:
        """
        Get best quality face and frame images for MVRpeople UUID.
        
        Process:
        1. Check if super-individual and get merged children if requested
        2. Query video appearances from database
        3. Group by video_uuid to minimize API calls
        4. Call Orchestrator for each video
        5. Extract best face across all videos
        6. Return response with bbox for client-side rendering
        """
        start_time = datetime.utcnow()
        
        logger.info(f"Getting best images for MVR {mvr_uuid[:8]}... (include_merged={include_merged})")
        
        # Get MVR UUIDs to check (parent + merged children if requested)
        mvr_uuids = [mvr_uuid]
        is_super_individual = False
        
        if include_merged:
            # TODO: Query mvr_merge_hierarchy for merged children
            # For now, just use the single UUID
            pass
        
        # Query video appearances
        logger.info(f"Querying video appearances for {len(mvr_uuids)} MVR UUIDs: {mvr_uuids}")
        video_appearances = await self._get_video_appearances_for_mvr(mvr_uuids, limit=20)
        
        if not video_appearances:
            logger.warning(f"No video appearances found for MVR {mvr_uuid}")
            # Return empty response
            return BestImageResponse(
                mvr_people_uuid=mvr_uuid,
                is_super_individual=is_super_individual,
                best_face=None,
                frame_image=None,
                metadata={
                    'total_appearances_checked': 0,
                    'total_mvr_checked': len(mvr_uuids),
                    'cache_hit': False,
                    'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000)
                }
            )
        
        # Find best face across all videos
        best_face = await self._find_best_face(video_appearances)
        
        if not best_face:
            logger.warning(f"No face data found for MVR {mvr_uuid}")
        
        # Set source MVR UUID
        if best_face:
            best_face.source_mvr_uuid = mvr_uuid
        
        # Get frame image (same video as best face)
        frame_image = None
        if best_face:
            frame_image = FrameImageData(
                image_url=f"/api/v1/media/{best_face.video_uuid}/thumbnail",
                person_object_uuid=best_face.person_object_uuid,
                video_uuid=best_face.video_uuid,
                timestamp=best_face.timestamp
            )
        
        # Build response
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return BestImageResponse(
            mvr_people_uuid=mvr_uuid,
            is_super_individual=is_super_individual,
            best_face=best_face,
            frame_image=frame_image,
            metadata={
                'total_appearances_checked': len(video_appearances),
                'total_mvr_checked': len(mvr_uuids),
                'cache_hit': False,
                'processing_time_ms': processing_time_ms
            }
        )
    
    async def _get_video_appearances_for_mvr(
        self,
        mvr_uuids: List[str],
        limit: int = 20
    ) -> List[Dict]:
        """
        Query VMeta database for video appearances (NOT person_objects).
        
        Returns list of video appearances with:
        - video_uuid: UUID of the video
        - confidence: Detection confidence
        - start_timestamp: When person appeared
        - individual_uuid: Individual UUID
        
        Changed from person_object_uuid query to video_uuid query
        to match Orchestrator API which is media-centric.
        """
        # Convert string UUIDs to UUID objects for PostgreSQL
        uuid_objects = [UUID(uuid_str) for uuid_str in mvr_uuids]
        
        # Query individual_video_appearances for video UUIDs
        query = """
            SELECT DISTINCT 
                iva.video_uuid,
                iva.confidence,
                iva.start_timestamp,
                iva.individual_uuid
            FROM individual_video_appearances iva
            JOIN individual_mvr_mapping imm 
                ON iva.individual_uuid = imm.individual_uuid
            WHERE imm.mvr_people_uuid = ANY($1::uuid[])
            ORDER BY iva.confidence DESC
            LIMIT $2
        """
        
        logger.debug(f"Executing query with {len(uuid_objects)} UUIDs, limit: {limit}")
        
        async with self.mvr_repo.pool.acquire() as conn:
            rows = await conn.fetch(query, uuid_objects, limit)
        
        logger.info(f"Query returned {len(rows)} video appearances")
        
        if rows:
            logger.info(f"Sample video UUIDs: {[str(row['video_uuid']) for row in rows[:3]]}")
        
        return [
            {
                'video_uuid': str(row['video_uuid']),
                'confidence': float(row['confidence']),
                'start_timestamp': row['start_timestamp'],
                'individual_uuid': str(row['individual_uuid'])
            }
            for row in rows
        ]
    
    async def _find_best_face(
        self,
        video_appearances: List[Dict]
    ) -> Optional[BestFaceData]:
        """
        Fetch faces from Orchestrator for each video and find best quality.
        
        Process:
        1. Group appearances by video_uuid to minimize API calls
        2. Call Orchestrator once per video with media_id
        3. Extract representative_faces from each video's response
        4. Compare quality_scores to find global best (0-100 scale)
        """
        if not video_appearances:
            logger.warning("No video appearances to process")
            return None
        
        # Group appearances by video_uuid
        videos_by_uuid = {}
        for appearance in video_appearances:
            video_uuid = appearance['video_uuid']
            if video_uuid not in videos_by_uuid:
                videos_by_uuid[video_uuid] = []
            videos_by_uuid[video_uuid].append(appearance)
        
        logger.info(f"Grouped {len(video_appearances)} appearances into {len(videos_by_uuid)} unique videos")
        
        # Fetch faces from Orchestrator in parallel
        tasks = [
            self._fetch_faces_from_orchestrator(video_uuid, appearances)
            for video_uuid, appearances in videos_by_uuid.items()
        ]
        
        face_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all faces
        all_faces = []
        for result in face_results:
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch faces: {result}")
                continue
            if result:
                all_faces.extend(result)
        
        if not all_faces:
            logger.warning("No face data found across all videos")
            return None
        
        logger.info(f"Collected {len(all_faces)} total faces from {len(videos_by_uuid)} videos")
        
        # Find highest quality face (quality_score is 0-100 from Orchestrator)
        best_face_data = max(all_faces, key=lambda f: f['quality_score'])
        
        logger.info(
            f"Best face: quality={best_face_data['quality_score']:.2f}/100, "
            f"video={best_face_data['video_uuid'][:8]}, "
            f"frame={best_face_data.get('frame_number')}"
        )
        
        # Get frame number for frame extraction URL
        frame_number = best_face_data.get('face_data', {}).get('frame_number', 0)
        
        # Convert to BestFaceData with frame extraction URL (not video stream!)
        return BestFaceData(
            image_url=f"/api/v1/media/{best_face_data['video_uuid']}/frame/{frame_number}?format=jpeg",
            quality_score=best_face_data['quality_score'] / 100.0,  # Convert 0-100 to 0-1
            person_object_uuid=best_face_data.get('person_uuid', ''),
            video_uuid=best_face_data['video_uuid'],
            timestamp=str(best_face_data.get('timestamp', '')),
            source_mvr_uuid='',  # Will be set by caller
            bbox=best_face_data.get('bbox', []),
            face_data=best_face_data.get('face_data', {})
        )
    
    async def _fetch_faces_from_orchestrator(
        self,
        video_uuid: str,
        appearances: List[Dict]
    ) -> List[Dict]:
        """
        Call Orchestrator API to get all person_groups in a video.
        
        Endpoint: GET /person-objects/{media_id} (direct to Orchestrator)
        Note: Gateway routes with /api/v1/orchestrator/ prefix
        
        Fetches from Orchestrator Enhanced Logic V2 which retrieves persistent
        face data from Vision database. Returns person_groups with
        representative_faces already ranked by quality_score (0-100).
        
        
        Returns list of faces with quality_score, bbox, and metadata.
        Each video returns all detected person_groups with representative_faces
        already ranked by quality (selection_rank: 1 is best).
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Orchestrator service directly uses /person-objects/{media_id}
                # Gateway adds /api/v1/orchestrator/ prefix
                url = f"{self.orchestrator_url}/person-objects/{video_uuid}"
                headers = {}
                if self.service_token:
                    headers['Authorization'] = f'Bearer {self.service_token}'
                
                logger.info(f"Calling Orchestrator: {url}")
                response = await client.get(url, headers=headers)
                
                logger.info(f"Orchestrator response: status={response.status_code}")
                
                if response.status_code == 404:
                    logger.warning(f"No person objects found for video {video_uuid[:8]} (404)")
                    logger.debug(f"404 Response body: {response.text[:200]}")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                if not data.get('success'):
                    logger.warning(f"Orchestrator returned success=false for video {video_uuid[:8]}")
                    return []
                
                # Extract best face from each person_group
                faces = []
                person_groups = data.get('person_groups', [])
                
                logger.debug(f"Video {video_uuid[:8]} has {len(person_groups)} person_groups")
                
                for group in person_groups:
                    representative_faces = group.get('representative_faces', [])
                    if not representative_faces:
                        continue
                    
                    # First face is highest quality (pre-ranked by Orchestrator)
                    best_face = representative_faces[0]
                    face_data = best_face.get('face_data', {})
                    quality_score = best_face.get('quality_score', 0)
                    
                    logger.debug(
                        f"  Person {group.get('person_uuid', 'unknown')[:8]}: "
                        f"quality={quality_score:.2f}, "
                        f"frame={face_data.get('frame_number')}, "
                        f"bbox={face_data.get('bbox')}"
                    )
                    
                    faces.append({
                        'quality_score': quality_score,  # 0-100 scale from Orchestrator
                        'bbox': face_data.get('bbox', []),
                        'face_data': face_data,
                        'video_uuid': video_uuid,
                        'frame_number': face_data.get('frame_number'),
                        'timestamp': face_data.get('timestamp'),
                        'person_uuid': group.get('person_uuid'),
                        'confidence': face_data.get('confidence'),
                        'distance_from_camera': face_data.get('distance_from_camera'),
                        'selection_rank': best_face.get('selection_rank', 1)
                    })
                
                logger.info(f"Extracted {len(faces)} faces from video {video_uuid[:8]}")
                return faces
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching faces for video {video_uuid[:8]}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching faces for video {video_uuid[:8]}: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error fetching faces for video {video_uuid[:8]}: {e}")
            return []
    
    async def _fetch_frame_from_vision(
        self,
        video_uuid: str
    ) -> Optional[str]:
        """
        Get frame thumbnail URL for a video.
        Returns media service thumbnail endpoint.
        """
        return f"/api/v1/media/{video_uuid}/thumbnail"
