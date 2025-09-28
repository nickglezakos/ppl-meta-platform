# PPL Thread Workflow Implementation Document

## Overview

This document outlines the implementation of the **PPL Thread Workflow**, a second-level person objects workflow that extends the PPL Meta Vision Service with advanced face grouping capabilities. The workflow applies the exact same face grouping processes from the autonomous PPL Meta Mini application, creating "person objects" from existing face detection data.

---

## Design Principles

### 1. **Autonomous Mini Preservation**
- **Zero Dependencies**: The PPL Meta Mini application remains completely autonomous
- **No Code Sharing**: Implementation creates independent modules to avoid coupling
- **Separate Codebase**: All functionality implemented as new Vision Service modules

### 2. **Data Structure Consistency**
- **Identical Output Format**: Person objects match PPL Meta Mini's individual data structure exactly
- **Compatible Response Format**: Results follow the same JSON schema as FaceGroupingEngine output
- **Consistent Metadata**: Quality scores, age detection, and distance calculations preserved

### 3. **Existing Infrastructure Integration**
- **Vision Service Extension**: New module integrated into existing PPL Meta Vision Service
- **Database Layer**: Utilizes existing face detection storage and session management
- **Workflow Orchestration**: Leverages current workflow architecture and traceability

---

## Implementation Phases

## Phase 1: Database Schema Extension

### 1.1 Person Objects Table Structure

Create new database tables to store person objects and their relationships:

```sql
-- Person objects table (main entities)
CREATE TABLE person_objects (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    face_count INTEGER NOT NULL,
    average_position_x REAL NOT NULL,
    average_position_y REAL NOT NULL,
    quality_score REAL NOT NULL,
    best_face_id TEXT,
    estimated_age INTEGER,
    distance_from_camera REAL,
    tracking_algorithm TEXT DEFAULT 'percentage_based_tracking',
    tolerance_percent REAL DEFAULT 20.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_uuid) REFERENCES face_detection_sessions(session_uuid)
);

-- Person-to-face mappings
CREATE TABLE person_face_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    face_detection_id TEXT NOT NULL,
    match_type TEXT NOT NULL, -- 'tracked' or 'new_track'
    match_distance REAL,
    frame_number INTEGER,
    position_x REAL NOT NULL,
    position_y REAL NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (person_id) REFERENCES person_objects(person_id),
    FOREIGN KEY (face_detection_id) REFERENCES face_detections(id)
);

-- Person workflow tracking
CREATE TABLE person_workflows (
    workflow_id TEXT PRIMARY KEY,
    session_uuid TEXT NOT NULL,
    status TEXT DEFAULT 'processing', -- 'processing', 'completed', 'failed'
    input_face_count INTEGER NOT NULL,
    output_person_count INTEGER DEFAULT 0,
    tolerance_percent REAL DEFAULT 20.0,
    processing_method TEXT DEFAULT 'percentage_based_tracking',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB,
    FOREIGN KEY (session_uuid) REFERENCES face_detection_sessions(session_uuid)
);

-- Indexes for performance
CREATE INDEX idx_person_objects_session_uuid ON person_objects(session_uuid);
CREATE INDEX idx_person_objects_workflow_id ON person_objects(workflow_id);
CREATE INDEX idx_person_face_mappings_person_id ON person_face_mappings(person_id);
CREATE INDEX idx_person_face_mappings_face_id ON person_face_mappings(face_detection_id);
CREATE INDEX idx_person_workflows_session_uuid ON person_workflows(session_uuid);
```

### 1.2 Database Migration Module

Create database migration handler:

```python
# ppl-meta-vision/src/database/person_objects_migrations.py

class PersonObjectsMigration:
    """Handle database schema migration for person objects functionality."""
    
    def __init__(self, database_connection):
        self.connection = database_connection
        
    async def migrate_schema(self):
        """Execute schema migration for person objects tables."""
        # Implementation for creating tables and indexes
        pass
        
    async def check_migration_status(self):
        """Check if migration has been applied."""
        pass
        
    async def rollback_migration(self):
        """Rollback person objects schema changes."""
        pass
```

---

## Phase 2: Core Face Grouping Engine

### 2.1 Independent Face Grouping Implementation

Create a new, independent implementation of the face grouping algorithm:

