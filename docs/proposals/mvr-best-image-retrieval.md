# Proposal: MVRpeople Best Face & Frame Image Retrieval

**Date**: December 18, 2025  
**Version**: 2.0 (REVISED)  
**Status**: In Development  
**Author**: PPL Meta Platform Team

**🔄 MAJOR UPDATE (Dec 18, 2025)**: Revised after discovering actual working API architecture from media-preview screen analysis.

## Critical Discovery Summary

During implementation, we analyzed the working media-preview screen and discovered:

### ❌ Original Assumption (WRONG)
- Orchestrator has endpoint: `GET /api/v1/orchestrator/person-objects/{person_object_uuid}`
- Returns single person_object with face data
- VMeta calls this for each person_object

### ✅ Actual Reality (CORRECT)
- Orchestrator has endpoint: `GET /api/v1/orchestrator/person-objects/{media_id}`
- Takes **video UUID** (media_id), NOT person_object_uuid
- Returns ALL person_groups detected in that video
- Each group has `representative_faces[]` pre-ranked by quality_score (0-100)
- Face data includes bbox for client-side cropping, not pre-cropped image URLs

### 🔧 Implementation Impact
- Query `video_uuid` from `individual_video_appearances`, not `person_object_uuid`
- Group appearances by video to minimize API calls
- Call Orchestrator once per unique video
- Extract `representative_faces[0]` (highest quality) from response
- Compare across all videos to find global best face

## Executive Summary

This proposal outlines a new API endpoint in the VMeta service to retrieve the highest quality cropped face image and corresponding frame image for any MVRpeople UUID, including support for super-individuals with merged members.

## Problem Statement

Currently, there is no efficient way to:
1. Retrieve the best quality cropped face for an MVRpeople UUID
2. Get the corresponding frame image for context
3. Handle super-individuals (aggregate best image across all merged children)
4. Do this without cross-service database queries

## Requirements

### Functional Requirements
- **FR-1**: Retrieve best quality cropped face for given MVRpeople UUID
- **FR-2**: Return corresponding frame image for the same appearance
- **FR-3**: Support super-individual UUIDs (aggregate across merged children)
- **FR-4**: Use REST APIs between services (no direct database access)
- **FR-5**: Rank faces by quality score (Vision service provides 3 faces per appearance)

### Non-Functional Requirements
- **NFR-1**: Response time < 3 seconds for non-cached requests
- **NFR-2**: Response time < 50ms for cached requests
- **NFR-3**: Support concurrent requests without service degradation
- **NFR-4**: Graceful degradation if Vision service unavailable

## Architecture Overview

### **CRITICAL DISCOVERY** (Dec 18, 2025)

After analyzing the working media-preview screen, we discovered the correct API architecture:

**Working API Call Pattern**:
```
GET /api/v1/orchestrator/person-objects/{MEDIA_UUID}
```

**Key Findings**:
1. ✅ Orchestrator endpoint takes **media_id** (video UUID), NOT person_object_uuid
2. ✅ Response includes all person_groups detected in that video
3. ✅ Each person_group has `representative_faces` array with quality_score and bbox
4. ✅ Faces are already ranked by quality_score (highest first)
5. ✅ Face data includes bbox coordinates for client-side cropping
6. ❌ No REST endpoint exists for individual person_object_uuid lookups

**Response Structure**:
```json
{
  "success": true,
  "media_id": "ba281b95-d613-4f6c-b107-a0e56bc9c128",
  "total_persons": 1,
  "total_faces": 3,
  "person_groups": [
    {
      "person_uuid": "61d0c412-aab0-40f6-a00c-65a93d012538",
      "face_count": 3,
      "representative_faces": [
        {
          "face_data": {
            "id": "1d22be9b-0ed3-456a-966a-af648e42a21c",
            "bbox": [558, 199, 922, 563],
            "confidence": 0.5,
            "frame_number": 530,
            "distance_from_camera": 7.55
          },
          "quality_score": 45.518,  // 0-100 scale
          "selection_rank": 1
        }
      ]
    }
  ]
}
```

### Service Responsibilities (Corrected)

```
┌─────────────────────────────────────────────────────────┐
│                    VMeta Service                         │
│  - Query person_object_uuid → video_uuid mapping        │
│  - Call Orchestrator with media_id                      │
│  - Extract representative_faces from response           │
│  - Select highest quality_score face                    │
│  - Return bbox for client-side rendering                │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Orchestrator  │
                  │  - Media-based  │
                  │    person data  │
                  │  - Pre-computed │
                  │    quality      │
                  └─────────────────┘
```

### Data Flow (Corrected)

```
1. Client Request: GET /api/v1/mvr-people/{mvr_uuid}/best-image?include_merged=true

2. VMeta checks if super-individual:
   - Query mvr_merge_hierarchy for merged children
   - Collect all MVRpeople UUIDs (parent + children)

3. VMeta gets video appearances:
   - Query individual_mvr_mapping → individual_uuid
   - Query individual_video_appearances → video_uuid (NOT person_object_uuid)
   - Group by video_uuid, limit to top 20 by confidence

4. VMeta calls Orchestrator for each video:
   - GET /api/v1/orchestrator/person-objects/{media_id}
   - Response contains ALL person_groups in that video
   - Each group has representative_faces[] already ranked by quality_score

5. VMeta extracts best face across all videos:
   - Collect all representative_faces from all videos
   - Select face with highest quality_score (0-100 scale)
   - Return bbox for client-side rendering

6. Client renders face:
   - Fetch video: GET /api/v1/media/stream/{video_uuid}
   - Crop frame to bbox coordinates [x1, y1, x2, y2]
   - Display cropped face
```

**Key Differences from Original Proposal**:
- ❌ No individual person_object endpoint - use media-based endpoint
- ✅ Orchestrator pre-computes quality scores and ranking
- ✅ Face data includes bbox, not pre-cropped image URLs
- ✅ Client-side rendering from bbox coordinates
- ⚠️  Multiple API calls if MVR person appears in many videos (optimization needed)


## API Specification

### VMeta Service Endpoint

#### Get Best Images for MVRpeople

```http
GET /api/v1/mvr-people/{mvr_uuid}/best-image
```

**Path Parameters:**
- `mvr_uuid` (required): MVRpeople UUID or Super-individual UUID

**Query Parameters:**
- `include_merged` (optional, boolean, default: false): Include merged children if super-individual
- `use_cache` (optional, boolean, default: true): Use cached result if available

