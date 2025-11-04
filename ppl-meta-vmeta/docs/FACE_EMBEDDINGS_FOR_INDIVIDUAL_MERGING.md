# Face Embeddings for Individual Merging - Technical Guide

**Document Version:** 1.0  
**Created:** November 3, 2025  
**Service:** ppl-meta-vmeta  
**Related Services:** ppl-meta-vision  
**Purpose:** Explain how to obtain face embeddings from cropped face images for merging duplicate individuals in cross-video tracking

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Context](#architecture-context)
3. [Face Crop Storage in Vision Service](#face-crop-storage-in-vision-service)
4. [Embedding Generation Process](#embedding-generation-process)
5. [Current Implementation in Individual Merging](#current-implementation-in-individual-merging)
6. [Step-by-Step Embedding Extraction](#step-by-step-embedding-extraction)
7. [Frontend Integration](#frontend-integration)
8. [Database Schema](#database-schema)
9. [Code Examples](#code-examples)
10. [Best Practices & Optimization](#best-practices--optimization)

---

## Overview

### What is Face Embedding?

A **face embedding** is a 512-dimensional numerical vector that represents unique facial features. The PPL Meta Platform uses **DeepFace with the Facenet512 model** to generate these embeddings. Each embedding acts as a "facial fingerprint" that can be compared mathematically to determine if two faces belong to the same person.

### Why Do We Need Embeddings for Individual Merging?

In cross-video tracking, individuals are initially grouped using spatial-temporal overlap algorithms (Union-Find). However, this can create duplicate individuals when the same person appears in different videos at different times without spatial overlap. Face embeddings solve this by:

1. **Providing biometric verification** beyond spatial/temporal heuristics
2. **Enabling similarity comparison** across video boundaries
3. **Merging duplicates** based on facial similarity (cosine similarity threshold)

### Key Components

- **Vision Service (`ppl-meta-vision`)**: Stores cropped face images in the `face_crops` table
- **vmeta Service (`ppl-meta-vmeta`)**: Contains the embedding service and merging logic
- **DeepFace Library**: Provides the Facenet512 model for embedding generation
- **PostgreSQL**: Stores face crops (base64) and individual records

---

## Architecture Context

### Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CROSS-VIDEO TRACKING FLOW                     │
└─────────────────────────────────────────────────────────────────┘

1. VIDEO PROCESSING (Vision Service)
   ├── Face Detection (HAAR + Dlib)
   ├── Face Crop Extraction (from bounding box)
   └── Store in face_crops table (base64 + quality_score)

2. PERSON OBJECT CREATION (Vision Service)
   ├── Group faces into person_objects
   ├── Select best_face_id (highest quality)
   └── Store person_object with metadata

3. CROSS-VIDEO INDIVIDUAL TRACKING (vmeta Service)
   ├── Phase 1-3: Spatial-temporal overlap detection
   ├── Phase 4: Create individuals from overlapping groups
   └── Phase 5: Merge duplicates using embeddings ← THIS DOCUMENT

4. EMBEDDING-BASED MERGING (vmeta Service)
   ├── For each individual:
   │   ├── Find person_object with highest quality
   │   ├── Retrieve face_crop from Vision DB
   │   ├── Generate embedding using DeepFace
   │   └── Store embedding for comparison
   ├── Compare all embeddings (cosine similarity)
   └── Merge individuals with similarity >= threshold
```

---

## Face Crop Storage in Vision Service

### Database Table: `face_crops`

Located in **Vision Service PostgreSQL database** (`ppl_vision_db`):

```sql
CREATE TABLE face_crops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    face_detection_id TEXT NOT NULL UNIQUE,  -- Links to face_detections.id
    crop_base64 TEXT,                         -- Base64-encoded JPEG face crop
    pre_computed_quality_score REAL,         -- Quality score (0.0 - 1.0)
    crop_width INTEGER,                       -- Crop width in pixels
    crop_height INTEGER,                      -- Crop height in pixels
    extracted_at TIMESTAMP DEFAULT NOW(),
    extraction_method TEXT DEFAULT 'bbox_coordinates'
);
```

### When Are Face Crops Created?

Face crops are created during **video processing** by the Vision Service:

1. **Face Detection**: HAAR cascade + Dlib validation detects faces in video frames
2. **Bounding Box Extraction**: Each face has coordinates `(x1, y1, x2, y2)`
3. **Crop Extraction**: The face region is cropped from the frame using the bounding box
4. **Quality Analysis**: A quality score is calculated based on:
   - Face size (larger is better)
   - Sharpness (Laplacian variance)
   - Brightness (optimal around 128)
   - Frontal orientation
5. **Base64 Encoding**: The crop is encoded as JPEG and stored as base64 string
6. **Database Storage**: Crop is stored in `face_crops` table with computed quality score

### Example Face Crop Record

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "face_detection_id": "face_vid123_frame042_det001",
  "crop_base64": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgG...",  // Truncated
  "pre_computed_quality_score": 0.87,
  "crop_width": 120,
  "crop_height": 160,
  "extracted_at": "2025-11-03T10:15:30.123456",
  "extraction_method": "bbox_coordinates"
}
```

---

## Embedding Generation Process

### DeepFace with Facenet512

The PPL Meta Platform uses **DeepFace library** with the **Facenet512 model**:

- **Model**: Facenet512 (pre-trained on millions of faces)
- **Output**: 512-dimensional float array (normalized values)
- **Format**: `numpy.ndarray` with shape `(512,)`
- **Storage**: Can be converted to Python list for JSON serialization

### Embedding Service (`ppl-meta-vmeta/src/services/embedding_service.py`)

The `EmbeddingService` class provides the core embedding generation functionality:

```python
class EmbeddingService:
    """
    Enhanced Vision Service with session-based face detection,
    distance calculation, and facial embeddings generation.
    """
    
    def __init__(self, database_client, config: dict = None):
        self.db = database_client
        self.embedding_model = config.get("embedding_model", "Facenet512")
        self.detector_backend = config.get("detector_backend", "opencv")
```

### Core Embedding Method

The private method `_generate_facial_embedding()` generates embeddings from face crops:

```python
async def _generate_facial_embedding(
    self, 
    frame: np.ndarray,      # The face crop image (already cropped)
    x: int,                 # X coordinate within crop (usually 0)
    y: int,                 # Y coordinate within crop (usually 0)
    width: int,             # Width of face region
    height: int             # Height of face region
) -> Tuple[Optional[List[float]], Optional[float]]:
    """
    Generate 512-dimensional facial embedding using DeepFace.
    
    Returns:
        Tuple of (embedding_vector, confidence_score)
    """
    
    if not DEEPFACE_AVAILABLE:
        return None, None
    
    try:
        # Extract face region (when processing a full frame)
        # For pre-cropped faces, use the entire image
        face_img = frame[y : y + height, x : x + width]
        
        # Convert BGR to RGB for DeepFace
        face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        
        # Generate embedding using DeepFace
        embedding_result = DeepFace.represent(
            img_path=face_rgb,              # Input image (numpy array)
            model_name=self.embedding_model, # "Facenet512"
            enforce_detection=False,         # Don't re-detect face
            detector_backend=self.detector_backend
        )
        
        if embedding_result and len(embedding_result) > 0:
            embedding = embedding_result[0]["embedding"]  # List of 512 floats
            
            # Calculate confidence based on face quality metrics
            confidence = self._calculate_embedding_confidence(face_img)
            
            return embedding, confidence
            
    except Exception as e:
        logger.warning(f"Failed to generate facial embedding: {e}")
    
    return None, None
```

### Embedding Confidence Calculation

Quality metrics determine the confidence of the embedding:

```python
def _calculate_embedding_confidence(self, face_img: np.ndarray) -> float:
    """
    Calculate embedding confidence based on face image quality.
    """
    
    try:
        height, width = face_img.shape[:2]
        
        # Size-based confidence (larger faces generally better)
        size_confidence = min(1.0, (width * height) / 10000)
        
        # Sharpness-based confidence (Laplacian variance)
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_confidence = min(1.0, sharpness / 1000)
        
        # Brightness-based confidence (optimal around 128)
        brightness = np.mean(gray)
        brightness_confidence = 1.0 - abs(brightness - 128) / 128
        
        # Combine metrics (weighted average)
        confidence = (
            size_confidence * 0.3 +
            sharpness_confidence * 0.4 +
            brightness_confidence * 0.3
        )
        
        return float(np.clip(confidence, 0.0, 1.0))
        
    except Exception as e:
        logger.error(f"Failed to calculate embedding confidence: {e}")
        return 0.5  # Default moderate confidence
```

---

## Current Implementation in Individual Merging

### Location

File: `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`  
Function: `merge_individuals_by_similarity()`

### High-Level Merging Flow

```
1. Extract representative face crops for each individual
   ├── Query individual's video appearances
   ├── Find person_object with highest quality score
   └── Retrieve face_crop from Vision DB

2. Generate embeddings for all individuals
   ├── Decode base64 face crop to image
   ├── Convert BGR to RGB
   ├── Call EmbeddingService._generate_facial_embedding()
   └── Store embedding for comparison

3. Calculate pairwise similarities
   ├── Build similarity matrix (cosine similarity)
   ├── Identify pairs with similarity >= threshold
   └── Group similar individuals

4. Merge duplicate individuals in database
   ├── Transfer appearances to kept individual
   ├── Delete merged individuals
   └── Update tracking session
```

### Function Signature

```python
async def merge_individuals_by_similarity(
    db_client,                        # Database client (vmeta DB)
    session_uuid: str,                # Tracking session UUID
    individual_uuids: List[str],      # List of individual UUIDs to compare
    auth_token: str,                  # Authorization token
    similarity_threshold: float = 0.75  # Minimum cosine similarity (0-1)
) -> int:
    """
    Merge individuals based on facial embedding similarity.
    
    Uses DeepFace/FaceNet embeddings to identify duplicate individuals
    across different video groups and merges them into single entities.
    
    Returns:
        Number of individuals merged (removed)
    """
```

---

## Step-by-Step Embedding Extraction

### Step 1: Retrieve Individual's Video Appearances

Query the vmeta database to find all videos where the individual appears:

```python
# Get all video UUIDs for this individual
video_appearances = await conn.fetch("""
    SELECT DISTINCT video_uuid
    FROM individual_video_appearances
    WHERE individual_uuid = $1
""", individual_uuid)

if not video_appearances:
    logger.warning(f"No appearances for individual {individual_uuid}")
    continue

video_uuids = [str(va['video_uuid']) for va in video_appearances]
```

### Step 2: Find Best Quality Person Object

Connect to the **Vision Service database** and find the person_object with the highest quality score:

```python
import asyncpg
import uuid

# Convert video UUIDs to PostgreSQL UUID array
video_uuid_objects = [uuid.UUID(v) for v in video_uuids]

# Connect to Vision DB
vision_conn_str = (
    "postgresql://postgres:localdevpass@localhost:5432/ppl_vision_db"
)
vision_conn = await asyncpg.connect(vision_conn_str)

try:
    # Get person_object with highest quality from these videos
    person_obj = await vision_conn.fetchrow("""
        SELECT 
            po.person_id,
            po.best_face_id,
            po.quality_score,
            fd.media_id
        FROM person_objects po
        JOIN face_detections fd 
            ON fd.id = po.best_face_id
        WHERE fd.media_id = ANY($1::uuid[])
          AND po.quality_score IS NOT NULL
        ORDER BY po.quality_score DESC
        LIMIT 1
    """, video_uuid_objects)
    
    if not person_obj or not person_obj['best_face_id']:
        logger.warning(f"No person_object with quality score found")
        continue
    
    best_face_id = person_obj['best_face_id']
    
finally:
    await vision_conn.close()
```

### Step 3: Retrieve Face Crop from Vision DB

Get the stored face crop from the `face_crops` table:

```python
# Get face crop from face_crops table
face_crop_data = await vision_conn.fetchrow("""
    SELECT crop_base64, crop_width, crop_height
    FROM face_crops
    WHERE face_detection_id = $1
""", best_face_id)

if not face_crop_data or not face_crop_data['crop_base64']:
    logger.warning(f"No face_crop for face {best_face_id}")
    continue
```

### Step 4: Decode Base64 Face Crop

Convert the base64 string back to an OpenCV image:

```python
import base64
import cv2
import numpy as np

# Decode base64 face crop
crop_bytes = base64.b64decode(face_crop_data['crop_base64'])
crop_array = np.frombuffer(crop_bytes, np.uint8)
face_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)

if face_crop is None or face_crop.size == 0:
    logger.warning(f"Failed to decode face crop for {best_face_id}")
    continue
```

### Step 5: Convert Color Space

DeepFace expects RGB images (OpenCV uses BGR):

```python
# Convert BGR to RGB for DeepFace
face_crop_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
```

### Step 6: Generate Embedding

Call the embedding service with the cropped face:

```python
from services.embedding_service import EmbeddingService

embedding_service = EmbeddingService(db_client)

# Generate DeepFace embedding from face crop
# Use full crop as bbox (face is already cropped)
h, w = face_crop_rgb.shape[:2]

embedding, embedding_confidence = await embedding_service._generate_facial_embedding(
    face_crop_rgb,  # The cropped face image (RGB)
    0,              # X offset (0 for pre-cropped)
    0,              # Y offset (0 for pre-cropped)
    w,              # Full width of crop
    h               # Full height of crop
)

if embedding is not None:
    # Store embedding for this individual
    individual_embeddings[individual_uuid] = embedding
    logger.info(f"✅ Generated embedding for individual {individual_uuid}")
```

### Step 7: Compare Embeddings

Once all embeddings are extracted, calculate pairwise similarities:

```python
from sklearn.metrics.pairwise import cosine_similarity

# Build similarity matrix
uuids = list(individual_embeddings.keys())
embeddings_matrix = np.array([
    individual_embeddings[uuid] for uuid in uuids
])

# Calculate pairwise cosine similarities
similarities = cosine_similarity(embeddings_matrix)

# Find individuals with similarity >= threshold
for i in range(len(uuids)):
    similar_indices = np.where(
        similarities[i] >= similarity_threshold
    )[0]
    
    # Filter out self-comparison
    similar_uuids = [
        uuids[j] for j in similar_indices
        if j != i
    ]
    
    if similar_uuids:
        # These individuals should be merged
        logger.info(f"Individual {uuids[i]} is similar to {similar_uuids}")
```

### Step 8: Execute Database Merge

Transfer appearances and delete duplicate individuals:

```python
async with db_client.pool.acquire() as conn:
    async with conn.transaction():
        for keep_uuid, merge_uuids in merge_groups:
            for merge_uuid in merge_uuids:
                # Transfer all appearances to kept individual
                await conn.execute("""
                    UPDATE individual_video_appearances
                    SET individual_uuid = $1
                    WHERE individual_uuid = $2
                """, keep_uuid, merge_uuid)
                
                # Delete merged individual
                await conn.execute("""
                    DELETE FROM individuals
                    WHERE individual_uuid = $1
                """, merge_uuid)
                
                logger.info(f"Merged individual {merge_uuid} into {keep_uuid}")
```

---

## Frontend Integration

### How Flutter Fetches Face Crops

#### 1. Collections Screen - Individuals Tab

**Location**: `http://localhost:3000/#/collections`  
**Screen**: Cross-video Individual Analysis  
**Tab**: Individuals

The Flutter app fetches **all appearances** for each individual from the `individual_video_appearances` table through the backend API:

```dart
// Endpoint called by Flutter
GET /api/v1/cross-video/individuals/{individual_uuid}/aggregated-analysis
    ?session_uuid={session_uuid}

// Response includes appearances
{
  "individual_uuid": "abc123...",
  "individual_id": "ind_001",
  "appearances": [
    {
      "individual_uuid": "abc123...",
      "video_uuid": "vid456...",
      "person_object_uuid": "po789...",
      "start_timestamp": "2025-11-03T10:00:00",
      "end_timestamp": "2025-11-03T10:05:00",
      "entry_bbox": [100, 150, 200, 350],
      "exit_bbox": [110, 160, 210, 360],
      "confidence_score": 0.92
    }
    // ... more appearances
  ],
  "total_appearances": 5,
  "total_videos": 2
}
```

#### 2. Media Preview - Person Objects Tab

**Location**: `http://localhost:3000/#/media-preview`  
**Screen**: Person Object Analysis  
**Tab**: Persons

The Flutter app displays the **best quality face** for each person object:

```dart
// File: lib/screens/person_objects_detail_screen.dart

Future<Widget> _buildCroppedFaceImageAsync(Map<String, dynamic> faceData) async {
  // Extract bounding box from face data
  final bbox = faceData['bbox'] as List<dynamic>?;
  
  if (bbox == null || bbox.length < 4) {
    // Fallback to full frame image
    return Image.network(frameUrl);
  }
  
  // Extract coordinates
  final x = bbox[0].toDouble();
  final y = bbox[1].toDouble();
  final x2 = bbox[2].toDouble();
  final y2 = bbox[3].toDouble();
  
  // Calculate expanded crop area (6.25x larger for better quality)
  final width = x2 - x;
  final height = y2 - y;
  final scaleFactor = math.sqrt(6.25);
  final expandedWidth = width * scaleFactor;
  final expandedHeight = height * scaleFactor;
  
  // Fetch and crop the frame image
  final frameUrl = 'http://localhost:8080/api/v1/media/${mediaUuid}/frame/$frameNumber';
  final croppedImage = await _cropImageFromNetwork(frameUrl, expandedX, expandedY, expandedWidth, expandedHeight);
  
  return croppedImage;
}
```

#### 3. Backend Support for Face Crops

The backend provides the face crop data through the Vision Service API:

```python
# Vision Service endpoint
GET /api/v1/faces/{face_id}/crop

# Returns base64 encoded face crop
{
  "face_id": "face_vid123_frame042_det001",
  "crop_base64": "/9j/4AAQSkZJRgABAQEAYABgAAD...",
  "width": 120,
  "height": 160,
  "quality_score": 0.87
}
```

---

## Database Schema

### Vision Service Database (`ppl_vision_db`)

#### Table: `face_crops`

```sql
CREATE TABLE face_crops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    face_detection_id TEXT NOT NULL UNIQUE,
    crop_base64 TEXT,
    pre_computed_quality_score REAL,
    crop_width INTEGER,
    crop_height INTEGER,
    extracted_at TIMESTAMP DEFAULT NOW(),
    extraction_method TEXT DEFAULT 'bbox_coordinates'
);

CREATE INDEX idx_face_crops_detection_id ON face_crops(face_detection_id);
CREATE INDEX idx_face_crops_quality ON face_crops(pre_computed_quality_score DESC);
```

#### Table: `person_objects`

```sql
CREATE TABLE person_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    media_id UUID NOT NULL,
    best_face_id TEXT,              -- Links to face_detections.id
    quality_score REAL,              -- Overall quality (0.0 - 1.0)
    face_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_person_objects_media ON person_objects(media_id);
CREATE INDEX idx_person_objects_quality ON person_objects(quality_score DESC);
```

### vmeta Service Database (`ppl_vmeta_db`)

#### Table: `individuals`

```sql
CREATE TABLE individuals (
    individual_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    individual_id TEXT NOT NULL,
    session_uuid UUID NOT NULL,
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_individuals_session ON individuals(session_uuid);
```

#### Table: `individual_video_appearances`

```sql
CREATE TABLE individual_video_appearances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid),
    video_uuid UUID NOT NULL,
    person_object_uuid UUID NOT NULL,
    start_timestamp TIMESTAMP,
    end_timestamp TIMESTAMP,
    entry_bbox REAL[],               -- [x1, y1, x2, y2]
    exit_bbox REAL[],                -- [x1, y1, x2, y2]
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_appearances_individual ON individual_video_appearances(individual_uuid);
CREATE INDEX idx_appearances_video ON individual_video_appearances(video_uuid);
```

---

## Code Examples

### Example 1: Extract Embedding from Face Crop

```python
async def extract_embedding_from_face_crop(
    face_detection_id: str,
    embedding_service: EmbeddingService
) -> Optional[List[float]]:
    """
    Extract embedding from a stored face crop in Vision DB.
    
    Args:
        face_detection_id: Face detection ID
        embedding_service: Initialized embedding service
        
    Returns:
        512-dimensional embedding or None
    """
    
    # Connect to Vision DB
    vision_conn = await asyncpg.connect(
        "postgresql://postgres:localdevpass@localhost:5432/ppl_vision_db"
    )
    
    try:
        # Get face crop
        crop_data = await vision_conn.fetchrow("""
            SELECT crop_base64
            FROM face_crops
            WHERE face_detection_id = $1
        """, face_detection_id)
        
        if not crop_data or not crop_data['crop_base64']:
            return None
        
        # Decode base64 to image
        crop_bytes = base64.b64decode(crop_data['crop_base64'])
        crop_array = np.frombuffer(crop_bytes, np.uint8)
        face_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)
        
        if face_crop is None:
            return None
        
        # Convert to RGB
        face_crop_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        
        # Generate embedding
        h, w = face_crop_rgb.shape[:2]
        embedding, _ = await embedding_service._generate_facial_embedding(
            face_crop_rgb, 0, 0, w, h
        )
        
        return embedding
        
    finally:
        await vision_conn.close()
```

### Example 2: Compare Two Individuals

```python
from sklearn.metrics.pairwise import cosine_similarity

async def compare_individuals(
    individual_uuid_1: str,
    individual_uuid_2: str,
    db_client,
    embedding_service: EmbeddingService
) -> float:
    """
    Compare two individuals using facial embeddings.
    
    Returns:
        Cosine similarity (0.0 to 1.0)
    """
    
    # Extract embeddings for both individuals
    embeddings = []
    
    for ind_uuid in [individual_uuid_1, individual_uuid_2]:
        # Get best face crop for individual
        face_id = await get_best_face_for_individual(ind_uuid, db_client)
        
        if not face_id:
            return 0.0
        
        # Extract embedding
        embedding = await extract_embedding_from_face_crop(
            face_id, embedding_service
        )
        
        if embedding is None:
            return 0.0
        
        embeddings.append(embedding)
    
    # Calculate cosine similarity
    similarity = cosine_similarity(
        [embeddings[0]], 
        [embeddings[1]]
    )[0][0]
    
    return float(similarity)
```

### Example 3: Batch Embedding Generation

```python
async def generate_embeddings_batch(
    individual_uuids: List[str],
    db_client,
    embedding_service: EmbeddingService,
    progress_callback=None
) -> Dict[str, np.ndarray]:
    """
    Generate embeddings for multiple individuals in batch.
    
    Args:
        individual_uuids: List of individual UUIDs
        db_client: Database client
        embedding_service: Embedding service instance
        progress_callback: Optional callback(current, total)
        
    Returns:
        Dict mapping individual_uuid to embedding array
    """
    
    embeddings = {}
    total = len(individual_uuids)
    
    for idx, ind_uuid in enumerate(individual_uuids):
        try:
            # Get best face for individual
            face_id = await get_best_face_for_individual(ind_uuid, db_client)
            
            if not face_id:
                logger.warning(f"No face found for individual {ind_uuid}")
                continue
            
            # Generate embedding
            embedding = await extract_embedding_from_face_crop(
                face_id, embedding_service
            )
            
            if embedding is not None:
                embeddings[ind_uuid] = np.array(embedding)
                logger.info(f"✅ Generated embedding {idx+1}/{total}")
            
            # Progress callback
            if progress_callback:
                progress_callback(idx + 1, total)
                
        except Exception as e:
            logger.error(f"Failed to generate embedding for {ind_uuid}: {e}")
            continue
    
    logger.info(f"Generated {len(embeddings)} embeddings out of {total} individuals")
    return embeddings
```

---

## Best Practices & Optimization

### 1. Quality Threshold

Only use face crops with quality scores above a threshold:

```python
MINIMUM_QUALITY_THRESHOLD = 0.6

person_obj = await vision_conn.fetchrow("""
    SELECT 
        po.person_id,
        po.best_face_id,
        po.quality_score
    FROM person_objects po
    WHERE po.quality_score >= $1
    ORDER BY po.quality_score DESC
    LIMIT 1
""", MINIMUM_QUALITY_THRESHOLD)
```

### 2. Caching Embeddings

Store generated embeddings to avoid re-computation:

```python
# Add embedding column to individuals table
ALTER TABLE individuals
ADD COLUMN face_embedding REAL[];  -- 512-element array

# Store embedding after generation
await conn.execute("""
    UPDATE individuals
    SET face_embedding = $1
    WHERE individual_uuid = $2
""", embedding, individual_uuid)

# Retrieve cached embedding
cached_embedding = await conn.fetchval("""
    SELECT face_embedding
    FROM individuals
    WHERE individual_uuid = $1
""", individual_uuid)
```

### 3. Batch Processing

Process embeddings in batches to improve performance:

```python
BATCH_SIZE = 10

for i in range(0, len(individual_uuids), BATCH_SIZE):
    batch = individual_uuids[i:i + BATCH_SIZE]
    
    # Process batch in parallel
    tasks = [
        extract_embedding_from_face_crop(face_id, embedding_service)
        for face_id in batch
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle results
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Batch item {idx} failed: {result}")
        else:
            embeddings[batch[idx]] = result
```

### 4. Similarity Threshold Tuning

Adjust the similarity threshold based on your use case:

```python
# Conservative (fewer false positives, may miss duplicates)
SIMILARITY_THRESHOLD_CONSERVATIVE = 0.85

# Moderate (balanced)
SIMILARITY_THRESHOLD_MODERATE = 0.75

# Aggressive (more merging, may have false positives)
SIMILARITY_THRESHOLD_AGGRESSIVE = 0.65
```

### 5. Error Handling

Implement robust error handling for production:

```python
try:
    embedding = await extract_embedding_from_face_crop(face_id, embedding_service)
    
except asyncpg.exceptions.PostgresError as e:
    logger.error(f"Database error: {e}")
    # Retry logic or fallback
    
except cv2.error as e:
    logger.error(f"OpenCV error (corrupt image?): {e}")
    # Skip this face crop
    
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Log for debugging
```

### 6. Performance Metrics

Track performance metrics for optimization:

```python
import time

start_time = time.time()

# Generate embeddings
embeddings = await generate_embeddings_batch(individual_uuids, db_client, embedding_service)

elapsed_time = time.time() - start_time
avg_time_per_embedding = elapsed_time / len(embeddings) if embeddings else 0

logger.info(f"Generated {len(embeddings)} embeddings in {elapsed_time:.2f}s")
logger.info(f"Average time per embedding: {avg_time_per_embedding:.3f}s")
```

### 7. Database Connection Pooling

Use connection pooling for Vision DB access:

```python
# Create connection pool (at service startup)
vision_pool = await asyncpg.create_pool(
    host='localhost',
    port=5432,
    user='postgres',
    password='localdevpass',
    database='ppl_vision_db',
    min_size=2,
    max_size=10
)

# Use pool in embedding extraction
async with vision_pool.acquire() as conn:
    crop_data = await conn.fetchrow("""
        SELECT crop_base64
        FROM face_crops
        WHERE face_detection_id = $1
    """, face_detection_id)
```

---

## Summary

### Key Takeaways

1. **Face crops are stored in Vision DB** (`face_crops` table) as base64-encoded images
2. **Embeddings are generated using DeepFace Facenet512** producing 512-dimensional vectors
3. **Best quality faces are selected** using pre-computed quality scores
4. **Cosine similarity is used** to compare embeddings (threshold typically 0.75)
5. **Merging happens in vmeta DB** by transferring appearances and deleting duplicates

### When to Use Embedding-Based Merging

- ✅ **After spatial-temporal grouping** (Phase 4 creates initial individuals)
- ✅ **When duplicates are suspected** (same person in different videos without overlap)
- ✅ **With high-quality face crops** (quality score >= 0.6)
- ✅ **For cross-video tracking** (individuals spanning multiple videos)

### Performance Considerations

- **Database queries**: Minimize round-trips by batching
- **Embedding generation**: Cache results to avoid re-computation
- **Connection pooling**: Reuse database connections
- **Error handling**: Gracefully handle missing or corrupt data
- **Threshold tuning**: Adjust based on false positive/negative rates

---

## Related Documentation

- [Cross-Video Individual Tracking Implementation](../docs/vision-vmeta/CROSS_VIDEO_INDIVIDUAL_ANALYSIS_IMPLEMENTATION.md)
- [Vision Service Data Formats](../docs/archive/vision-service/VIS-001.1.5-Data-Formats-and-Database-Schema.md)
- [Flutter Phase 5 & 6 Integration](../docs/vision-vmeta/FLUTTER_PHASE_5_6_INTEGRATION_COMPLETE.md)
- [Individual Creator Algorithm](../src/algorithms/individual_creator.py)
- [Embedding Service Source](../src/services/embedding_service.py)

---

**Document End**