```python
# ppl-meta-vision/src/person_objects/face_grouping_engine.py

import cv2
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

class VisionFaceGroupingEngine:
    """
    Independent face grouping engine for PPL Meta Vision Service.
    
    Implements the same percentage-based tolerance matching algorithm
    as PPL Meta Mini's FaceGroupingEngine, but as a completely separate
    implementation to maintain mini's autonomy.
    """
    
    def __init__(self):
        self.tolerance_percent = 20.0
        self.quality_weights = {
            'sharpness': 0.4,
            'exposure': 0.3, 
            'contrast': 0.2,
            'noise': 0.1
        }
    
    def calculate_quality_score(self, image_crop: np.ndarray) -> float:
        """
        Calculate image quality score using the same metrics as PPL Meta Mini.
        
        Metrics:
        - Sharpness (40%): Laplacian variance
        - Exposure (30%): Histogram distribution analysis
        - Contrast (20%): Dynamic range calculation
        - Noise (10%): Standard deviation analysis (inverted)
        """
        if image_crop.size == 0:
            return 0.0
            
        # Convert to grayscale if needed
        if len(image_crop.shape) == 3:
            gray = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_crop
            
        # Sharpness calculation (Laplacian variance)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        normalized_sharpness = min(sharpness / 1000.0, 1.0)
        
        # Exposure calculation (histogram analysis)
        mean_intensity = np.mean(gray)
        exposure_score = 1.0 / (1.0 + abs(mean_intensity - 128) / 128)
        
        # Contrast calculation (dynamic range)
        contrast = gray.max() - gray.min()
        normalized_contrast = contrast / 255.0
        
        # Noise calculation (inverted standard deviation)
        noise_level = np.std(gray)
        noise_score = max(0, 1.0 - (noise_level / 128.0))
        
        # Weighted combination
        quality_score = (
            self.quality_weights['sharpness'] * normalized_sharpness +
            self.quality_weights['exposure'] * exposure_score +
            self.quality_weights['contrast'] * normalized_contrast +
            self.quality_weights['noise'] * noise_score
        )
        
        return min(max(quality_score, 0.0), 1.0)
    
    def calculate_position_distance(self, pos1: Dict, pos2: Dict) -> Dict[str, float]:
        """
        Calculate position-based distance with percentage tolerance matching.
        
        Returns dictionary with:
        - x_distance: Absolute X coordinate difference
        - y_distance: Absolute Y coordinate difference  
        - euclidean_distance: Geometric distance
        - combined_distance: Weighted combination
        - within_tolerance: Boolean indicating if within 20% tolerance
        """
        x1, y1 = pos1['x'], pos1['y']
        x2, y2 = pos2['x'], pos2['y']
        
        # Calculate absolute differences
        x_distance = abs(x1 - x2)
        y_distance = abs(y1 - y2)
        
        # Calculate percentage-based tolerances
        x_tolerance = x1 * (self.tolerance_percent / 100.0)
        y_tolerance = y1 * (self.tolerance_percent / 100.0)
        
        # Check if within tolerance thresholds
        x_within_tolerance = x_distance <= x_tolerance
        y_within_tolerance = y_distance <= y_tolerance
        
        # Calculate Euclidean distance
        euclidean_distance = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
        
        # Calculate combined distance metric (weighted)
        combined_distance = (x_distance * 0.3 + y_distance * 0.3 + euclidean_distance * 0.4)
        
        return {
            'x_distance': x_distance,
            'y_distance': y_distance,
            'euclidean_distance': euclidean_distance,
            'combined_distance': combined_distance,
            'within_tolerance': x_within_tolerance and y_within_tolerance,
            'x_tolerance_used': x_tolerance,
            'y_tolerance_used': y_tolerance
        }
    
    async def apply_percentage_based_tracking(
        self, 
        face_detections: List[Dict], 
        tolerance_percent: float = 20.0
    ) -> Dict[str, Any]:
        """
        Apply the same percentage-based tracking algorithm as PPL Meta Mini.
        
        Args:
            face_detections: List of face detection records from database
            tolerance_percent: Position matching tolerance percentage
            
        Returns:
            Dictionary with person objects and tracking statistics
        """
        self.tolerance_percent = tolerance_percent
        
        # Group face detections by frame number for chronological processing
        frames_with_faces = {}
        for face in face_detections:
            frame_num = face.get('frame_number', 0)
            if frame_num not in frames_with_faces:
                frames_with_faces[frame_num] = []
            frames_with_faces[frame_num].append(face)
        
        # Sort frames chronologically
        sorted_frames = sorted(frames_with_faces.keys())
        
        # Initialize tracking state
        active_tracks = {}  # track_id -> track_info
        person_objects = []
        face_mappings = []
        next_person_id = 1
        tracked_faces = 0
        new_faces = 0
        
        # Process each frame chronologically
        for frame_number in sorted_frames:
            frame_faces = frames_with_faces[frame_number]
            
            for face in frame_faces:
                face_position = {
                    'x': face.get('position_x', face.get('bbox_x1', 0)),
                    'y': face.get('position_y', face.get('bbox_y1', 0))
                }
                
                # Find best matching active track
                best_match = None
                best_distance = float('inf')
                
                for track_id, track_info in active_tracks.items():
                    track_position = track_info['position']
                    distance_data = self.calculate_position_distance(
                        face_position, track_position
                    )
                    
                    if (distance_data['within_tolerance'] and 
                        distance_data['combined_distance'] < best_distance):
                        best_match = track_id
                        best_distance = distance_data['combined_distance']
                
                if best_match is not None:
                    # Update existing track
                    active_tracks[best_match]['position'] = face_position
                    active_tracks[best_match]['last_seen_frame'] = frame_number
                    active_tracks[best_match]['face_count'] += 1
                    
                    # Record face mapping
                    face_mappings.append({
                        'person_id': best_match,
                        'face_detection_id': face['id'],
                        'match_type': 'tracked',
                        'match_distance': best_distance,
                        'frame_number': frame_number,
                        'position_x': face_position['x'],
                        'position_y': face_position['y']
                    })
                    
                    tracked_faces += 1
                    
                else:
                    # Create new track
                    person_id = f"person_{next_person_id}"
                    next_person_id += 1
                    
                    active_tracks[person_id] = {
                        'person_id': person_id,
                        'position': face_position,
                        'last_seen_frame': frame_number,
                        'face_count': 1,
                        'first_face_id': face['id']
                    }
                    
                    # Record face mapping  
                    face_mappings.append({
                        'person_id': person_id,
                        'face_detection_id': face['id'],
                        'match_type': 'new_track',
                        'match_distance': 0.0,
                        'frame_number': frame_number,
                        'position_x': face_position['x'],
                        'position_y': face_position['y']
                    })
                    
                    new_faces += 1
        
        # Create person objects from final tracks
        for track_id, track_info in active_tracks.items():
            # Calculate average position from all mapped faces
            person_faces = [fm for fm in face_mappings if fm['person_id'] == track_id]
            avg_x = sum(fm['position_x'] for fm in person_faces) / len(person_faces)
            avg_y = sum(fm['position_y'] for fm in person_faces) / len(person_faces)
            
            person_objects.append({
                'person_id': track_id,
                'face_count': track_info['face_count'],
                'average_position': {'x': avg_x, 'y': avg_y},
                'tracking_algorithm': 'percentage_based_tracking',
                'tolerance_percent': tolerance_percent,
                'original_face_ids': [fm['face_detection_id'] for fm in person_faces]
            })
        
        return {
            'person_objects': person_objects,
            'face_mappings': face_mappings,
            'statistics': {
                'total_faces': len(face_detections),
                'total_persons': len(person_objects),
                'tracked_faces': tracked_faces,
                'new_faces': new_faces,
                'frames_processed': len(sorted_frames),
                'tolerance_percent': tolerance_percent,
                'algorithm': 'percentage_based_tracking'
            }
        }
```

### 2.2 Quality Analysis and Age Detection Module

```python
# ppl-meta-vision/src/person_objects/quality_analyzer.py

import cv2
import numpy as np
from typing import Dict, List, Any, Optional

class PersonQualityAnalyzer:
    """
    Analyze face image quality and detect age for person objects.
    Independent implementation matching PPL Meta Mini functionality.
    """
    
    def __init__(self):
        self.deepface_available = False
        try:
            from deepface import DeepFace
            self.deepface_available = True
            self.deepface = DeepFace
        except ImportError:
            pass
    
    async def find_best_quality_faces_per_person(
        self, 
        person_objects: List[Dict], 
        session_uuid: str,
        database: 'VisionDatabase'
    ) -> Dict[str, Dict]:
        """
        Find the best quality face image per person using stored face data.
        
        This is internal Vision Service functionality that uses existing
        face detection data without requiring external frame extraction.
        
        Args:
            person_objects: List of person objects from grouping
            session_uuid: Session identifier for database queries
            database: Vision Service database connection
            
        Returns:
            Dict mapping person_id to best face analysis results
        """
        best_faces_per_person = {}
        
        for person in person_objects:
            person_id = person['person_id']
            face_ids = person['original_face_ids']
            
            best_quality_score = 0.0
            best_face_info = None
            
            # Analyze each face for this person using stored data
            for face_id in face_ids:
                # Get face detection record with stored face crop data
                face_record = await self._get_face_detection_with_crop_data(face_id, database)
                if not face_record:
                    continue
                
                # Use pre-computed face crop or calculate from stored bbox
                face_crop = await self._get_or_calculate_face_crop(face_record, database)
                if face_crop is None:
                    continue
                
                # Calculate quality score (using same algorithm as grouping engine)
                from .face_grouping_engine import VisionFaceGroupingEngine
                grouping_engine = VisionFaceGroupingEngine()
                quality_score = grouping_engine.calculate_quality_score(face_crop)
                
                # Check if this is the best quality face
                if quality_score > best_quality_score:
                    best_quality_score = quality_score
                    best_face_info = {
                        'face_id': face_id,
                        'frame_number': face_record['frame_number'],
                        'quality_score': quality_score,
                        'bbox': [
                            face_record['bbox_x1'],
                            face_record['bbox_y1'], 
                            face_record['bbox_x2'],
                            face_record['bbox_y2']
                        ],
                        'face_crop': face_crop
                    }
            
            # Perform age detection on best face
            if best_face_info and self.deepface_available:
                try:
                    # Convert to RGB for DeepFace
                    face_rgb = cv2.cvtColor(best_face_info['face_crop'], cv2.COLOR_BGR2RGB)
                    
                    # Analyze age
                    analysis = self.deepface.analyze(
                        face_rgb, actions=['age'], enforce_detection=False
                    )
                    
                    if isinstance(analysis, list):
                        analysis = analysis[0]
                        
                    estimated_age = analysis['age']
                    best_face_info['estimated_age'] = estimated_age
                    
                except Exception as e:
                    best_face_info['estimated_age'] = "Unknown"
            else:
                if best_face_info:
                    best_face_info['estimated_age'] = "Unknown"
            
            # Calculate distance from camera (same as PPL Meta Mini)
            if best_face_info:
                bbox = best_face_info['bbox']
                face_width = bbox[2] - bbox[0]
                face_height = bbox[3] - bbox[1]
                face_area = face_width * face_height
                distance = 1000000 / max(face_area, 1)  # Inverse area relationship
                best_face_info['distance_from_camera'] = round(distance, 2)
                
                # Remove face crop from result (memory management)
                best_face_info.pop('face_crop', None)
                
                best_faces_per_person[person_id] = best_face_info
        
        # Sort by distance (closest first)
        sorted_faces = dict(
            sorted(
                best_faces_per_person.items(),
                key=lambda x: x[1].get('distance_from_camera', float('inf'))
            )
        )
        
        return sorted_faces
    
    async def _get_face_detection_record(self, face_id: str) -> Optional[Dict]:
        """Retrieve face detection record from database."""
        # Implementation to fetch from face_detections table
        pass
    
    async def _extract_frame_image(
        self, 
        face_record: Dict, 
        session_uuid: str, 
        media_service_client
    ) -> Optional[np.ndarray]:
        """Extract frame image from video via media service."""
        # Implementation to fetch frame from media service
        pass
    
    def _extract_face_crop(
        self, 
        frame_image: np.ndarray, 
        face_record: Dict
    ) -> Optional[np.ndarray]:
        """Extract face region from frame image."""
        try:
            x1, y1 = face_record['bbox_x1'], face_record['bbox_y1']
            x2, y2 = face_record['bbox_x2'], face_record['bbox_y2']
            
            face_crop = frame_image[y1:y2, x1:x2]
            return face_crop if face_crop.size > 0 else None
            
        except Exception:
            return None
```