**Response Schema:**

```json
{
  "mvr_people_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "is_super_individual": true,
  "best_face": {
    "image_url": "https://storage/faces/abc123.jpg",
    "quality_score": 0.95,
    "person_object_uuid": "223e4567-e89b-12d3-a456-426614174000",
    "video_uuid": "323e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2025-12-18T10:30:45.123Z",
    "source_mvr_uuid": "423e4567-e89b-12d3-a456-426614174000"
  },
  "frame_image": {
    "image_url": "https://storage/frames/def456.jpg",
    "person_object_uuid": "223e4567-e89b-12d3-a456-426614174000",
    "video_uuid": "323e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2025-12-18T10:30:45.123Z"
  },
  "metadata": {
    "total_appearances_checked": 15,
    "total_mvr_checked": 3,
    "cache_hit": false,
    "processing_time_ms": 1250
  }
}
```

**Error Responses:**

```json
// 404 - MVRpeople not found
{
  "error": "MVRpeople not found",
  "mvr_uuid": "123e4567-e89b-12d3-a456-426614174000"
}

// 404 - No appearances found
{
  "error": "No appearances found for MVRpeople",
  "mvr_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "total_appearances": 0
}

// 503 - Vision service unavailable
{
  "error": "Vision service unavailable",
  "fallback_used": true,
  "best_face": null,
  "frame_image": null
}
```

### Working Orchestrator Endpoint (Dec 18, 2025 Discovery)

**CRITICAL**: Analysis of working media-preview screen revealed the actual API architecture.

#### Orchestrator Person Objects Endpoint

```http
GET /api/v1/orchestrator/person-objects/{media_id}
```

**Path Parameters:**
- `media_id` (required): Video/Media UUID (NOT person_object_uuid)

**Complete Response Structure:**
```json
{
  "success": true,
  "media_id": "ba281b95-d613-4f6c-b107-a0e56bc9c128",
  "total_persons": 1,
  "total_faces": 3,
  "status": "completed",
  "message": "Rectangle overlap detection with detailed person objects",
  "person_groups": [
    {
      "person_uuid": "61d0c412-aab0-40f6-a00c-65a93d012538",
      "person_id": "person_1",
      "face_count": 3,
      "representative_faces": [
        {
          "face_data": {
            "id": "1d22be9b-0ed3-456a-966a-af648e42a21c",
            "bbox": [558, 199, 922, 563],
            "bbox_x1": 558,
            "bbox_y1": 199,
            "bbox_x2": 922,
            "bbox_y2": 563,
            "confidence": 0.5,
            "method": "two_stage_haar_dlib",
            "timestamp": 17.666666,
            "frame_number": 530,
            "distance_from_camera": 7.55,
            "center_x": 740,
            "center_y": 381,
            "face_width": 364,
            "face_height": 364,
            "face_area": 132496
          },
          "quality_score": 45.518,
          "selection_rank": 1,
          "selection_criteria": {
            "distance_weight": 0.3,
            "confidence_weight": 0.3,
            "area_weight": 0.2,
            "position_weight": 0.2,
            "method": "composite_quality_scoring"
          }
        }
      ],
      "all_face_ids": ["face_470", "face_480", "face_530"],
      "average_confidence": 0.5,
      "quality_metrics": {
        "average_quality": 41.65,
        "max_quality": 45.52,
        "min_quality": 37.15
      }
    }
  ],
  "grouping_algorithm": "rectangle_overlap_detection",
  "iou_threshold": 0.3,
  "processing_time_ms": 39.19
}
```

**Key Response Fields for Our Use Case**:
- `person_groups[].representative_faces[]`: Already sorted by quality (highest first)
- `quality_score`: Float 0-100 scale (composite quality)
- `face_data.bbox`: [x1, y1, x2, y2] coordinates for client-side face cropping
- `face_data.frame_number`: Exact frame number where face appears
- `face_data.distance_from_camera`: Used in quality calculation
- `selection_rank`: Pre-computed ranking (1 = best quality)

**Important Architectural Notes**:
1. ✅ Endpoint is **media-centric**, not person_object-centric
2. ✅ Returns ALL person_groups detected in that video
3. ⚠️  VMeta must filter response to find specific person_object (if needed)
4. ✅ Quality scoring already computed by Orchestrator
5. ✅ Faces already ranked (selection_rank: 1 is best)
6. ❌ No pre-cropped image URLs provided
7. ✅ Client crops face using bbox coordinates and frame_number
8. ✅ **Enhanced Logic V2** retrieves persistent stored face data from Vision database
9. ✅ Returns 404 only if video has no face detection data stored

**How Enhanced Logic V2 Works**:
- Queries Vision database for stored face detection results
- If data exists, returns it immediately with distance calculations
- If no stored data, returns 404 (not an error - video simply has no faces)
- Data persists across sessions and restarts

**Implications for Our Implementation**:
- Query `individual_video_appearances` for `video_uuid` (not person_object_uuid)
- Group appearances by video to minimize API calls
- Call Orchestrator once per unique video
- Extract `representative_faces[0]` (highest quality) from each person_group
- Compare quality_scores across all videos to find global best
- **Note**: 404 from Orchestrator means video has no stored face data (skip it)

### ~~Required Vision Service Endpoints~~ (OBSOLETE)

**NOTE**: Original proposal assumed individual person_object endpoints existed. 
Discovery shows we must use media-based Orchestrator endpoint instead.

#### ~~1. Get Best Face for Person Object~~ (DOES NOT EXIST)

```http
GET /api/v1/person-objects/{person_object_uuid}/best-face
```

**Response:**
```json
{
  "person_object_uuid": "223e4567-e89b-12d3-a456-426614174000",
  "best_face": {
    "image_url": "https://storage/faces/abc123.jpg",
    "quality_score": 0.95,
    "face_index": 0
  },
  "all_faces": [
    {"image_url": "...", "quality_score": 0.95},
    {"image_url": "...", "quality_score": 0.87},
    {"image_url": "...", "quality_score": 0.73}
  ]
}
```

#### ~~2. Get Frame Image for Person Object~~ (DOES NOT EXIST)

```http
GET /api/v1/person-objects/{person_object_uuid}/frame
```

**Response:**
```json
{
  "person_object_uuid": "223e4567-e89b-12d3-a456-426614174000",
  "frame_image": {
    "image_url": "https://storage/frames/def456.jpg",
    "width": 1920,
    "height": 1080,
    "format": "jpg"
  }
}
```

