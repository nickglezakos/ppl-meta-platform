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
import json
import os
import urllib.parse
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
        self.vision_url = os.getenv("VISION_SERVICE_URL", "http://localhost:8003")
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
            descendant_query = """
                WITH RECURSIVE descendants AS (
                    SELECT mvr_people_uuid
                    FROM mvr_people
                    WHERE mvr_people_uuid = $1::uuid

                    UNION

                    SELECT child.mvr_people_uuid
                    FROM mvr_people child
                    INNER JOIN descendants parent
                        ON child.merged_into_mvr_uuid = parent.mvr_people_uuid
                )
                SELECT mvr_people_uuid
                FROM descendants
            """
            async with self.mvr_repo.pool.acquire() as conn:
                descendant_rows = await conn.fetch(descendant_query, UUID(mvr_uuid))

            expanded_mvr_uuids = [str(row['mvr_people_uuid']) for row in descendant_rows]
            if expanded_mvr_uuids:
                mvr_uuids = expanded_mvr_uuids
            is_super_individual = len(mvr_uuids) > 1
        
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
                    'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    'fallback_image_urls': []
                }
            )
        
        # Find best face across all videos
        best_face, fallback_image_urls = await self._find_best_face(video_appearances)
        
        if not best_face:
            logger.warning(f"No face data found for MVR {mvr_uuid}")
        
        # Set source MVR UUID
        if best_face:
            best_face.source_mvr_uuid = mvr_uuid
        
        # Get frame image (same video as best face)
        frame_image = None
        if best_face:
            frame_image = FrameImageData(
                image_url=f"/api/v1/media/thumbnail/{best_face.video_uuid}",
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
                'processing_time_ms': processing_time_ms,
                'fallback_image_urls': fallback_image_urls
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
                iva.person_object_uuid,
                iva.confidence,
                iva.start_timestamp,
                iva.individual_uuid,
                iva.representative_faces
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
        
        # Fallback for orphaned (child) MVR people: their individuals were reassigned
        # to the winner after a merge, so the normal join returns 0 rows.
        # Look up the original individual UUIDs via mvr_merge_audit_log.
        if not rows and len(mvr_uuids) == 1:
            logger.info(
                f"No appearances via current mapping for {mvr_uuids[0][:8]}..., "
                "trying audit log fallback (orphaned MVR)"
            )
            audit_query = """
                SELECT DISTINCT source_individual_uuid
                FROM mvr_merge_audit_log
                WHERE source_mvr_uuid = $1::uuid
                  AND merge_action    = 'merged'
            """
            async with self.mvr_repo.pool.acquire() as conn:
                audit_rows = await conn.fetch(audit_query, uuid_objects[0])
            
            if audit_rows:
                individual_uuids = [r["source_individual_uuid"] for r in audit_rows]
                logger.info(
                    f"Audit log returned {len(individual_uuids)} original individuals "
                    f"for orphaned MVR {mvr_uuids[0][:8]}..."
                )
                fallback_query = """
                    SELECT DISTINCT
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.confidence,
                        iva.start_timestamp,
                        iva.individual_uuid,
                        iva.representative_faces
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                    ORDER BY iva.confidence DESC
                    LIMIT $2
                """
                async with self.mvr_repo.pool.acquire() as conn:
                    rows = await conn.fetch(fallback_query, individual_uuids, limit)
                logger.info(f"Fallback query returned {len(rows)} video appearances")
        
        if rows:
            logger.info(f"Sample video UUIDs: {[str(row['video_uuid']) for row in rows[:3]]}")
        
        return [
            {
                'video_uuid': str(row['video_uuid']),
                'person_object_uuid': str(row['person_object_uuid']) if row['person_object_uuid'] else '',
                'confidence': float(row['confidence']),
                'start_timestamp': row['start_timestamp'],
                'individual_uuid': str(row['individual_uuid']),
                'representative_faces': row['representative_faces'],
            }
            for row in rows
        ]
    
    async def _find_best_face(
        self,
        video_appearances: List[Dict]
    ) -> tuple[Optional[BestFaceData], List[str]]:
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
            return None, []
        
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
            return None, []
        
        logger.info(f"Collected {len(all_faces)} total faces from {len(videos_by_uuid)} videos")
        
        # Sort by quality score descending and build prioritized fallback candidates
        sorted_faces = sorted(all_faces, key=lambda f: f.get('quality_score', 0), reverse=True)
        fallback_image_urls: List[str] = []
        fallback_seen = set()

        max_fallback_candidates = 6
        for candidate in sorted_faces[:10]:
            candidate_video_uuid = candidate.get('video_uuid')
            if candidate_video_uuid:
                thumbnail_url = f"/api/v1/media/thumbnail/{candidate_video_uuid}"
                if thumbnail_url not in fallback_seen:
                    fallback_seen.add(thumbnail_url)
                    fallback_image_urls.append(thumbnail_url)
                    if len(fallback_image_urls) >= max_fallback_candidates:
                        break

        best_face_data = None
        for candidate in sorted_faces:
            candidate_frame = self._extract_frame_number(candidate)
            if candidate_frame is None:
                continue
            best_face_data = candidate
            break

        if best_face_data is None:
            best_face_data = sorted_faces[0]
        
        logger.info(
            f"Best face: quality={best_face_data['quality_score']:.2f}/100, "
            f"video={best_face_data['video_uuid'][:8]}, "
            f"frame={best_face_data.get('frame_number')}"
        )
        
        frame_number = self._extract_frame_number(best_face_data)
        bbox = best_face_data.get('bbox') or []
        has_complete_bbox = len(bbox) == 4 and all(value is not None for value in bbox)
        has_crop_params = frame_number is not None and has_complete_bbox
        logger.info(
            "Best face payload: video=%s frame=%s bbox=%s has_crop_params=%s face_meta_keys=%s",
            best_face_data['video_uuid'],
            frame_number,
            bbox,
            has_crop_params,
            sorted((best_face_data.get('face_data') or {}).keys()),
        )

        best_face_params = {
            'video_uuid': best_face_data['video_uuid'],
            'frame_number': frame_number,
            'x1': bbox[0] if len(bbox) == 4 else None,
            'y1': bbox[1] if len(bbox) == 4 else None,
            'x2': bbox[2] if len(bbox) == 4 else None,
            'y2': bbox[3] if len(bbox) == 4 else None,
        }
        face_meta = best_face_data.get('face_data') or {}
        if face_meta.get('frame_width') is not None:
            best_face_params['detect_frame_width'] = face_meta.get('frame_width')
        if face_meta.get('frame_height') is not None:
            best_face_params['detect_frame_height'] = face_meta.get('frame_height')

        crop_query = urllib.parse.urlencode({
            key: value for key, value in best_face_params.items()
            if value is not None
        })

        image_url = (
            f"/api/v1/mvr-people/face-crop?{crop_query}"
            if has_crop_params
            else f"/api/v1/media/thumbnail/{best_face_data['video_uuid']}"
        )

        # Persisted person-groups can expose only face_id/quality_score without crop coordinates.
        # Fall back to the video thumbnail instead of emitting a broken face-crop URL.
        best_face = BestFaceData(
            image_url=image_url,
            quality_score=best_face_data['quality_score'] / 100.0,  # Convert 0-100 to 0-1
            person_object_uuid=best_face_data.get('person_uuid', ''),
            video_uuid=best_face_data['video_uuid'],
            timestamp=str(best_face_data.get('timestamp', '')),
            source_mvr_uuid='',  # Will be set by caller
            bbox=bbox if has_crop_params else None,
            face_data=face_meta if has_crop_params else None
        )

        return best_face, fallback_image_urls

    def _extract_frame_number(self, face_candidate: Dict[str, Any]) -> Optional[int]:
        direct_frame = face_candidate.get('frame_number')
        if isinstance(direct_frame, str):
            try:
                direct_frame = int(direct_frame)
            except ValueError:
                direct_frame = None
        if isinstance(direct_frame, int) and direct_frame >= 0:
            return direct_frame

        face_data = face_candidate.get('face_data') or {}
        nested_frame = face_data.get('frame_number')
        if isinstance(nested_frame, str):
            try:
                nested_frame = int(nested_frame)
            except ValueError:
                nested_frame = None
        if isinstance(nested_frame, int) and nested_frame >= 0:
            return nested_frame

        return None
    
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
                
                # Extract faces only from person_groups that match the target
                # appearance rows for this MVR. Without this filter, a different
                # person from the same video can be selected as the "best" face.
                faces = []
                person_groups = data.get('person_groups', [])
                face_details_by_id = await self._fetch_face_details_from_vision(video_uuid)
                
                logger.debug(f"Video {video_uuid[:8]} has {len(person_groups)} person_groups")
                
                for appearance in appearances:
                    appearance_representative_faces = self._parse_representative_faces(
                        appearance.get('representative_faces')
                    )
                    matched_group = self._match_person_group_for_appearance(
                        person_groups,
                        appearance.get('person_object_uuid'),
                        appearance_representative_faces,
                    )
                    if matched_group is None:
                        logger.debug(
                            "No matching person_group found for MVR appearance %s in video %s",
                            appearance.get('person_object_uuid'),
                            video_uuid[:8],
                        )
                        if appearance_representative_faces:
                            faces.extend(
                                self._build_face_candidates(
                                    video_uuid,
                                    appearance,
                                    appearance_representative_faces,
                                    appearance.get('person_object_uuid'),
                                    appearance,
                                    face_details_by_id,
                                )
                            )
                        else:
                            # Fallback for appearances persisted with synthetic
                            # person_uuid AND empty representative_faces (a
                            # legacy materialization path). Without this we
                            # would emit zero candidates and the MVR would
                            # render the generic person icon. Use whatever
                            # representative_faces the orchestrator has for
                            # this video so the user at least sees a face.
                            logger.info(
                                "MVR appearance %s in video %s has no rep_faces "
                                "and no group match; using all video person_groups "
                                "as fallback candidates",
                                appearance.get('person_object_uuid'),
                                video_uuid[:8],
                            )
                            for fallback_group in person_groups:
                                fallback_rep_faces = fallback_group.get(
                                    'representative_faces', []
                                )
                                if not self._representative_faces_have_face_data(
                                    fallback_rep_faces
                                ):
                                    continue
                                faces.extend(
                                    self._build_face_candidates(
                                        video_uuid,
                                        appearance,
                                        fallback_rep_faces,
                                        fallback_group.get('person_uuid'),
                                        fallback_group,
                                        face_details_by_id,
                                    )
                                )
                        continue

                    representative_faces = matched_group.get('representative_faces', [])
                    if not self._representative_faces_have_face_data(representative_faces):
                        representative_faces = appearance_representative_faces

                    if not representative_faces:
                        continue

                    faces.extend(
                        self._build_face_candidates(
                            video_uuid,
                            appearance,
                            representative_faces,
                            matched_group.get('person_uuid'),
                            matched_group,
                            face_details_by_id,
                        )
                    )
                
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

    def _build_face_candidates(
        self,
        video_uuid: str,
        appearance: Dict[str, Any],
        representative_faces: Any,
        person_uuid: Optional[Any],
        source_metadata: Optional[Dict[str, Any]] = None,
        face_details_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        for face in self._parse_representative_faces(representative_faces)[:3]:
            face_data = self._normalize_face_data(face, source_metadata, face_details_by_id)
            quality_score = face.get('quality_score', 0)

            person_label = str(person_uuid or 'unknown')
            logger.debug(
                f"  Person {person_label[:8]}: "
                f"quality={quality_score:.2f}, "
                f"frame={face_data.get('frame_number')}, "
                f"bbox={face_data.get('bbox')}"
            )

            candidates.append({
                'quality_score': quality_score,
                'bbox': face_data.get('bbox', []),
                'face_data': face_data,
                'video_uuid': video_uuid,
                'frame_number': face_data.get('frame_number'),
                'timestamp': face_data.get('timestamp'),
                'person_uuid': str(person_uuid or appearance.get('person_object_uuid', '')),
                'person_object_uuid': appearance.get('person_object_uuid', ''),
                'confidence': face_data.get('confidence'),
                'distance_from_camera': face_data.get('distance_from_camera'),
                'selection_rank': face.get('selection_rank', face.get('rank', 1))
            })

        return candidates

    def _normalize_face_data(
        self,
        face: Dict[str, Any],
        source_metadata: Optional[Dict[str, Any]] = None,
        face_details_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        face_data = dict(face.get('face_data') or {})
        source_metadata = source_metadata or {}
        face_details_by_id = face_details_by_id or {}
        face_id = face.get('face_id') or face_data.get('id')
        face_details = face_details_by_id.get(str(face_id)) if face_id else None

        frame_number = face_data.get('frame_number')
        if not self._is_valid_frame_number(frame_number):
            frame_number = face.get('frame_number')
            if not self._is_valid_frame_number(frame_number):
                frame_number = source_metadata.get('best_face_frame')
            if not self._is_valid_frame_number(frame_number) and face_details is not None:
                frame_number = face_details.get('frame_number')
            if self._is_valid_frame_number(frame_number):
                face_data['frame_number'] = frame_number

        if not face_data.get('bbox') or not self._is_valid_bbox(face_data.get('bbox')):
            bbox = face.get('bbox')
            if not bbox or not self._is_valid_bbox(bbox):
                bbox = source_metadata.get('best_face_bbox')
            if (not bbox or not self._is_valid_bbox(bbox)) and face_details is not None:
                bbox = face_details.get('bbox')
            if bbox and self._is_valid_bbox(bbox):
                face_data['bbox'] = bbox

        if face_data.get('frame_width') is None:
            frame_width = face.get('frame_width')
            if frame_width is None:
                frame_width = source_metadata.get('detect_frame_width')
            if frame_width is not None:
                face_data['frame_width'] = frame_width

        if face_data.get('frame_height') is None:
            frame_height = face.get('frame_height')
            if frame_height is None:
                frame_height = source_metadata.get('detect_frame_height')
            if frame_height is not None:
                face_data['frame_height'] = frame_height

        if face_data.get('timestamp') is None and face.get('timestamp') is not None:
            face_data['timestamp'] = face.get('timestamp')

        if face_data.get('confidence') is None and face.get('confidence') is not None:
            face_data['confidence'] = face.get('confidence')
        if face_data.get('confidence') is None and face_details is not None and face_details.get('confidence') is not None:
            face_data['confidence'] = face_details.get('confidence')

        if face_data.get('distance_from_camera') is None and face.get('distance_from_camera') is not None:
            face_data['distance_from_camera'] = face.get('distance_from_camera')

        if face_id and face_data.get('id') is None:
            face_data['id'] = face_id

        return face_data

    @staticmethod
    def _is_valid_bbox(bbox: Any) -> bool:
        return (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(value is not None for value in bbox)
            and float(bbox[2]) > float(bbox[0])
            and float(bbox[3]) > float(bbox[1])
        )

    @staticmethod
    def _is_valid_frame_number(frame_number: Any) -> bool:
        try:
            return int(frame_number) > 0
        except (TypeError, ValueError):
            return False

    async def _fetch_face_details_from_vision(self, video_uuid: str) -> Dict[str, Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {}
                if self.service_token:
                    headers['Authorization'] = f'Bearer {self.service_token}'

                response = await client.get(
                    f"{self.vision_url}/faces/media/{video_uuid}",
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("Failed to fetch Vision face details for video %s: %s", video_uuid[:8], exc)
            return {}

        if isinstance(payload, list):
            faces = payload
        elif isinstance(payload, dict):
            faces = payload.get('faces', []) or []
            if not faces:
                faces_by_frame = payload.get('faces_by_frame', {}) or {}
                faces = []
                for frame_faces in faces_by_frame.values():
                    if isinstance(frame_faces, list):
                        faces.extend(frame_faces)
        else:
            faces = []

        face_details_by_id: Dict[str, Dict[str, Any]] = {}
        for face in faces:
            if not isinstance(face, dict):
                continue
            face_id = face.get('id') or face.get('face_id')
            if not face_id:
                continue
            face_details_by_id[str(face_id)] = {
                'frame_number': face.get('frame_number'),
                'bbox': [
                    face.get('bbox_x1'),
                    face.get('bbox_y1'),
                    face.get('bbox_x2'),
                    face.get('bbox_y2'),
                ],
                'confidence': face.get('confidence'),
            }
        return face_details_by_id

    def _match_person_group_for_appearance(
        self,
        person_groups: List[Dict[str, Any]],
        person_object_uuid: Any,
        representative_faces: Any,
    ) -> Optional[Dict[str, Any]]:
        """Match an appearance row to its orchestrator person_group.

        Prefer a direct persisted person UUID match when the orchestrator is
        serving stored person groups. Fall back to representative-face
        geometry when the response came from live regrouping.
        """
        if not person_groups:
            return None

        if person_object_uuid:
            persisted_person_uuid = str(person_object_uuid)
            for group in person_groups:
                group_person_uuid = group.get('person_uuid')
                group_person_id = group.get('person_id')
                if group_person_uuid and str(group_person_uuid) == persisted_person_uuid:
                    return group
                if group_person_id and str(group_person_id) == persisted_person_uuid:
                    return group

        reference_face_ids = self._extract_face_ids_from_representative_faces(representative_faces)
        if reference_face_ids:
            for group in person_groups:
                group_face_ids = {
                    str(face_id)
                    for face_id in (group.get('all_face_ids') or [])
                    if face_id
                }
                if group_face_ids.intersection(reference_face_ids):
                    return group

        representative_faces = self._parse_representative_faces(representative_faces)

        ref_frame: Optional[int] = None
        ref_cx: Optional[float] = None
        ref_cy: Optional[float] = None

        faces = self._parse_representative_faces(representative_faces)
        if faces:
            face_data = (faces[0] or {}).get('face_data') or {}
            try:
                ref_frame = int(face_data['frame_number'])
            except (KeyError, TypeError, ValueError):
                pass
            try:
                ref_cx = float(face_data['center_x'])
                ref_cy = float(face_data.get('center_y') or 0.0)
            except (KeyError, TypeError, ValueError):
                pass

        if ref_frame is None and ref_cx is None:
            return None

        if ref_frame is not None and ref_cx is not None:
            for group in person_groups:
                route_points = (group.get('movement_tracking') or {}).get('route_points') or []
                for route_point in route_points:
                    if route_point.get('frame_number') == ref_frame:
                        if abs(float(route_point.get('center_x', 0)) - ref_cx) <= 2.0:
                            return group

        if ref_cx is not None and ref_cy is not None:
            best_group: Optional[Dict[str, Any]] = None
            best_distance = float('inf')
            for group in person_groups:
                route_points = (group.get('movement_tracking') or {}).get('route_points') or []
                for route_point in route_points:
                    dx = float(route_point.get('center_x', 0)) - ref_cx
                    dy = float(route_point.get('center_y', 0)) - ref_cy
                    distance = (dx * dx + dy * dy) ** 0.5
                    if distance < best_distance:
                        best_distance = distance
                        best_group = group
            if best_distance < 15.0:
                return best_group

        return None

    def _parse_representative_faces(self, representative_faces: Any) -> List[Dict[str, Any]]:
        if isinstance(representative_faces, str):
            try:
                representative_faces = json.loads(representative_faces)
            except (TypeError, ValueError):
                representative_faces = {}

        if isinstance(representative_faces, dict):
            faces = representative_faces.get('faces') or []
            if isinstance(faces, list):
                return [face for face in faces if isinstance(face, dict)]

        if isinstance(representative_faces, list):
            return [face for face in representative_faces if isinstance(face, dict)]

        return []

    def _extract_face_ids_from_representative_faces(self, representative_faces: Any) -> set[str]:
        face_ids: set[str] = set()
        for face in self._parse_representative_faces(representative_faces):
            face_id = face.get('face_id')
            if face_id:
                face_ids.add(str(face_id))

            face_data = face.get('face_data') or {}
            nested_face_id = face_data.get('id')
            if nested_face_id:
                face_ids.add(str(nested_face_id))

        return face_ids

    def _representative_faces_have_face_data(self, representative_faces: Any) -> bool:
        for face in self._parse_representative_faces(representative_faces):
            if isinstance(face.get('face_data'), dict) and face.get('face_data'):
                return True
        return False
    
    async def _fetch_frame_from_vision(
        self,
        video_uuid: str
    ) -> Optional[str]:
        """
        Get frame thumbnail URL for a video.
        Returns media service thumbnail endpoint.
        """
        return f"/api/v1/media/thumbnail/{video_uuid}"