---

## Phase 3: Workflow Integration

### 3.1 PPL Thread Workflow Controller

```python
# ppl-meta-vision/src/person_objects/ppl_thread_workflow.py

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..database import VisionDatabase
from .face_grouping_engine import VisionFaceGroupingEngine
from .quality_analyzer import PersonQualityAnalyzer

class PPLThreadWorkflowController:
    """
    Main workflow controller for PPL Thread (Person Objects) processing.
    
    This workflow operates as a second-level processing stage that takes
    existing face detection data and applies advanced grouping to create
    person objects with the same structure as PPL Meta Mini output.
    """
    
    def __init__(self, database: VisionDatabase):
        self.db = database
        self.face_grouping_engine = VisionFaceGroupingEngine()
        self.quality_analyzer = PersonQualityAnalyzer()
    
    async def start_person_objects_workflow(
        self,
        session_uuid: str,
        tolerance_percent: float = 20.0,
        enable_quality_analysis: bool = True,
        enable_age_detection: bool = True,
        workflow_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Start PPL Thread workflow for creating person objects from face detections.
        
        Args:
            session_uuid: Face detection session to process
            tolerance_percent: Position matching tolerance (default 20%)
            enable_quality_analysis: Enable best face quality analysis
            enable_age_detection: Enable age estimation
            workflow_metadata: Additional workflow metadata
            
        Returns:
            Workflow execution results with person objects data
        """
        workflow_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Create workflow record
            await self._create_workflow_record(
                workflow_id, session_uuid, tolerance_percent, workflow_metadata
            )
            
            # Fetch face detection data for session
            face_detections = await self._get_session_face_detections(session_uuid)
            
            if not face_detections:
                raise ValueError(f"No face detections found for session {session_uuid}")
            
            # Apply face grouping algorithm
            grouping_results = await self.face_grouping_engine.apply_percentage_based_tracking(
                face_detections, tolerance_percent
            )
            
            # Store person objects in database
            await self._store_person_objects(
                workflow_id, session_uuid, grouping_results
            )
            
            # Perform quality analysis if enabled
            best_quality_faces = {}
            if enable_quality_analysis:
                # Use internal Vision Service functionality - no external client needed
                best_quality_faces = await self.quality_analyzer.find_best_quality_faces_per_person(
                    grouping_results['person_objects'],
                    session_uuid,
                    self.db  # Pass database for internal access
                )
                
                # Update person objects with quality analysis
                await self._update_person_objects_with_quality(
                    workflow_id, best_quality_faces
                )
            
            # Update workflow status to completed
            await self._complete_workflow(
                workflow_id, 
                len(grouping_results['person_objects']),
                len(face_detections)
            )
            
            # Format response to match PPL Meta Mini structure
            response = self._format_ppl_mini_compatible_response(
                grouping_results, best_quality_faces, workflow_id, session_uuid
            )
            
            return response
            
        except Exception as e:
            # Update workflow status to failed
            await self._fail_workflow(workflow_id, str(e))
            raise
    
    async def get_person_objects_for_session(
        self, 
        session_uuid: str
    ) -> Dict[str, Any]:
        """
        Retrieve existing person objects for a session.
        
        Returns results in PPL Meta Mini compatible format.
        """
        # Fetch person objects from database
        person_objects = await self._get_stored_person_objects(session_uuid)
        
        if not person_objects:
            return {
                'success': False,
                'message': 'No person objects found for session',
                'person_objects': [],
                'statistics': {}
            }
        
        # Format response
        return self._format_stored_person_objects_response(person_objects, session_uuid)
    
    def _format_ppl_mini_compatible_response(
        self,
        grouping_results: Dict,
        best_quality_faces: Dict,
        workflow_id: str,
        session_uuid: str
    ) -> Dict[str, Any]:
        """
        Format response to exactly match PPL Meta Mini FaceGroupingEngine output structure.
        """
        person_objects = grouping_results['person_objects']
        statistics = grouping_results['statistics']
        
        # Create group tracking list (matching PPL Mini format)
        group_tracking_list = []
        for person in person_objects:
            person_id = person['person_id']
            
            group_tracking_list.append({
                'Merged_Group_ID': person_id,
                'Original_Group_IDs': person['original_face_ids'],
                'Face_Count': person['face_count'],
                'Average_Position': person['average_position'],
                'Y_Coordinate_Based': False,
                'Tracking_Based': True,
                'Tolerance_Percent': person['tolerance_percent'],
                'Merge_History': []
            })
        
        # Create best quality faces dict (matching PPL Mini format)  
        best_quality_formatted = {}
        for person_id, quality_data in best_quality_faces.items():
            best_quality_formatted[person_id] = {
                'face_id': quality_data['face_id'],
                'frame_number': quality_data['frame_number'],
                'quality_score': quality_data['quality_score'],
                'bbox': quality_data['bbox'],
                'age_detection': {
                    'estimated_age': quality_data.get('estimated_age', 'Unknown')
                },
                'distance': quality_data.get('distance_from_camera', 0.0)
            }
        
        # Create summary statistics (matching PPL Mini format)
        summary = {
            'total_groups': statistics['total_persons'],
            'original_unique_faces': statistics['total_faces'],
            'merged_groups_count': statistics['total_persons'],
            'total_detections': statistics['total_faces'],
            'frames_processed': statistics['frames_processed'],
            'grouping_algorithm': 'percentage_based_tracking',
            'tolerance_percent': statistics['tolerance_percent'],
            'tracked_faces': statistics['tracked_faces'],
            'new_faces': statistics['new_faces'],
            'merge_iterations': 0
        }
        
        return {
            'workflow_id': workflow_id,
            'session_uuid': session_uuid,
            'success': True,
            'original_groups': statistics['total_faces'],
            'merged_groups': statistics['total_persons'],
            'group_tracking': group_tracking_list,
            'summary': summary,
            'statistics': summary,
            'best_quality_faces': best_quality_formatted,
            'classified_faces': grouping_results['face_mappings'],
            'processing_timestamp': datetime.now().isoformat(),
            'workflow_type': 'ppl_thread_person_objects'
        }
    
    # Database operations
    async def _create_workflow_record(
        self, 
        workflow_id: str, 
        session_uuid: str, 
        tolerance_percent: float,
        metadata: Optional[Dict]
    ):
        """Create initial workflow record."""
        pass
    
    async def _get_session_face_detections(self, session_uuid: str) -> List[Dict]:
        """Fetch face detections for session from database.""" 
        pass
    
    async def _store_person_objects(
        self, 
        workflow_id: str, 
        session_uuid: str, 
        grouping_results: Dict
    ):
        """Store person objects and mappings in database."""
        pass
    
    async def _update_person_objects_with_quality(
        self, 
        workflow_id: str, 
        best_quality_faces: Dict
    ):
        """Update person objects with quality analysis results."""
        pass
    
    async def _complete_workflow(
        self, 
        workflow_id: str, 
        person_count: int, 
        face_count: int
    ):
        """Mark workflow as completed."""
        pass
    
    async def _fail_workflow(self, workflow_id: str, error_message: str):
        """Mark workflow as failed."""
        pass
```