**Alternative**: If these endpoints don't exist, VMeta can use existing endpoint:
```http
GET /api/v1/person-objects/{person_object_uuid}
```
Then extract and rank faces from response.

**✅ CORRECTION (Dec 18, 2025)**: Use Orchestrator media-based endpoint instead:
```http
GET /api/v1/orchestrator/person-objects/{media_id}
```
This endpoint exists and is proven to work in production (media-preview screen).

## Implementation Details (REVISED - Dec 18, 2025)

### Corrected Implementation Approach

**Key Changes from Original Proposal**:
1. Query `video_uuid` instead of `person_object_uuid` from database
2. Group appearances by `video_uuid` to minimize API calls  
3. Call Orchestrator with `media_id` (video UUID)
4. Parse response to extract `representative_faces[0]` (pre-ranked best quality)
5. Compare quality across all videos to find global best
6. Return bbox for client-side face cropping

### Revised Code Structure

```python
# services/mvr_image_manager.py (CORRECTED)

class MVRImageManager:
    def __init__(self, mvr_repo: MVRRepository, orchestrator_url: str):
        self.mvr_repo = mvr_repo
        self.orchestrator_url = orchestrator_url
        self.service_token = None  # TODO: Get from config
    
    async def get_best_images_for_mvr(
        self,
        mvr_uuid: str,
        include_merged: bool = False,
        use_cache: bool = True
    ) -> BestImageResponse:
        """Get best quality face for MVRpeople UUID."""
        
        # 1. Query video appearances (NOT person_objects)
        video_appearances = await self._get_video_appearances_for_mvr(
            mvr_uuid, 
            include_merged,
            limit=20
        )
        
        if not video_appearances:
            raise HTTPException(404, "No appearances found")
        
        # 2. Group by video_uuid to minimize API calls
        videos_by_uuid = {}
        for appearance in video_appearances:
            video_uuid = appearance['video_uuid']
            if video_uuid not in videos_by_uuid:
                videos_by_uuid[video_uuid] = []
            videos_by_uuid[video_uuid].append(appearance)
        
        # 3. Fetch face data from Orchestrator (parallel)
        tasks = [
            self._fetch_faces_from_orchestrator(video_uuid, appearances)
            for video_uuid, appearances in videos_by_uuid.items()
        ]
        face_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. Extract best face across all videos
        all_faces = []
        for result in face_results:
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch faces: {result}")
                continue
            if result:
                all_faces.extend(result)
        
        if not all_faces:
            raise HTTPException(404, "No face data found")
        
        # 5. Find highest quality face
        best_face = max(all_faces, key=lambda f: f['quality_score'])
        
        return BestImageResponse(
            mvr_people_uuid=mvr_uuid,
            best_face=BestFaceData(
                image_url=f"/api/v1/media/stream/{best_face['video_uuid']}",
                quality_score=best_face['quality_score'] / 100.0,  # Convert 0-100 to 0-1
                bbox=best_face['bbox'],
                face_data=best_face['face_data'],
                video_uuid=best_face['video_uuid'],
                frame_number=best_face['frame_number'],
                timestamp=best_face['timestamp']
            )
        )
    
    async def _get_video_appearances_for_mvr(
        self,
        mvr_uuid: str,
        include_merged: bool,
        limit: int = 20
    ) -> List[Dict]:
        """
        Query VMeta database for video appearances.
        
        Returns: List of {video_uuid, confidence, timestamp, individual_uuid}
        """
        # Get MVR UUIDs to check (parent + merged children if requested)
        mvr_uuids = [mvr_uuid]
        if include_merged:
            merged_children = await self.mvr_repo.get_merged_children(mvr_uuid)
            mvr_uuids.extend(merged_children)
        
        # Query individual_video_appearances
        query = """
            SELECT DISTINCT 
                iva.video_uuid,
                iva.confidence,
                iva.start_timestamp as timestamp,
                iva.individual_uuid
            FROM individual_video_appearances iva
            JOIN individual_mvr_mapping imm 
                ON iva.individual_uuid = imm.individual_uuid
            WHERE imm.mvr_people_uuid = ANY($1)
            ORDER BY iva.confidence DESC
            LIMIT $2
        """
        
        async with self.mvr_repo.db_pool.acquire() as conn:
            rows = await conn.fetch(query, mvr_uuids, limit)
        
        return [dict(row) for row in rows]
    
    async def _fetch_faces_from_orchestrator(
        self,
        video_uuid: str,
        appearances: List[Dict]
    ) -> List[Dict]:
        """
        Call Orchestrator API to get all person_groups in video.
        Extract representative faces and return with metadata.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.orchestrator_url}/api/v1/orchestrator/person-objects/{video_uuid}"
                headers = {}
                if self.service_token:
                    headers['Authorization'] = f'Bearer {self.service_token}'
                
                logger.debug(f"Fetching person data from Orchestrator: {video_uuid[:8]}...")
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    logger.warning(f"No person objects found for video {video_uuid[:8]}")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                if not data.get('success'):
                    logger.warning(f"Orchestrator returned success=false for {video_uuid[:8]}")
                    return []
                
                # Extract best face from each person_group
                faces = []
                person_groups = data.get('person_groups', [])
                
                for group in person_groups:
                    representative_faces = group.get('representative_faces', [])
                    if not representative_faces:
                        continue
                    
                    # First face is highest quality (pre-ranked by Orchestrator)
                    best_face = representative_faces[0]
                    face_data = best_face.get('face_data', {})
                    
                    faces.append({
                        'quality_score': best_face.get('quality_score', 0),
                        'bbox': face_data.get('bbox', []),
                        'face_data': face_data,
                        'video_uuid': video_uuid,
                        'frame_number': face_data.get('frame_number'),
                        'timestamp': face_data.get('timestamp'),
                        'person_uuid': group.get('person_uuid'),
                        'confidence': face_data.get('confidence'),
                        'distance_from_camera': face_data.get('distance_from_camera')
                    })
                
                logger.info(f"Extracted {len(faces)} faces from video {video_uuid[:8]}")
                return faces
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching faces for video {video_uuid[:8]}")
            return []
        except Exception as e:
            logger.error(f"Error fetching faces for video {video_uuid[:8]}: {e}")
            return []
```

### Performance Optimization

