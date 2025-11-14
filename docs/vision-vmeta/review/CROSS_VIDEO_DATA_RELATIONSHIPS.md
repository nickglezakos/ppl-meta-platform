# Cross-Video Individual Tracking - Data Relationships
**PPL Meta Platform v2.19.13+**  
**Date:** October 24, 2025

## Overview
The Cross-Video Individual Tracking system uses a multi-layered data architecture to track individuals across multiple videos. Here's how the data objects relate to each other:

## Data Flow Architecture

```
Videos → Person Objects → Individuals → Cross-Video Tracking
   ↓           ↓              ↓              ↓
Cache    Appearance     Signatures    Session Results
```

## Core Data Entities

### 1. Videos (Source Data)
- **Source:** External media files in collections (e.g., "usb camera 0")
- **Identification:** `video_uuid` 
- **Content:** Raw video recordings with timestamps
- **Role:** Primary data source for person detection

### 2. Person Objects (Extracted Features)
- **Storage:** `cached_person_objects` table
- **Purpose:** Extracted person detection data from individual videos
- **Key Fields:**
  - `cache_key`: Hash of (video_uuid, config_hash) - unique identifier
  - `video_uuid`: Links back to source video
  - `person_objects`: JSONB array of detected person instances
  - `config_hash`: Algorithm configuration used for detection
  - `processing_metadata`: Additional detection information

**Person Object Structure (JSONB):**
```json
{
  "person_object_uuid": "uuid",
  "confidence": 0.85,
  "bounding_boxes": [
    {"timestamp": "00:01:23", "bbox": [x1, y1, x2, y2]},
    {"timestamp": "00:01:24", "bbox": [x1, y1, x2, y2]}
  ],
  "facial_embeddings": [...],
  "movement_pattern": {...},
  "appearance_features": {...}
}
```

### 3. Individuals (Cross-Video Entities)
- **Storage:** `individuals` table  
- **Purpose:** Unified identity across multiple videos/person objects
- **Key Fields:**
  - `individual_uuid`: Unique identifier for the tracked individual
  - `individual_id`: Human-readable identifier (e.g., "person_2_videos")
  - `confidence_score`: Overall matching confidence (0.0 to 1.0)
  - `spatial_signature`: JSONB of characteristic spatial patterns
  - `temporal_signature`: JSONB of movement and timing patterns

### 4. Individual Video Appearances (Relationships)
- **Storage:** `individual_video_appearances` table
- **Purpose:** Links individuals to their appearances in specific videos
- **Key Fields:**
  - `individual_uuid`: References the tracked individual
  - `video_uuid`: References the source video
  - `person_object_uuid`: References the specific person object
  - `start_timestamp`/`end_timestamp`: Time range of appearance
  - `entry_bbox`/`exit_bbox`: First and last face rectangles
  - `confidence_score`: Confidence of this appearance match

## Relationship Flow

### Step 1: Video Processing
1. **Input:** Video files from collections
2. **Process:** Person detection algorithms extract person objects
3. **Output:** `cached_person_objects` entries with detected persons

### Step 2: Cross-Video Analysis  
1. **Input:** Person objects from multiple videos
2. **Process:** Cross-video tracking algorithm analyzes:
   - Facial embedding similarity
   - Spatial movement patterns
   - Temporal appearance sequences
   - Bounding box overlaps
3. **Output:** Groups of person objects belonging to same individual

### Step 3: Individual Creation
1. **Input:** Grouped person objects
2. **Process:** Create unified individual identity with:
   - Aggregated confidence score
   - Computed spatial signature (characteristic patterns)
   - Computed temporal signature (movement behaviors)
3. **Output:** `individuals` table entry

### Step 4: Appearance Linking
1. **Input:** Individual and contributing person objects
2. **Process:** Create appearance records linking:
   - Individual to each source video
   - Individual to specific person objects
   - Timeline information (start/end times)
   - Spatial information (entry/exit positions)
3. **Output:** `individual_video_appearances` entries

## Example Relationship

For your test case with 2 consecutive videos:

```
Video A (7b462847-cd1f-441a-8bd9-aaed6643b7cb)
   └── Person Object A1 (detected person with confidence 0.85)
       └── Bounding boxes: [(0:10, [100,200,150,300]), (0:15, [105,205,155,305])]

Video B (38f80c41-e0af-41fc-882d-f7ff79abd43d)  
   └── Person Object B1 (detected person with confidence 0.80)
       └── Bounding boxes: [(0:05, [110,210,160,310]), (0:10, [115,215,165,315])]

Cross-Video Analysis:
   └── Determines Person Object A1 and B1 are same individual
       └── Individual I1 created with confidence 0.825 (average)
           ├── Appearance 1: Video A, Person Object A1, 0:10-0:15
           └── Appearance 2: Video B, Person Object B1, 0:05-0:10
```

## Database Queries

### Get Individual's Complete Journey
```sql
SELECT 
    i.individual_id,
    i.confidence_score,
    iva.video_uuid,
    iva.start_timestamp,
    iva.end_timestamp,
    cpo.person_objects
FROM individuals i
JOIN individual_video_appearances iva ON i.individual_uuid = iva.individual_uuid  
JOIN cached_person_objects cpo ON iva.person_object_uuid = cpo.video_uuid
WHERE i.individual_uuid = 'target-uuid'
ORDER BY iva.start_timestamp;
```

### Get All Individuals in Session
```sql
SELECT 
    ts.session_uuid,
    COUNT(DISTINCT si.individual_uuid) as individuals_found,
    COUNT(DISTINCT iva.video_uuid) as videos_involved
FROM tracking_sessions ts
JOIN session_individuals si ON ts.session_uuid = si.session_uuid
JOIN individual_video_appearances iva ON si.individual_uuid = iva.individual_uuid
WHERE ts.session_uuid = 'session-uuid'
GROUP BY ts.session_uuid;
```

## Key Design Principles

1. **Separation of Concerns:**
   - Person objects = what was detected in each video
   - Individuals = who the person is across videos
   - Appearances = when/where individuals appeared

2. **Traceability:**
   - Every individual can be traced back to source videos
   - Every appearance links to specific person objects
   - All processing metadata is preserved

3. **Flexibility:**
   - JSONB fields allow complex signature storage
   - Cache keys enable efficient reprocessing
   - Confidence scores enable quality filtering

4. **Performance:**
   - Cached person objects avoid reprocessing videos
   - Hash-based cache keys enable quick lookups
   - Indexed relationships enable fast queries

## Algorithm Integration

The cross-video tracking algorithm:
1. **Loads** person objects from cache for target videos
2. **Compares** facial embeddings, spatial patterns, temporal sequences
3. **Groups** similar person objects using configurable thresholds
4. **Creates** individual records with computed signatures
5. **Links** individuals to appearances across all videos

This architecture enables efficient cross-video person tracking while maintaining full traceability from detection results back to source videos.