### 3.2 API Integration

```python
# ppl-meta-vision/src/api/person_objects_api.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from ..person_objects.ppl_thread_workflow import PPLThreadWorkflowController
from ..database import vision_db

router = APIRouter(prefix="/api/v1/person-objects", tags=["person-objects"])

class PersonObjectsWorkflowRequest(BaseModel):
    """Request model for starting person objects workflow."""
    
    session_uuid: str = Field(..., description="Face detection session UUID")
    tolerance_percent: float = Field(default=20.0, description="Position matching tolerance")
    enable_quality_analysis: bool = Field(default=True, description="Enable quality analysis")
    enable_age_detection: bool = Field(default=True, description="Enable age detection")
    workflow_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class PersonObjectsWorkflowResponse(BaseModel):
    """Response model for person objects workflow."""
    
    workflow_id: str
    session_uuid: str
    success: bool
    original_groups: int
    merged_groups: int
    group_tracking: List[Dict[str, Any]]
    summary: Dict[str, Any]
    statistics: Dict[str, Any]
    best_quality_faces: Dict[str, Any]
    classified_faces: List[Dict[str, Any]]
    processing_timestamp: str
    workflow_type: str

@router.post("/workflows/start", response_model=PersonObjectsWorkflowResponse)
async def start_person_objects_workflow(
    request: PersonObjectsWorkflowRequest
):
    """
    Start PPL Thread workflow to create person objects from existing face detections.
    
    This endpoint applies the same face grouping algorithm as PPL Meta Mini's
    FaceGroupingEngine to create person objects with identical data structure.
    """
    try:
        controller = PPLThreadWorkflowController(vision_db)
        
        result = await controller.start_person_objects_workflow(
            session_uuid=request.session_uuid,
            tolerance_percent=request.tolerance_percent,
            enable_quality_analysis=request.enable_quality_analysis,
            enable_age_detection=request.enable_age_detection,
            workflow_metadata=request.workflow_metadata
        )
        
        return PersonObjectsWorkflowResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

@router.get("/sessions/{session_uuid}", response_model=PersonObjectsWorkflowResponse)
async def get_person_objects_for_session(
    session_uuid: str,
    include_quality_analysis: bool = Query(default=True, description="Include quality analysis data")
):
    """
    Retrieve existing person objects for a face detection session.
    
    Returns data in PPL Meta Mini compatible format.
    """
    try:
        controller = PPLThreadWorkflowController(vision_db)
        
        result = await controller.get_person_objects_for_session(session_uuid)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result['message'])
            
        return PersonObjectsWorkflowResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve person objects: {str(e)}")

@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get status of a person objects workflow."""
    try:
        controller = PPLThreadWorkflowController(vision_db)
        status = await controller.get_workflow_status(workflow_id)
        
        return {
            'workflow_id': workflow_id,
            'status': status['status'],
            'created_at': status['started_at'],
            'completed_at': status.get('completed_at'),
            'person_count': status.get('output_person_count', 0),
            'face_count': status.get('input_face_count', 0),
            'error_message': status.get('error_message')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

@router.get("/sessions/{session_uuid}/statistics")
async def get_session_person_statistics(session_uuid: str):
    """Get person objects statistics for a session."""
    try:
        controller = PPLThreadWorkflowController(vision_db)
        stats = await controller.get_session_statistics(session_uuid)
        
        return {
            'session_uuid': session_uuid,
            'total_face_detections': stats['total_faces'],
            'total_person_objects': stats['total_persons'],
            'grouping_efficiency': stats['grouping_efficiency'],
            'average_faces_per_person': stats['avg_faces_per_person'],
            'quality_analysis_completed': stats['has_quality_analysis'],
            'age_detection_completed': stats['has_age_detection']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
```

---

## Phase 4: Service Integration and Testing

### 4.1 Main Service Integration

Update the main Vision Service to include the new person objects functionality:

```python
# ppl-meta-vision/src/main.py (additions)

# Import person objects router
from api.person_objects_api import router as person_objects_router

# Add person objects router to main app
app.include_router(person_objects_router)

@app.on_event("startup")
async def startup_event():
    """Enhanced startup with person objects functionality."""
    global face_detector_instance, media_processor_instance

    try:
        # Existing initialization...
        
        # Initialize person objects database schema
        from database.person_objects_migrations import PersonObjectsMigration
        
        migration = PersonObjectsMigration(vision_db.connection)
        await migration.migrate_schema()
        
        logger.info("✅ Person Objects (PPL Thread) functionality initialized")
        
    except Exception as e:
        logger.error(f"❌ Person Objects initialization failed: {e}")
```

### 4.2 Enhanced Database Schema for Quality Analysis

Instead of external frame extraction, enhance the database to support quality analysis internally:

```python
# ppl-meta-vision/src/database/face_data_manager.py

class FaceDataManager:
    """Enhanced face data management for quality analysis."""
    
    def __init__(self, database: VisionDatabase):
        self.db = database
    
    async def store_face_detection_with_crop(
        self,
        face_detection_data: Dict,
        face_crop_base64: Optional[str] = None
    ):
        """
        Store face detection with optional pre-computed face crop.
        
        This allows quality analysis without re-extracting frames.
        """
        # Store main face detection record
        await self._store_face_detection(face_detection_data)
        
        # Optionally store face crop for later quality analysis
        if face_crop_base64:
            await self._store_face_crop(
                face_detection_data['id'],
                face_crop_base64
            )
    
    async def get_face_detection_with_quality_data(
        self, 
        face_id: str
    ) -> Optional[Dict]:
        """
        Retrieve face detection with all data needed for quality analysis.
        
        Returns bbox coordinates and pre-stored crop if available.
        """
        try:
            query = """
            SELECT fd.*, fc.crop_base64, fc.pre_computed_quality_score
            FROM face_detections fd
            LEFT JOIN face_crops fc ON fd.id = fc.face_detection_id
            WHERE fd.id = %s
            """
            
            cursor = self.db.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, (face_id,))
            result = cursor.fetchone()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to get face detection with quality data: {e}")
            return None
    
    async def calculate_and_store_quality_score(
        self,
        face_id: str,
        original_frame: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate quality score using stored bbox data or provided frame.
        
        This internal method eliminates need for external frame extraction.
        """
        # Implementation for internal quality calculation
        pass

# Additional database table for storing face crops
CREATE TABLE IF NOT EXISTS face_crops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    face_detection_id TEXT NOT NULL UNIQUE,
    crop_base64 TEXT,  -- Base64 encoded face crop image
    pre_computed_quality_score REAL,
    crop_width INTEGER,
    crop_height INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (face_detection_id) REFERENCES face_detections(id)
);
```

### 4.3 Integration Testing Suite