**Problem**: If MVR person appears in 10 videos, we make 10 API calls.

**Solution**: Limit to top N videos by confidence (already done with `LIMIT 20`).

**Future Enhancement**: Orchestrator could add batch endpoint:
```http
POST /api/v1/orchestrator/person-objects/batch
{
  "media_ids": ["uuid1", "uuid2", "uuid3"]
}
```

## Database Schema Changes

### New Columns for mvr_people Table

```sql
-- Add caching columns for best images
ALTER TABLE mvr_people 
ADD COLUMN best_face_url TEXT,
ADD COLUMN best_face_quality FLOAT,
ADD COLUMN best_face_person_object_uuid UUID,
ADD COLUMN best_frame_url TEXT,
ADD COLUMN best_images_updated_at TIMESTAMP,
ADD COLUMN best_images_metadata JSONB;

-- Index for cache lookups
CREATE INDEX idx_mvr_people_best_images_updated 
ON mvr_people(mvr_people_uuid, best_images_updated_at) 
WHERE best_images_updated_at IS NOT NULL;
```

### Cache Metadata Schema

```json
{
  "total_appearances_checked": 15,
  "source_mvr_uuids": ["uuid1", "uuid2"],
  "video_uuid": "uuid",
  "timestamp": "ISO8601",
  "cached_at": "ISO8601"
}
```

## Implementation Details

### Phase 1: Basic Endpoint (Week 1)

**Goal**: Working endpoint without caching

**Tasks**:
1. Create `services/mvr_image_manager.py`
2. Implement `get_best_images_for_mvr()` method
3. Add database queries for person_objects
4. Implement Vision service REST API calls
5. Add endpoint to `routes/mvr_people.py`
6. Unit tests

**Code Structure**:

```python
# services/mvr_image_manager.py

class MVRImageManager:
    def __init__(self, db_pool, vision_service_url: str):
        self.db_pool = db_pool
        self.vision_service_url = vision_service_url
    
    async def get_best_images_for_mvr(
        self,
        mvr_uuid: str,
        include_merged: bool = False,
        use_cache: bool = True
    ) -> BestImageResponse:
        """
        Get best quality face and frame for MVRpeople.
        """
        # Step 1: Get all MVR UUIDs to check
        mvr_uuids = await self._get_mvr_uuids_to_check(
            mvr_uuid, include_merged
        )
        
        # Step 2: Get person_object_uuids for these MVRs
        person_objects = await self._get_person_objects_for_mvr(
            mvr_uuids, limit=20
        )
        
        # Step 3: Fetch face data from Vision service
        best_face = await self._find_best_face(person_objects)
        
        # Step 4: Fetch frame for best face
        frame_data = await self._fetch_frame_from_vision(
            best_face['person_object_uuid']
        )
        
        return BestImageResponse(
            mvr_people_uuid=mvr_uuid,
            is_super_individual=include_merged,
            best_face=best_face,
            frame_image=frame_data,
            metadata={...}
        )
    
    async def _get_person_objects_for_mvr(
        self,
        mvr_uuids: List[str],
        limit: int = 20
    ) -> List[Dict]:
        """Query individual_video_appearances for person_objects."""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT DISTINCT 
                    iva.person_object_uuid,
                    iva.video_uuid,
                    iva.start_timestamp,
                    iva.confidence,
                    imm.mvr_people_uuid
                FROM individual_video_appearances iva
                JOIN individual_mvr_mapping imm 
                    ON iva.individual_uuid = imm.individual_uuid
                WHERE imm.mvr_people_uuid = ANY($1::uuid[])
                ORDER BY iva.confidence DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, mvr_uuids, limit)
            return [dict(row) for row in rows]
    
    async def _fetch_best_face_from_vision(
        self,
        person_object_uuid: str
    ) -> Dict:
        """Call Vision service REST API for best face."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{self.vision_service_url}/api/v1/person-objects/"
                f"{person_object_uuid}/best-face",
                headers={"Authorization": f"Bearer {self.service_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def _find_best_face(
        self,
        person_objects: List[Dict]
    ) -> Dict:
        """Fetch all faces and return highest quality."""
        best_face = None
        best_quality = 0.0
        
        # Use asyncio.gather for parallel API calls
        tasks = [
            self._fetch_best_face_from_vision(obj['person_object_uuid'])
            for obj in person_objects
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch face: {result}")
                continue
                
            if result['best_face']['quality_score'] > best_quality:
                best_quality = result['best_face']['quality_score']
                best_face = {
                    'image_url': result['best_face']['image_url'],
                    'quality_score': best_quality,
                    'person_object_uuid': person_objects[idx]['person_object_uuid'],
                    'video_uuid': person_objects[idx]['video_uuid'],
                    'timestamp': person_objects[idx]['start_timestamp'].isoformat(),
                    'source_mvr_uuid': person_objects[idx]['mvr_people_uuid']
                }
        
        return best_face
```

### Phase 2: Super-Individual Support (Week 2)

**Goal**: Aggregate across merged children

**Tasks**:
1. Implement `_get_merged_children()` method
2. Query mvr_merge_hierarchy table
3. Aggregate results across all MVRpeople
4. Add integration tests for super-individuals

**Code**:
```python
async def _get_mvr_uuids_to_check(
    self,
    mvr_uuid: str,
    include_merged: bool
) -> List[str]:
    """Get all MVR UUIDs to check (parent + children if super-individual)."""
    mvr_uuids = [mvr_uuid]
    
    if include_merged:
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT merged_mvr_uuid 
                FROM mvr_merge_hierarchy 
                WHERE super_individual_uuid = $1
            """
            rows = await conn.fetch(query, uuid.UUID(mvr_uuid))
            children = [str(row['merged_mvr_uuid']) for row in rows]
            mvr_uuids.extend(children)
            
            logger.info(
                f"Super-individual {mvr_uuid[:8]} has "
                f"{len(children)} merged children"
            )
    
    return mvr_uuids
```

### Phase 3: Caching (Week 3)

**Goal**: Sub-100ms response times for cached results

**Tasks**:
1. Add cache columns to mvr_people table
2. Implement cache read/write logic
3. Add cache invalidation on new appearances
4. Add cache invalidation on MVR merges
5. Add TTL logic (24 hours)
6. Performance testing

**Cache Logic**:
```python
async def get_best_images_for_mvr(
    self,
    mvr_uuid: str,
    include_merged: bool = False,
    use_cache: bool = True
) -> BestImageResponse:
    """Get best images with caching support."""
    
    # Check cache first
    if use_cache:
        cached = await self._get_cached_images(mvr_uuid)
        if cached and self._is_cache_valid(cached):
            logger.info(f"Cache hit for MVR {mvr_uuid[:8]}")
            return cached
    
    # Cache miss - compute result
    result = await self._compute_best_images(mvr_uuid, include_merged)
    
    # Update cache
    await self._update_cache(mvr_uuid, result)
    
    return result

async def _update_cache(
    self,
    mvr_uuid: str,
    result: BestImageResponse
) -> None:
    """Update cache in mvr_people table."""
    async with self.db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE mvr_people
            SET best_face_url = $1,
                best_face_quality = $2,
                best_face_person_object_uuid = $3,
                best_frame_url = $4,
                best_images_updated_at = NOW(),
                best_images_metadata = $5
            WHERE mvr_people_uuid = $6
        """,
            result.best_face['image_url'],
            result.best_face['quality_score'],
            result.best_face['person_object_uuid'],
            result.frame_image['image_url'],
            json.dumps(result.metadata),
            uuid.UUID(mvr_uuid)
        )

def _is_cache_valid(self, cached: Dict) -> bool:
    """Check if cache is still valid (24h TTL)."""
    cache_age = datetime.utcnow() - cached['best_images_updated_at']
    return cache_age.total_seconds() < 86400  # 24 hours
```

### Phase 4: Optimization (Week 4)

**Goal**: Handle high load, improve performance

**Tasks**:
1. Add Redis cache layer for hot MVRpeople
2. Implement parallel API calls (asyncio.gather)
3. Add circuit breaker for Vision service
4. Optimize database queries with indexes
5. Add monitoring and metrics
6. Load testing

## Performance Analysis

### Without Caching

**Scenario**: Super-individual with 3 merged children, 15 total appearances

```
1. Query mvr_merge_hierarchy:           5ms
2. Query individual_video_appearances:  10ms
3. Fetch 15 faces from Vision:          15 × 100ms = 1500ms (parallel: 200ms)
4. Fetch 1 frame from Vision:           100ms
5. Processing & ranking:                5ms
----------------------------------------
Total (sequential):                     1620ms
Total (parallel):                       320ms
```

### With Database Cache

```
1. Query mvr_people cache:              5ms
2. Validate cache:                      1ms
----------------------------------------
Total:                                  6ms
```

### With Redis Cache

```
1. Redis GET:                           1ms
----------------------------------------
Total:                                  1ms
```

## Cache Invalidation Strategy

### Triggers for Cache Invalidation

1. **New Appearance Added**:
   - When new person_object linked to individual
   - Invalidate cache for that MVRpeople
   - Invalidate cache for parent super-individual

2. **MVR Merge Event**:
   - When two MVRpeople merged
   - Invalidate both source MVR caches
   - Invalidate winner/super-individual cache

3. **TTL Expiration**:
   - After 24 hours
   - Lazy invalidation (check on read)

4. **Manual Invalidation**:
   - Admin endpoint: `DELETE /api/v1/mvr-people/{uuid}/cache`

## Frontend Integration

### Usage Example

```dart
// lib/services/mvr_image_service.dart

class MVRImageService {
  final ApiClient _apiClient;
  
  Future<BestImageResponse> getBestImages(
    String mvrUuid, {
    bool includeMerged = false,
    bool useCache = true,
  }) async {
    final response = await _apiClient.get(
      '/api/v1/mvr-people/$mvrUuid/best-image',
      queryParameters: {
        'include_merged': includeMerged,
        'use_cache': useCache,
      },
    );
    
    return BestImageResponse.fromJson(response.data);
  }
}

// Usage in UI
final imageService = ref.watch(mvrImageServiceProvider);
final images = await imageService.getBestImages(
  mvrUuid,
  includeMerged: true,
);

// Display
CircleAvatar(
  backgroundImage: NetworkImage(images.bestFace.imageUrl),
  radius: 50,
)

Image.network(images.frameImage.imageUrl)
```

### Integration into Existing UI Screens

#### 1. Cross-Video Analysis Screen Integration

**Current State**: 
- Displays MVRpeople with frame images only
- Uses `person_objects_detail_screen.dart`
- Shows route data across multiple videos

**Enhanced with Face Thumbnails**:

```dart
// lib/screens/person_objects_detail_screen.dart

class PersonObjectDetailScreen extends ConsumerStatefulWidget {
  // ... existing code ...
}

class _PersonObjectDetailScreenState extends ConsumerState<PersonObjectDetailScreen> {
  Map<String, BestImageResponse?> _mvrFaceThumbnails = {};
  
  @override
  void initState() {
    super.initState();
    _loadFaceThumbnails();
  }
  
  Future<void> _loadFaceThumbnails() async {
    // Get all unique MVR UUIDs from the analysis results
    final mvrUuids = _extractMvrUuidsFromResults();
    
    final imageService = ref.read(mvrImageServiceProvider);
    
    for (final mvrUuid in mvrUuids) {
      try {
        final images = await imageService.getBestImages(
          mvrUuid,
          includeMerged: true,  // Include super-individual merged faces
          useCache: true,
        );
        
        setState(() {
          _mvrFaceThumbnails[mvrUuid] = images;
        });
      } catch (e) {
        logger.error('Failed to load face for MVR $mvrUuid: $e');
      }
    }
  }
  
  Widget _buildPersonCard(PersonGroup personGroup) {
    final mvrUuid = personGroup.mvrPersonUuid;
    final faceData = _mvrFaceThumbnails[mvrUuid];
    
    return Card(
      child: ListTile(
        // Face thumbnail as leading avatar
        leading: CircleAvatar(
          radius: 30,
          backgroundColor: Colors.grey[300],
          backgroundImage: faceData?.bestFace?.imageUrl != null
              ? NetworkImage(faceData!.bestFace!.imageUrl)
              : null,
          child: faceData?.bestFace?.imageUrl == null
              ? Icon(Icons.person, size: 30)
              : null,
        ),
        
        // MVR info
        title: Text('Person ${personGroup.personId}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('MVR: ${mvrUuid.substring(0, 8)}...'),
            if (faceData?.bestFace?.qualityScore != null)
              Text(
                'Face Quality: ${(faceData!.bestFace!.qualityScore * 100).toStringAsFixed(1)}%',
                style: TextStyle(fontSize: 12, color: Colors.green),
              ),
            Text('Appearances: ${personGroup.totalAppearances}'),
            Text('Videos: ${personGroup.videoUuids.length}'),
          ],
        ),
        
        // Expand to show route details
        trailing: Icon(Icons.expand_more),
        onTap: () => _showPersonDetails(personGroup, faceData),
      ),
    );
  }
  
  void _showPersonDetails(PersonGroup personGroup, BestImageResponse? faceData) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 800,
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header with face and frame
              Row(
                children: [
                  // Face thumbnail
                  if (faceData?.bestFace?.imageUrl != null)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.network(
                        faceData!.bestFace!.imageUrl,
                        width: 120,
                        height: 120,
                        fit: BoxFit.cover,
                      ),
                    ),
                  
                  SizedBox(width: 16),
                  
                  // Frame image
                  if (faceData?.frameImage?.imageUrl != null)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.network(
                        faceData!.frameImage!.imageUrl,
                        width: 240,
                        height: 120,
                        fit: BoxFit.cover,
                      ),
                    ),
                  
                  Spacer(),
                  
                  // Stats
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        'Quality: ${(faceData?.bestFace?.qualityScore ?? 0) * 100}%',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text('Appearances: ${personGroup.totalAppearances}'),
                      Text('Videos: ${personGroup.videoUuids.length}'),
                    ],
                  ),
                ],
              ),
              
              SizedBox(height: 24),
              
              // Route visualization (existing code)
              Expanded(
                child: _buildRouteVisualization(personGroup),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

**UI Layout**:

```
╔══════════════════════════════════════════════════════════╗
║ Cross-Video Analysis Results                             ║
╠══════════════════════════════════════════════════════════╣
║ ┌─────────────────────────────────────────────────────┐  ║
║ │ [👤 Face]  Person 1                                 │  ║
║ │           MVR: b24ad688...                          │  ║
║ │           Face Quality: 95.3%                       │  ║
║ │           Appearances: 25 | Videos: 2               │  ║
║ └─────────────────────────────────────────────────────┘  ║
║                                                           ║
║ ┌─────────────────────────────────────────────────────┐  ║
║ │ [👤 Face]  Person 2                                 │  ║
║ │           MVR: 5a7c3d91...                          │  ║
║ │           Face Quality: 87.5%                       │  ║
║ │           Appearances: 12 | Videos: 1               │  ║
║ └─────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════╝

[Expanded View]
╔══════════════════════════════════════════════════════════╗
║ Person Details                                      [X]   ║
╠══════════════════════════════════════════════════════════╣
║                                                           ║
║  ┌──────────┐  ┌─────────────────┐  Quality: 95.3%     ║
║  │          │  │                 │  Appearances: 25     ║
║  │ [Face]   │  │  [Frame Image]  │  Videos: 2           ║
║  │ 120x120  │  │   240x120       │                      ║
║  └──────────┘  └─────────────────┘                      ║
║                                                           ║
║  Route Visualization:                                    ║
║  ┌─────────────────────────────────────────────────┐    ║
║  │        [Map with route points]                  │    ║
║  │                                                  │    ║
║  └─────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════╝
```

#### 2. Individual Groups Screen Integration

**Current State**:
- Lists group members
- Shows member count and metadata
- Uses `individual_groups_screen.dart`

**Enhanced with Face Thumbnails**:

```dart
// lib/screens/individual_groups_screen.dart

class IndividualGroupsScreen extends ConsumerStatefulWidget {
  // ... existing code ...
}

class _IndividualGroupsScreenState extends ConsumerState<IndividualGroupsScreen> {
  
  Widget _buildMembersList(List<GroupMember> members) {
    return ListView.builder(
      itemCount: members.length,
      itemBuilder: (context, index) {
        final member = members[index];
        return _buildMemberCard(member);
      },
    );
  }
  