```python
# ppl-meta-vision/src/tests/test_person_objects_workflow.py

import pytest
import asyncio
from datetime import datetime
from ..person_objects.ppl_thread_workflow import PPLThreadWorkflowController
from ..person_objects.face_grouping_engine import VisionFaceGroupingEngine

class TestPersonObjectsWorkflow:
    """Comprehensive test suite for PPL Thread workflow."""
    
    @pytest.fixture
    async def sample_face_detections(self):
        """Create sample face detection data for testing."""
        return [
            {
                'id': 'face_1',
                'frame_number': 1,
                'bbox_x1': 100, 'bbox_y1': 100,
                'bbox_x2': 200, 'bbox_y2': 200,
                'confidence': 0.85,
                'method': 'two_stage'
            },
            {
                'id': 'face_2', 
                'frame_number': 2,
                'bbox_x1': 105, 'bbox_y1': 105,
                'bbox_x2': 205, 'bbox_y2': 205,
                'confidence': 0.90,
                'method': 'two_stage'
            }
            # Add more test data...
        ]
    
    async def test_face_grouping_algorithm(self, sample_face_detections):
        """Test that face grouping produces consistent results."""
        engine = VisionFaceGroupingEngine()
        
        results = await engine.apply_percentage_based_tracking(
            sample_face_detections, tolerance_percent=20.0
        )
        
        assert 'person_objects' in results
        assert 'face_mappings' in results
        assert 'statistics' in results
        assert results['statistics']['algorithm'] == 'percentage_based_tracking'
    
    async def test_ppl_mini_compatibility(self, sample_face_detections):
        """Test that output format matches PPL Meta Mini exactly."""
        controller = PPLThreadWorkflowController(None)  # Mock database
        
        # Test response format compatibility
        grouping_results = {
            'person_objects': [
                {
                    'person_id': 'person_1',
                    'face_count': 2,
                    'average_position': {'x': 102.5, 'y': 102.5},
                    'tolerance_percent': 20.0,
                    'original_face_ids': ['face_1', 'face_2']
                }
            ],
            'face_mappings': [],
            'statistics': {
                'total_faces': 2,
                'total_persons': 1,
                'tracked_faces': 1,
                'new_faces': 1,
                'frames_processed': 2,
                'tolerance_percent': 20.0
            }
        }
        
        response = controller._format_ppl_mini_compatible_response(
            grouping_results, {}, 'test_workflow', 'test_session'
        )
        
        # Verify PPL Mini compatibility
        assert 'group_tracking' in response
        assert 'summary' in response
        assert 'statistics' in response
        assert 'best_quality_faces' in response
        assert response['workflow_type'] == 'ppl_thread_person_objects'
        
        # Verify group tracking format
        group_tracking = response['group_tracking'][0]
        assert 'Merged_Group_ID' in group_tracking
        assert 'Original_Group_IDs' in group_tracking
        assert 'Face_Count' in group_tracking
        assert 'Average_Position' in group_tracking
        assert group_tracking['Tracking_Based'] == True
        assert group_tracking['Y_Coordinate_Based'] == False
    
    async def test_tolerance_matching(self):
        """Test percentage-based tolerance matching algorithm."""
        engine = VisionFaceGroupingEngine()
        
        pos1 = {'x': 100, 'y': 100}
        pos2 = {'x': 115, 'y': 110}  # Within 20% tolerance
        pos3 = {'x': 150, 'y': 150}  # Outside 20% tolerance
        
        # Test within tolerance
        distance1 = engine.calculate_position_distance(pos1, pos2)
        assert distance1['within_tolerance'] == True
        
        # Test outside tolerance  
        distance2 = engine.calculate_position_distance(pos1, pos3)
        assert distance2['within_tolerance'] == False
        
        # Verify tolerance calculations
        assert distance1['x_tolerance_used'] == 20.0  # 20% of 100
        assert distance1['y_tolerance_used'] == 20.0  # 20% of 100
```

---

## Phase 5: Documentation and Deployment

### 5.1 API Documentation

Create comprehensive API documentation that clearly shows the PPL Meta Mini compatibility:

```markdown
# PPL Thread Workflow API Documentation

## Overview

The PPL Thread Workflow extends the PPL Meta Vision Service with advanced face grouping capabilities, creating "person objects" from existing face detection data. The workflow applies the exact same percentage-based tolerance matching algorithm as PPL Meta Mini's FaceGroupingEngine while maintaining complete independence.

## Key Features

- **PPL Meta Mini Compatibility**: Identical output format and data structure
- **Percentage-Based Tracking**: 20% tolerance algorithm for robust face matching
- **Quality Analysis**: Best face selection with quality scoring and age detection
- **Independent Implementation**: Zero dependencies on PPL Meta Mini codebase
- **Session-Based Processing**: Operates on existing face detection sessions

## API Endpoints

### Start Person Objects Workflow

**POST** `/api/v1/person-objects/workflows/start`

Create person objects from existing face detections in a session.

**Request Body:**
```json
{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
  "tolerance_percent": 20.0,
  "enable_quality_analysis": true,
  "enable_age_detection": true,
  "workflow_metadata": {
    "description": "Person objects for security footage analysis"
  }
}
```

**Response:**
```json
{
  "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
  "session_uuid": "550e8400-e29b-41d4-a716-446655440002", 
  "success": true,
  "original_groups": 15,
  "merged_groups": 8,
  "group_tracking": [
    {
      "Merged_Group_ID": "person_1",
      "Original_Group_IDs": ["face_1", "face_3", "face_7"],
      "Face_Count": 3,
      "Average_Position": {"x": 245.5, "y": 180.2},
      "Y_Coordinate_Based": false,
      "Tracking_Based": true,
      "Tolerance_Percent": 20.0,
      "Merge_History": []
    }
  ],
  "summary": {
    "total_groups": 8,
    "original_unique_faces": 15,
    "merged_groups_count": 8,
    "total_detections": 15,
    "frames_processed": 120,
    "grouping_algorithm": "percentage_based_tracking",
    "tolerance_percent": 20.0,
    "tracked_faces": 12,
    "new_faces": 3
  },
  "best_quality_faces": {
    "person_1": {
      "face_id": "face_7",
      "frame_number": 45,
      "quality_score": 0.92,
      "bbox": [200, 150, 290, 240],
      "age_detection": {"estimated_age": 28},
      "distance": 156.2
    }
  },
  "classified_faces": [
    {
      "person_id": "person_1",
      "face_detection_id": "face_1", 
      "match_type": "new_track",
      "match_distance": 0.0,
      "frame_number": 15,
      "position_x": 240.0,
      "position_y": 175.0
    }
  ],
  "processing_timestamp": "2024-09-24T10:30:45.123456",
  "workflow_type": "ppl_thread_person_objects"
}
```
```

### 5.2 Deployment Configuration

```yaml
# deployment/person-objects-config.yaml

person_objects:
  enabled: true
  default_tolerance_percent: 20.0
  quality_analysis:
    enabled: true
    deepface_enabled: true
  age_detection:
    enabled: true
    fallback_unknown: true
  performance:
    max_concurrent_workflows: 5
    frame_extraction_timeout: 30
    database_batch_size: 100
  database:
    schema_auto_migrate: true
    cleanup_old_workflows: true
    retention_days: 30
```

---

## Acceptance Criteria

### Technical Requirements

1. **Algorithm Accuracy**
   - [ ] Face grouping results match PPL Meta Mini output within 95% accuracy
   - [ ] Percentage-based tolerance matching works identically (20% default)
   - [ ] Quality scoring produces consistent results across implementations

2. **Data Structure Compatibility**
   - [ ] Output JSON structure exactly matches PPL Meta Mini format
   - [ ] All field names and data types identical
   - [ ] Group tracking format preserved exactly

3. **Performance Standards**
   - [ ] Process 1000 faces in under 10 seconds
   - [ ] Quality analysis completes within 30 seconds per session
   - [ ] Database operations complete within acceptable latency

4. **Independence Requirements**
   - [ ] Zero code sharing with PPL Meta Mini
   - [ ] No imports or dependencies on mini application
   - [ ] Standalone operation within Vision Service

### Functional Requirements

1. **Workflow Execution**
   - [ ] Successfully process existing face detection sessions
   - [ ] Generate person objects with proper grouping
   - [ ] Complete quality analysis and age detection

2. **API Functionality** 
   - [ ] All endpoints respond correctly
   - [ ] Proper error handling and validation
   - [ ] Consistent response formats

3. **Database Integration**
   - [ ] Schema migrations work correctly  
   - [ ] Data storage and retrieval functions properly
   - [ ] Proper indexing for performance

### Integration Requirements

1. **Vision Service Integration**
   - [ ] Seamless integration with existing functionality
   - [ ] No disruption to current face detection workflows
   - [ ] Proper startup and initialization

2. **Media Service Compatibility**
   - [ ] Frame extraction works correctly
   - [ ] Proper session correlation
   - [ ] Efficient media data access

---

## Phase 6: Frontend Integration

### 6.1 Enhanced Media Preview Screen Integration

The PPL Thread workflow results will be seamlessly integrated into the existing `http://localhost:3000/#/media-preview` screen, providing users with person objects data alongside face detection results.

#### Media Preview Screen Enhancements