  Widget _buildMemberCard(GroupMember member) {
    return FutureBuilder<BestImageResponse?>(
      future: _loadMemberFace(member.mvrPeopleUuid),
      builder: (context, snapshot) {
        final faceData = snapshot.data;
        
        return Card(
          margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            // Face thumbnail with quality indicator
            leading: Stack(
              children: [
                CircleAvatar(
                  radius: 30,
                  backgroundColor: Colors.grey[300],
                  backgroundImage: faceData?.bestFace?.imageUrl != null
                      ? NetworkImage(faceData!.bestFace!.imageUrl)
                      : null,
                  child: faceData?.bestFace?.imageUrl == null
                      ? Icon(Icons.person, size: 30)
                      : null,
                ),
                
                // Quality badge
                if (faceData?.bestFace?.qualityScore != null)
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      padding: EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        color: _getQualityColor(faceData!.bestFace!.qualityScore),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.check,
                        size: 12,
                        color: Colors.white,
                      ),
                    ),
                  ),
              ],
            ),
            
            title: Text(member.name ?? 'Member ${member.mvrPeopleUuid.substring(0, 8)}'),
            
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('MVR: ${member.mvrPeopleUuid.substring(0, 8)}...'),
                if (faceData?.bestFace?.qualityScore != null)
                  Text(
                    'Quality: ${(faceData!.bestFace!.qualityScore * 100).toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 12,
                      color: _getQualityColor(faceData.bestFace!.qualityScore),
                    ),
                  ),
                Text('Appearances: ${member.totalAppearances ?? 0}'),
              ],
            ),
            
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Frame thumbnail preview
                if (faceData?.frameImage?.imageUrl != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: Image.network(
                      faceData!.frameImage!.imageUrl,
                      width: 60,
                      height: 40,
                      fit: BoxFit.cover,
                    ),
                  ),
                
                SizedBox(width: 8),
                
                IconButton(
                  icon: Icon(Icons.remove_circle_outline, color: Colors.red),
                  onPressed: () => _removeMember(member),
                ),
              ],
            ),
            
            onTap: () => _showMemberDetails(member, faceData),
          ),
        );
      },
    );
  }
  
  Future<BestImageResponse?> _loadMemberFace(String mvrUuid) async {
    try {
      final imageService = ref.read(mvrImageServiceProvider);
      return await imageService.getBestImages(
        mvrUuid,
        includeMerged: true,  // Get best face across merged MVRpeople
        useCache: true,
      );
    } catch (e) {
      logger.error('Failed to load face for member $mvrUuid: $e');
      return null;
    }
  }
  
  Color _getQualityColor(double qualityScore) {
    if (qualityScore >= 0.9) return Colors.green;
    if (qualityScore >= 0.7) return Colors.orange;
    return Colors.red;
  }
  
  void _showMemberDetails(GroupMember member, BestImageResponse? faceData) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 600,
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Member Details',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              
              SizedBox(height: 24),
              
              // Face and frame images side by side
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Best quality face
                  Column(
                    children: [
                      if (faceData?.bestFace?.imageUrl != null)
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.network(
                            faceData!.bestFace!.imageUrl,
                            width: 200,
                            height: 200,
                            fit: BoxFit.cover,
                          ),
                        ),
                      SizedBox(height: 8),
                      Text(
                        'Best Face',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'Quality: ${(faceData?.bestFace?.qualityScore ?? 0) * 100}%',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                  
                  SizedBox(width: 24),
                  
                  // Context frame
                  Column(
                    children: [
                      if (faceData?.frameImage?.imageUrl != null)
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.network(
                            faceData!.frameImage!.imageUrl,
                            width: 300,
                            height: 200,
                            fit: BoxFit.cover,
                          ),
                        ),
                      SizedBox(height: 8),
                      Text(
                        'Context Frame',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      if (faceData?.frameImage?.timestamp != null)
                        Text(
                          _formatTimestamp(faceData!.frameImage!.timestamp),
                          style: TextStyle(fontSize: 12),
                        ),
                    ],
                  ),
                ],
              ),
              
              SizedBox(height: 24),
              
              // Member metadata
              _buildMetadataSection(member, faceData),
              
              SizedBox(height: 24),
              
              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text('Close'),
                  ),
                  SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: () => _viewFullHistory(member),
                    icon: Icon(Icons.history),
                    label: Text('View Full History'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildMetadataSection(GroupMember member, BestImageResponse? faceData) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildMetadataRow('MVR UUID', member.mvrPeopleUuid),
          _buildMetadataRow('Total Appearances', '${member.totalAppearances ?? 0}'),
          _buildMetadataRow('Added to Group', _formatDate(member.addedDate)),
          if (faceData?.metadata != null) ...[
            Divider(),
            Text('Image Metadata', style: TextStyle(fontWeight: FontWeight.bold)),
            _buildMetadataRow('Appearances Checked', '${faceData!.metadata!.totalAppearancesChecked}'),
            _buildMetadataRow('Source Video', faceData.bestFace!.videoUuid.substring(0, 8) + '...'),
            _buildMetadataRow('Captured At', _formatTimestamp(faceData.bestFace!.timestamp)),
          ],
        ],
      ),
    );
  }
  
  Widget _buildMetadataRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.grey[700])),
          Text(value, style: TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
```

**UI Layout**:

```
╔══════════════════════════════════════════════════════════╗
║ Individual Group: VIP Customers                          ║
╠══════════════════════════════════════════════════════════╣
║ Members (2)                                              ║
║                                                           ║
║ ┌─────────────────────────────────────────────────────┐  ║
║ │ [👤 Face ✓] Member 1                        [Frame] │  ║
║ │            MVR: b24ad688...                     [X] │  ║
║ │            Quality: 95.3%                           │  ║
║ │            Appearances: 25                          │  ║
║ └─────────────────────────────────────────────────────┘  ║
║                                                           ║
║ ┌─────────────────────────────────────────────────────┐  ║
║ │ [👤 Face ✓] Member 2                        [Frame] │  ║
║ │            MVR: 5a7c3d91...                     [X] │  ║
║ │            Quality: 87.5%                           │  ║
║ │            Appearances: 12                          │  ║
║ └─────────────────────────────────────────────────────┘  ║
║                                                           ║
║ [+ Add Members]  [🔍 Search in Camera]                   ║
╚══════════════════════════════════════════════════════════╝

[Member Details Dialog]
╔══════════════════════════════════════════════════════════╗
║ Member Details                                      [X]   ║
╠══════════════════════════════════════════════════════════╣
║                                                           ║
║     ┌──────────┐        ┌─────────────────┐             ║
║     │          │        │                 │             ║
║     │  [Face]  │        │ [Context Frame] │             ║
║     │  200x200 │        │    300x200      │             ║
║     └──────────┘        └─────────────────┘             ║
║      Best Face            Context Frame                 ║
║    Quality: 95.3%      Dec 18, 2025 10:30              ║
║                                                           ║
║  ┌─────────────────────────────────────────────────┐    ║
║  │ MVR UUID:             b24ad688...               │    ║
║  │ Total Appearances:    25                        │    ║
║  │ Added to Group:       Dec 10, 2025              │    ║
║  │ ─────────────────────────────────────────────   │    ║
║  │ Image Metadata                                  │    ║
║  │ Appearances Checked:  15                        │    ║
║  │ Source Video:         6e729029...               │    ║
║  │ Captured At:          Dec 18, 2025 10:30        │    ║
║  └─────────────────────────────────────────────────┘    ║
║                                                           ║
║                        [Close] [📜 View Full History]    ║
╚══════════════════════════════════════════════════════════╝
```

### Preloading Strategy for Performance

To avoid UI lag, preload face thumbnails:

```dart
// Preload all faces when group is opened
class _IndividualGroupsScreenState extends ConsumerState<IndividualGroupsScreen> {
  final Map<String, BestImageResponse?> _faceThumbnailCache = {};
  
  @override
  void initState() {
    super.initState();
    _preloadAllFaces();
  }
  
  Future<void> _preloadAllFaces() async {
    final members = await _fetchGroupMembers();
    final imageService = ref.read(mvrImageServiceProvider);
    
    // Batch load all faces in parallel
    final futures = members.map((member) async {
      try {
        final images = await imageService.getBestImages(
          member.mvrPeopleUuid,
          includeMerged: true,
          useCache: true,
        );
        _faceThumbnailCache[member.mvrPeopleUuid] = images;
      } catch (e) {
        _faceThumbnailCache[member.mvrPeopleUuid] = null;
      }
    }).toList();
    
    await Future.wait(futures);
    setState(() {}); // Rebuild with cached images
  }
}
```

### Image Caching Configuration

```dart
// lib/core/config/image_cache_config.dart

class ImageCacheConfig {
  static void configure() {
    // Increase image cache for face thumbnails
    PaintingBinding.instance.imageCache.maximumSize = 500;
    PaintingBinding.instance.imageCache.maximumSizeBytes = 100 * 1024 * 1024; // 100MB
  }
}
```

### Fallback Handling

```dart
Widget _buildFaceThumbnail(String? imageUrl, {double radius = 30}) {
  return CircleAvatar(
    radius: radius,
    backgroundColor: Colors.grey[300],
    child: imageUrl != null
        ? CachedNetworkImage(
            imageUrl: imageUrl,
            imageBuilder: (context, imageProvider) => Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                image: DecorationImage(
                  image: imageProvider,
                  fit: BoxFit.cover,
                ),
              ),
            ),
            placeholder: (context, url) => CircularProgressIndicator(
              strokeWidth: 2,
            ),
            errorWidget: (context, url, error) => Icon(
              Icons.person,
              size: radius,
              color: Colors.grey[600],
            ),
          )
        : Icon(
            Icons.person,
            size: radius,
            color: Colors.grey[600],
          ),
  );
}