```dart
// ppl-meta-frontend/lib/screens/media_preview_screen.dart (enhancements)

class _EnhancedMediaPreviewScreenState extends ConsumerState<EnhancedMediaPreviewScreen> {
  // Add person objects state
  PersonObjectsData? _personObjectsData;
  bool _isLoadingPersonObjects = false;
  
  @override
  void initState() {
    super.initState();
    
    // Existing face data loading
    WidgetsBinding.instance.addPostFrameCallback((_) {
      EnhancedAutoFaceLoader.loadFacesForMedia(ref, widget.mediaItem.uuid);
      // Add automatic person objects loading
      _loadPersonObjectsIfAvailable();
    });
  }
  
  /// Load person objects if available for this media
  Future<void> _loadPersonObjectsIfAvailable() async {
    try {
      final personObjects = await PersonObjectsApiClient().getPersonObjectsForMedia(
        widget.mediaItem.uuid
      );
      
      if (mounted && personObjects != null) {
        setState(() {
          _personObjectsData = personObjects;
        });
      }
    } catch (e) {
      // Person objects not available yet - this is normal
      debugPrint('Person objects not available for media ${widget.mediaItem.uuid}');
    }
  }
}

/// Enhanced processing status display with person objects
Widget _buildCompactProcessingStatus(ProcessingStatus status, WidgetRef ref) {
  final isProcessed = status.faceDetectionProcessed;
  final faceCount = status.totalFacesDetected ?? 0;
  final hasActiveSession = status.currentSession != null;
  
  // Get person objects count
  final personCount = _personObjectsData?.totalPersons ?? 0;
  final hasPersonObjects = _personObjectsData != null;
  
  return Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(
        isProcessed ? Icons.check_circle : (hasActiveSession ? Icons.play_circle : Icons.face),
        color: isProcessed ? Colors.green : (hasActiveSession ? Colors.blue : Colors.grey),
        size: 14,
      ),
      const SizedBox(width: 4),
      Flexible(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Faces detected line
            Text(
              isProcessed 
                  ? '$faceCount faces detected'
                  : hasActiveSession 
                      ? 'Processing...'
                      : 'Ready',
              style: TextStyle(
                color: isProcessed ? Colors.green : (hasActiveSession ? Colors.blue : Colors.white70),
                fontSize: 12,
              ),
              overflow: TextOverflow.ellipsis,
            ),
            
            // Person objects line (new)
            if (hasPersonObjects) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  Icon(
                    Icons.person,
                    color: Colors.orange,
                    size: 12,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '$personCount persons identified',
                    style: const TextStyle(
                      color: Colors.orange,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ] else if (isProcessed) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  Icon(
                    Icons.hourglass_empty,
                    color: Colors.orange[300],
                    size: 12,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Analyzing persons...',
                    style: TextStyle(
                      color: Colors.orange[300],
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    ],
  );
}
```

### 6.2 Person Objects Data Models

```dart
// ppl-meta-frontend/lib/models/person_objects_models.dart

/// Person objects data model matching PPL Meta Mini output structure
class PersonObjectsData {
  final String workflowId;
  final String sessionUuid;
  final bool success;
  final int originalGroups;
  final int mergedGroups;
  final int totalPersons;
  final List<PersonGroup> groupTracking;
  final PersonObjectsStatistics statistics;
  final Map<String, BestQualityFace> bestQualityFaces;
  final List<ClassifiedFace> classifiedFaces;
  final String processingTimestamp;
  final String workflowType;

  const PersonObjectsData({
    required this.workflowId,
    required this.sessionUuid,
    required this.success,
    required this.originalGroups,
    required this.mergedGroups,
    required this.totalPersons,
    required this.groupTracking,
    required this.statistics,
    required this.bestQualityFaces,
    required this.classifiedFaces,
    required this.processingTimestamp,
    required this.workflowType,
  });

  factory PersonObjectsData.fromJson(Map<String, dynamic> json) {
    return PersonObjectsData(
      workflowId: json['workflow_id'] ?? '',
      sessionUuid: json['session_uuid'] ?? '',
      success: json['success'] ?? false,
      originalGroups: json['original_groups'] ?? 0,
      mergedGroups: json['merged_groups'] ?? 0,
      totalPersons: json['merged_groups'] ?? 0,  // Same as merged_groups
      groupTracking: (json['group_tracking'] as List? ?? [])
          .map((item) => PersonGroup.fromJson(item))
          .toList(),
      statistics: PersonObjectsStatistics.fromJson(json['statistics'] ?? {}),
      bestQualityFaces: (json['best_quality_faces'] as Map<String, dynamic>? ?? {})
          .map((key, value) => MapEntry(key, BestQualityFace.fromJson(value))),
      classifiedFaces: (json['classified_faces'] as List? ?? [])
          .map((item) => ClassifiedFace.fromJson(item))
          .toList(),
      processingTimestamp: json['processing_timestamp'] ?? '',
      workflowType: json['workflow_type'] ?? '',
    );
  }
}

/// Person group tracking data (matches PPL Mini format exactly)
class PersonGroup {
  final String mergedGroupId;
  final List<String> originalGroupIds;
  final int faceCount;
  final PersonPosition averagePosition;
  final bool yCoordinateBased;
  final bool trackingBased;
  final double tolerancePercent;
  final List<dynamic> mergeHistory;

  const PersonGroup({
    required this.mergedGroupId,
    required this.originalGroupIds,
    required this.faceCount,
    required this.averagePosition,
    required this.yCoordinateBased,
    required this.trackingBased,
    required this.tolerancePercent,
    required this.mergeHistory,
  });

  factory PersonGroup.fromJson(Map<String, dynamic> json) {
    return PersonGroup(
      mergedGroupId: json['Merged_Group_ID'] ?? '',
      originalGroupIds: List<String>.from(json['Original_Group_IDs'] ?? []),
      faceCount: json['Face_Count'] ?? 0,
      averagePosition: PersonPosition.fromJson(json['Average_Position'] ?? {}),
      yCoordinateBased: json['Y_Coordinate_Based'] ?? false,
      trackingBased: json['Tracking_Based'] ?? false,
      tolerancePercent: (json['Tolerance_Percent'] ?? 0).toDouble(),
      mergeHistory: json['Merge_History'] ?? [],
    );
  }
}

/// Person position coordinates
class PersonPosition {
  final double x;
  final double y;

  const PersonPosition({required this.x, required this.y});

  factory PersonPosition.fromJson(Map<String, dynamic> json) {
    return PersonPosition(
      x: (json['x'] ?? 0).toDouble(),
      y: (json['y'] ?? 0).toDouble(),
    );
  }
}

/// Best quality face for a person
class BestQualityFace {
  final String faceId;
  final int frameNumber;
  final double qualityScore;
  final List<int> bbox;
  final AgeDetection ageDetection;
  final double distance;

  const BestQualityFace({
    required this.faceId,
    required this.frameNumber,
    required this.qualityScore,
    required this.bbox,
    required this.ageDetection,
    required this.distance,
  });

  factory BestQualityFace.fromJson(Map<String, dynamic> json) {
    return BestQualityFace(
      faceId: json['face_id'] ?? '',
      frameNumber: json['frame_number'] ?? 0,
      qualityScore: (json['quality_score'] ?? 0).toDouble(),
      bbox: List<int>.from(json['bbox'] ?? []),
      ageDetection: AgeDetection.fromJson(json['age_detection'] ?? {}),
      distance: (json['distance'] ?? 0).toDouble(),
    );
  }
}

/// Age detection result
class AgeDetection {
  final dynamic estimatedAge;  // Can be int or "Unknown"

  const AgeDetection({required this.estimatedAge});

  factory AgeDetection.fromJson(Map<String, dynamic> json) {
    return AgeDetection(
      estimatedAge: json['estimated_age'] ?? 'Unknown',
    );
  }
  
  String get displayAge {
    if (estimatedAge is int) {
      return '$estimatedAge years';
    }
    return estimatedAge.toString();
  }
}

/// Person objects processing statistics
class PersonObjectsStatistics {
  final int totalGroups;
  final int originalUniqueFaces;
  final int mergedGroupsCount;
  final int totalDetections;
  final int framesProcessed;
  final String groupingAlgorithm;
  final double tolerancePercent;
  final int trackedFaces;
  final int newFaces;
  final int mergeIterations;

  const PersonObjectsStatistics({
    required this.totalGroups,
    required this.originalUniqueFaces,
    required this.mergedGroupsCount,
    required this.totalDetections,
    required this.framesProcessed,
    required this.groupingAlgorithm,
    required this.tolerancePercent,
    required this.trackedFaces,
    required this.newFaces,
    required this.mergeIterations,
  });

  factory PersonObjectsStatistics.fromJson(Map<String, dynamic> json) {
    return PersonObjectsStatistics(
      totalGroups: json['total_groups'] ?? 0,
      originalUniqueFaces: json['original_unique_faces'] ?? 0,
      mergedGroupsCount: json['merged_groups_count'] ?? 0,
      totalDetections: json['total_detections'] ?? 0,
      framesProcessed: json['frames_processed'] ?? 0,
      groupingAlgorithm: json['grouping_algorithm'] ?? '',
      tolerancePercent: (json['tolerance_percent'] ?? 0).toDouble(),
      trackedFaces: json['tracked_faces'] ?? 0,
      newFaces: json['new_faces'] ?? 0,
      mergeIterations: json['merge_iterations'] ?? 0,
    );
  }
}

/// Classified face mapping
class ClassifiedFace {
  final String personId;
  final String faceDetectionId;
  final String matchType;
  final double matchDistance;
  final int frameNumber;
  final double positionX;
  final double positionY;

  const ClassifiedFace({
    required this.personId,
    required this.faceDetectionId,
    required this.matchType,
    required this.matchDistance,
    required this.frameNumber,
    required this.positionX,
    required this.positionY,
  });

  factory ClassifiedFace.fromJson(Map<String, dynamic> json) {
    return ClassifiedFace(
      personId: json['person_id'] ?? '',
      faceDetectionId: json['face_detection_id'] ?? '',
      matchType: json['match_type'] ?? '',
      matchDistance: (json['match_distance'] ?? 0).toDouble(),
      frameNumber: json['frame_number'] ?? 0,
      positionX: (json['position_x'] ?? 0).toDouble(),
      positionY: (json['position_y'] ?? 0).toDouble(),
    );
  }
}
```