## Test Data

**Test MVR UUIDs (Known to have appearances):**
- `b24ad688-26f0-4e1e-9484-4fecec18df9c` 
- `27627db6-71bb-4ee5-a6d8-883a3bc35aab`

**Test Individual Group:**
- `grp_9e3fd3d2995f` (contains above MVR people as members)

Use these UUIDs for endpoint testing and validation.

---

## Testing Strategy

### Unit Tests
- [ ] Test MVR UUID collection (single, super-individual)
- [ ] Test person_object query logic
- [ ] Test face ranking algorithm
- [ ] Test cache read/write/invalidation
- [ ] Test error handling (Vision service down)

### Integration Tests
- [ ] Test full flow: MVR UUID → images
- [ ] Test super-individual aggregation
- [ ] Test cache hit/miss scenarios
- [ ] Test parallel API calls
- [ ] Test Vision service timeout handling

### Performance Tests
- [ ] Load test: 100 concurrent requests
- [ ] Measure cache hit rate
- [ ] Measure response time distribution
- [ ] Test with large super-individuals (10+ children)

## Monitoring & Metrics

### Key Metrics

1. **Latency**:
   - P50, P95, P99 response times
   - Cached vs non-cached

2. **Cache Performance**:
   - Cache hit rate
   - Cache size
   - Invalidation frequency

3. **Vision Service**:
   - API call success rate
   - API call latency
   - Circuit breaker trips

4. **Business Metrics**:
   - Total images served
   - Unique MVRpeople accessed
   - Super-individual ratio

## Security Considerations

1. **Authentication**: All Vision service calls use service-to-service JWT tokens
2. **Authorization**: Check user permissions before returning images
3. **Rate Limiting**: Prevent abuse of image endpoint
4. **Image URLs**: Use signed URLs with expiration
5. **PII Protection**: Ensure face images comply with privacy regulations

## Rollout Plan

### Week 1: Development
- Implement Phase 1 (basic endpoint)
- Unit tests
- Code review

### Week 2: Testing
- Integration tests
- Internal testing with sample data
- Performance baseline

### Week 3: Beta
- Deploy to staging
- Beta testing with select users
- Monitor performance

### Week 4: Production
- Deploy Phase 1 to production
- Monitor metrics
- Gather feedback

### Week 5-6: Enhancements
- Implement Phase 2 (super-individuals)
- Implement Phase 3 (caching)
- Performance optimization

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Vision service downtime | High | Medium | Circuit breaker, fallback to cached data |
| Slow API calls | Medium | High | Parallel requests, aggressive caching |
| Cache invalidation bugs | Medium | Low | Comprehensive testing, monitoring |
| High memory usage | Low | Medium | Limit concurrent requests, pagination |
| Image storage costs | Medium | Low | CDN caching, image compression |

## Success Criteria

1. **Performance**: 
   - < 3s for non-cached requests
   - < 50ms for cached requests
   - 95%+ cache hit rate after warmup

2. **Reliability**:
   - 99.9% uptime
   - Graceful degradation on Vision service failure

3. **Adoption**:
   - Used by frontend for MVRpeople display
   - Integrated into Individual Groups UI
   - Positive user feedback

## Future Enhancements

1. **Batch Endpoint**: Get best images for multiple MVRpeople in one call
2. **Thumbnail Variants**: Return multiple image sizes
3. **Video Clips**: Return short video clip instead of frame
4. **Face Recognition**: Compare uploaded image with MVRpeople
5. **Quality Improvement**: ML model to predict best face angle/lighting

## Conclusion

This proposal provides a comprehensive solution for retrieving the best quality face and frame images for MVRpeople, with proper separation of concerns across services, aggressive caching for performance, and support for super-individual aggregation. The phased implementation approach allows for incremental delivery and validation.

## Appendix

### A. Related Documentation
- [MVR Architecture](../architecture/mvr-architecture.md)
- [Vision Service API](../api/vision-service.md)
- [Database Schema](../database/schema.md)

### B. API Examples

**Example 1: Get best image for single MVRpeople**
```bash
curl -X GET "http://localhost:8008/api/v1/mvr-people/123e4567-e89b-12d3-a456-426614174000/best-image" \
  -H "Authorization: Bearer $TOKEN"
```

**Example 2: Get best image for super-individual (includes merged children)**
```bash
curl -X GET "http://localhost:8008/api/v1/mvr-people/123e4567-e89b-12d3-a456-426614174000/best-image?include_merged=true" \
  -H "Authorization: Bearer $TOKEN"
```

**Example 3: Force cache refresh**
```bash
curl -X GET "http://localhost:8008/api/v1/mvr-people/123e4567-e89b-12d3-a456-426614174000/best-image?use_cache=false" \
  -H "Authorization: Bearer $TOKEN"
```

### C. Database Indexes

```sql
-- Optimize person_object queries
CREATE INDEX idx_individual_video_appearances_mvr_lookup 
ON individual_video_appearances(individual_uuid, confidence DESC);

-- Optimize super-individual queries
CREATE INDEX idx_mvr_merge_hierarchy_super_lookup 
ON mvr_merge_hierarchy(super_individual_uuid);

-- Optimize cache queries
CREATE INDEX idx_mvr_people_cache_lookup 
ON mvr_people(mvr_people_uuid, best_images_updated_at) 
WHERE best_images_updated_at IS NOT NULL;
```

---

**Review Status**: ⏳ Pending Review  
**Approved By**: _______________________  
**Approval Date**: _______________________