### 6.3 Person Objects API Client

```dart
// ppl-meta-frontend/lib/services/person_objects_api_client.dart

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/person_objects_models.dart';
import '../core/api/api_client.dart';

class PersonObjectsApiClient {
  final ApiClient _apiClient = ApiClient();
  
  /// Get person objects for a media item (by session UUID lookup)
  Future<PersonObjectsData?> getPersonObjectsForMedia(String mediaUuid) async {
    try {
      // First, find the session UUID for this media
      final sessionUuid = await _getSessionUuidForMedia(mediaUuid);
      if (sessionUuid == null) return null;
      
      // Get person objects for the session
      return await getPersonObjectsForSession(sessionUuid);
      
    } catch (e) {
      debugPrint('Failed to get person objects for media $mediaUuid: $e');
      return null;
    }
  }
  
  /// Get person objects for a specific session
  Future<PersonObjectsData?> getPersonObjectsForSession(String sessionUuid) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/person-objects/sessions/$sessionUuid',
      );
      
      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return PersonObjectsData.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        // Person objects not created yet
        return null;
      } else {
        throw Exception('Failed to get person objects: ${response.statusCode}');
      }
      
    } catch (e) {
      debugPrint('Failed to get person objects for session $sessionUuid: $e');
      return null;
    }
  }
  
  /// Start person objects workflow for a session
  Future<PersonObjectsData?> startPersonObjectsWorkflow(
    String sessionUuid, {
    double tolerancePercent = 20.0,
    bool enableQualityAnalysis = true,
    bool enableAgeDetection = true,
    Map<String, dynamic>? workflowMetadata,
  }) async {
    try {
      final requestBody = {
        'session_uuid': sessionUuid,
        'tolerance_percent': tolerancePercent,
        'enable_quality_analysis': enableQualityAnalysis,
        'enable_age_detection': enableAgeDetection,
        if (workflowMetadata != null) 'workflow_metadata': workflowMetadata,
      };
      
      final response = await _apiClient.post(
        '/api/v1/person-objects/workflows/start',
        body: json.encode(requestBody),
      );
      
      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return PersonObjectsData.fromJson(jsonData);
      } else {
        throw Exception('Failed to start person objects workflow: ${response.statusCode}');
      }
      
    } catch (e) {
      debugPrint('Failed to start person objects workflow: $e');
      rethrow;
    }
  }
  
  /// Get session UUID for a media item (internal helper)
  Future<String?> _getSessionUuidForMedia(String mediaUuid) async {
    try {
      // Query Vision Service for sessions associated with this media
      final response = await _apiClient.get(
        '/api/v1/sessions?media_uuid=$mediaUuid',
      );
      
      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        final sessions = jsonData['sessions'] as List?;
        
        if (sessions != null && sessions.isNotEmpty) {
          // Return the most recent session UUID
          return sessions.first['session_uuid'] as String?;
        }
      }
      
      return null;
      
    } catch (e) {
      debugPrint('Failed to get session UUID for media $mediaUuid: $e');
      return null;
    }
  }
}
```

### 6.4 Automatic Workflow Execution Integration

Update the existing workflow system to automatically trigger person objects creation:

```dart
// ppl-meta-frontend/lib/providers/workflow_providers.dart (enhancements)

class MediaWorkflowNotifier extends StateNotifier<WorkflowState> {
  // Existing implementation...
  
  /// Enhanced workflow completion handler with automatic person objects trigger
  Future<void> _handleWorkflowCompletion(String workflowId) async {
    try {
      final currentState = state;
      if (!currentState.isCompleted) return;
      
      // Existing completion logic...
      
      // NEW: Automatically trigger person objects workflow after face detection completes
      if (currentState.processingStatus?.faceDetectionProcessed == true) {
        await _triggerPersonObjectsWorkflow();
      }
      
    } catch (e) {
      debugPrint('Error in workflow completion handler: $e');
    }
  }
  
  /// Trigger person objects workflow automatically
  Future<void> _triggerPersonObjectsWorkflow() async {
    try {
      final sessionUuid = await _getCurrentSessionUuid();
      if (sessionUuid == null) return;
      
      debugPrint('🧠 Auto-triggering person objects workflow for session: $sessionUuid');
      
      // Start person objects workflow in background
      final personObjectsClient = PersonObjectsApiClient();
      await personObjectsClient.startPersonObjectsWorkflow(
        sessionUuid,
        workflowMetadata: {
          'triggered_by': 'automatic_post_face_detection',
          'media_uuid': mediaUuid,
          'timestamp': DateTime.now().toIso8601String(),
        },
      );
      
      // Update UI state to show person objects are being processed
      _updatePersonObjectsProcessingStatus(true);
      
      // Start monitoring person objects completion
      _monitorPersonObjectsCompletion(sessionUuid);
      
    } catch (e) {
      debugPrint('Failed to trigger automatic person objects workflow: $e');
    }
  }
  
  /// Monitor person objects workflow completion
  void _monitorPersonObjectsCompletion(String sessionUuid) {
    Timer.periodic(const Duration(seconds: 2), (timer) async {
      try {
        final personObjectsClient = PersonObjectsApiClient();
        final result = await personObjectsClient.getPersonObjectsForSession(sessionUuid);
        
        if (result != null) {
          // Person objects completed
          timer.cancel();
          _updatePersonObjectsProcessingStatus(false);
          _notifyPersonObjectsCompleted(result);
        }
        
        // Cancel after 5 minutes to prevent infinite polling
        if (timer.tick > 150) {
          timer.cancel();
          _updatePersonObjectsProcessingStatus(false);
        }
        
      } catch (e) {
        debugPrint('Error monitoring person objects completion: $e');
      }
    });
  }
  
  /// Update person objects processing status in UI
  void _updatePersonObjectsProcessingStatus(bool isProcessing) {
    // Update state to reflect person objects processing status
    // This will trigger UI updates in the media preview screen
    state = state.copyWith(
      customStatus: {
        ...state.customStatus,
        'person_objects_processing': isProcessing,
      },
    );
  }
  
  /// Notify UI that person objects are completed
  void _notifyPersonObjectsCompleted(PersonObjectsData result) {
    state = state.copyWith(
      customStatus: {
        ...state.customStatus,
        'person_objects_processing': false,
        'person_objects_completed': true,
        'person_objects_data': result,
      },
    );
  }
}
```

### 6.5 Enhanced UI Components

Create additional UI components to display person objects information:

```dart
// ppl-meta-frontend/lib/widgets/person_objects/person_objects_summary_widget.dart

class PersonObjectsSummaryWidget extends StatelessWidget {
  final PersonObjectsData personObjectsData;
  final bool showDetails;

  const PersonObjectsSummaryWidget({
    super.key,
    required this.personObjectsData,
    this.showDetails = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.orange[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Icon(Icons.person, color: Colors.orange[700], size: 20),
              const SizedBox(width: 8),
              Text(
                'Person Objects Analysis',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.orange[700],
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.orange[700],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${personObjectsData.totalPersons} persons',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          
          if (showDetails) ...[
            const SizedBox(height: 12),
            
            // Statistics
            _buildStatisticRow('Original faces', '${personObjectsData.originalGroups}'),
            _buildStatisticRow('Merged groups', '${personObjectsData.mergedGroups}'),
            _buildStatisticRow('Algorithm', personObjectsData.statistics.groupingAlgorithm),
            _buildStatisticRow('Tolerance', '${personObjectsData.statistics.tolerancePercent}%'),
            
            const SizedBox(height: 12),
            
            // Best quality faces preview
            if (personObjectsData.bestQualityFaces.isNotEmpty) ...[
              Text(
                'Identified Persons',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.orange[700],
                ),
              ),
              const SizedBox(height: 8),
              
              ...personObjectsData.bestQualityFaces.entries.take(3).map(
                (entry) => _buildPersonCard(entry.key, entry.value),
              ),
              
              if (personObjectsData.bestQualityFaces.length > 3) ...[
                Text(
                  '... and ${personObjectsData.bestQualityFaces.length - 3} more persons',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.orange[600],
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ],
          ],
        ],
      ),
    );
  }
  
  Widget _buildStatisticRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 12, color: Colors.black87),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPersonCard(String personId, BestQualityFace face) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.orange[200]!),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: Colors.orange[100],
            radius: 16,
            child: Text(
              personId.replaceAll('person_', 'P'),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.bold,
                color: Colors.orange[700],
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Person ${personId.replaceAll('person_', '')}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  'Age: ${face.ageDetection.displayAge} • Quality: ${(face.qualityScore * 100).toInt()}%',
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

### 6.6 Integration Summary

The frontend integration provides:

1. **Automatic Workflow Execution**: Person objects workflow triggers automatically after face detection completes
2. **Enhanced Status Display**: Media preview screen shows both face count and person count
3. **Real-time Updates**: UI updates automatically when person objects analysis completes
4. **Detailed Analytics**: Expandable person objects summary with quality analysis
5. **Seamless UX**: No user intervention required - everything happens automatically

**User Experience Flow:**
```text
1. User uploads video → Face detection starts automatically
2. Face detection completes → Shows "X faces detected"
3. Person objects workflow starts → Shows "Analyzing persons..."
4. Person objects complete → Shows "Y persons identified"
5. User can expand to see detailed person analytics
```

This creates a smooth, automated experience where users get both face detection and person identification results without any manual intervention.

---

## Risk Mitigation

### Technical Risks

1. **Algorithm Divergence**
   - **Risk**: Implementation differences causing result inconsistency
   - **Mitigation**: Comprehensive cross-validation testing against PPL Meta Mini
   - **Monitoring**: Automated accuracy comparison tests

2. **Performance Impact**
   - **Risk**: Person objects processing affecting existing Vision Service performance  
   - **Mitigation**: Async processing, resource limits, performance monitoring
   - **Monitoring**: Real-time performance metrics and alerting

3. **Database Schema Conflicts**
   - **Risk**: New tables conflicting with existing database structure
   - **Mitigation**: Careful schema design, migration testing, rollback procedures
   - **Monitoring**: Database performance and integrity checks

### Operational Risks

1. **Memory Usage**
   - **Risk**: Quality analysis consuming excessive memory for large sessions
   - **Mitigation**: Streaming processing, memory limits, garbage collection
   - **Monitoring**: Memory usage tracking and alerts

2. **Dependencies** 
   - **Risk**: DeepFace or other ML libraries causing stability issues
   - **Mitigation**: Optional features, fallback mechanisms, error handling
   - **Monitoring**: Dependency health checks and version monitoring

---

## Success Metrics

### Quantitative Metrics

- **Accuracy**: 95%+ match with PPL Meta Mini results
- **Performance**: <10s processing time for 1000 faces  
- **Availability**: 99.9% uptime for person objects functionality
- **Throughput**: Handle 100 concurrent sessions

### Qualitative Metrics

- **Code Quality**: Clean, maintainable, well-documented code
- **API Usability**: Intuitive, consistent API design
- **Integration**: Seamless operation within existing platform
- **Maintainability**: Easy to extend and modify functionality

---

## Timeline and Milestones

### Phase 1: Database Schema (1 week)
- Day 1-2: Schema design and review
- Day 3-4: Migration implementation  
- Day 5-7: Testing and validation

### Phase 2: Core Engine (2 weeks)
- Week 1: Face grouping algorithm implementation
- Week 2: Quality analyzer implementation and testing

### Phase 3: Workflow Integration (1 week) 
- Day 1-3: Workflow controller implementation
- Day 4-5: API integration
- Day 6-7: Integration testing

### Phase 4: Testing and Validation (1 week)
- Day 1-3: Comprehensive test suite
- Day 4-5: Cross-validation with PPL Meta Mini
- Day 6-7: Performance testing and optimization

### Phase 5: Documentation and Deployment (1 week)
- Day 1-2: Documentation completion
- Day 3-4: Deployment preparation
- Day 5-7: Final validation and release

### Phase 6: Frontend Integration (1 week)

- Day 1-2: Flutter model classes and API client implementation
- Day 3-4: UI component integration and status display updates
- Day 5-6: Automatic workflow execution implementation  
- Day 7: End-to-end testing and validation

#### Total Timeline: 7 weeks

---

## Conclusion

This implementation provides a complete, independent person objects workflow for the PPL Meta Vision Service that exactly replicates the functionality and output format of the PPL Meta Mini application's FaceGroupingEngine, while maintaining complete separation and autonomy between the systems.

### Key Benefits

1. **Seamless User Experience**: Automatic execution after face detection with real-time UI updates on `http://localhost:3000/#/media-preview`
2. **Architecture Consistency**: Maintains PPL Meta service autonomy and design patterns  
3. **Complete Feature Parity**: Identical functionality to PPL Meta Mini with enhanced platform integration
4. **Production Ready**: Comprehensive testing, error handling, and scalability considerations
5. **Developer Friendly**: Clear API interfaces, detailed documentation, and modular design

### Frontend Integration Highlights

- **Automatic Workflow Trigger**: Person objects analysis starts immediately after face detection completes
- **Enhanced Status Display**: Shows both "X faces detected" and "Y persons identified" on media preview
- **Real-time Updates**: UI automatically reflects workflow progress and completion
- **Detailed Analytics**: Expandable person objects summary with quality metrics and age detection
- **Zero User Intervention**: Complete automation provides seamless user experience

The implementation ensures that users will see comprehensive face and person analytics automatically appear without any manual steps, creating an intuitive and powerful media analysis experience.
