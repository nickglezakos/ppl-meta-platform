# Playground Issues - Person Trails Notebook

## Issue #001: Fully Functional Progressive Face Detection Notebook

### Overview
The `person_trails.ipynb` notebook needs to be transformed into a fully functional, decoupled testing environment that can authenticate and test progressive face detection capabilities independent of the main application UI.

### Requirements

#### 1. **Nginx Endpoint Usage**
- **Requirement**: All API calls must go through nginx proxy
- **Base URL**: `http://localhost/` (nginx routing)
- **Rationale**: Test the complete request flow as it would happen in production
- **Implementation**: Use nginx-routed endpoints instead of direct service calls

#### 2. **Database Access**
- **Requirement**: Direct database access for test data validation and setup
- **Target Databases**: 
  - Media service database for media item metadata
  - Any other databases needed for comprehensive testing
- **Purpose**: Validate data consistency and retrieve test data independently
- **Implementation**: PostgreSQL connections to service databases

#### 3. **Test User Authentication**
- **Test Credentials**:
  ```json
  {
    "email": "fresh.user@example.com",
    "password": "SecureTestPass123!"
  }
  ```
- **Requirement**: Authenticate through nginx-routed endpoints
- **Expected Outcome**: Valid JWT token for authenticated API calls
- **Implementation**: POST to `/api/v1/auth/login` via nginx

#### 4. **Authenticated Access to Test Video**
- **Target Media ID**: `170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e`
- **Requirement**: Obtain authenticated access to this specific video file
- **Process**: Use JWT token from authentication step
- **Validation**: Confirm access permissions and file availability
- **Implementation**: Verify media access through authenticated endpoints

#### 5. **Video Metadata Retrieval**
- **Target**: Same video (`170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e`)
- **Requirement**: Retrieve complete video metadata using authenticated endpoints
- **Expected Data**:
  - Video properties (duration, FPS, resolution)
  - File information (path, size, format)
  - Face detection capabilities status
- **Implementation**: Use authenticated media metadata endpoints

#### 6. **Clear Face Data Module**
- **Purpose**: Clean up test data after experiments
- **Scope**: Remove face detection data for the test video
- **Placement**: Independent function placed after all tests
- **Requirement**: Should NOT be part of test execution loops
- **Implementation**: Standalone cleanup function that can be called manually

#### 7. **Progressive Face Detection Test**
- **Scope**: Single comprehensive test of progressive face detection
- **Target**: Test video `170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e`
- **Requirements**:
  - Use authenticated access
  - Test through nginx endpoints
  - Validate progressive detection workflow
  - Display actual face detection results
- **Expected Outcome**: Real face detection data from the test video

### Technical Specifications

#### Authentication Flow
```
1. POST /api/v1/auth/login (via nginx)
   → Receive JWT token
2. Use token in Authorization header for all subsequent requests
3. Validate token works with protected endpoints
```

#### Progressive Face Detection Endpoint
```
POST /api/v1/stream/faces/{media_id}/progressive
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "confidence_threshold": 0.5,
  "method": "two_stage",
  "frame_interval": 10
}
```

#### Expected Notebook Structure
```
1. Configuration & Imports
2. Authentication Function
3. Database Access Functions  
4. Video Metadata Retrieval
5. Progressive Face Detection Test
6. Results Analysis & Visualization
7. Clear Face Data Module (independent)
```

### Success Criteria

#### ✅ Authentication Success
- [ ] Successfully authenticate with test user credentials
- [ ] Receive valid JWT token
- [ ] Token works with protected endpoints

#### ✅ Data Access Success  
- [ ] Access test video through authenticated endpoints
- [ ] Retrieve complete video metadata
- [ ] Confirm video file exists and is accessible

#### ✅ Progressive Face Detection Success
- [ ] Execute progressive face detection on test video
- [ ] Receive actual face detection results
- [ ] Display detection data (coordinates, confidence scores)
- [ ] Validate detection accuracy

#### ✅ Notebook Independence
- [ ] Notebook runs completely independent of main application UI
- [ ] All functionality accessible through code cells
- [ ] Clear separation between test execution and cleanup
- [ ] Reproducible results

### Implementation Notes

#### Error Handling
- Comprehensive error handling for authentication failures
- Graceful handling of missing video files or access denied
- Clear error messages for debugging

#### Performance Considerations  
- Efficient database queries
- Minimal API calls for authentication
- Proper resource cleanup

#### Documentation
- Clear cell documentation explaining each step
- Examples of expected outputs
- Troubleshooting guide for common issues

---

### Issue Status: **✅ RESOLVED**

This issue has been successfully implemented with Flutter-inspired complete video face detection and comprehensive coordinate visualization.

---

## Issue #002: Multi-Video Metadata Extraction and Analysis

### Overview
Enhance the `person_trails.ipynb` notebook to support multiple video files by implementing a workflow that mirrors the Flutter gallery functionality. The notebook should be able to process a list of video UUIDs, retrieve their file paths and metadata, and perform comprehensive analysis across multiple videos.

### Requirements

#### 1. **Multi-Video UUID Management**
- **Requirement**: Store multiple video UUIDs in a configurable list
- **Purpose**: Enable batch processing of multiple video files
- **Implementation**: Create a list variable containing video UUIDs for processing
- **Example**:
  ```python
  VIDEO_UUIDS = [
      "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e",
      "4cf362b1-3e05-4e85-81c7-c08a98c7e41b",
      # Additional UUIDs...
  ]
  ```

#### 2. **Flutter Gallery-Style Metadata Retrieval**
- **Requirement**: Replicate the metadata retrieval functionality from `http://localhost:3000/#/gallery`
- **Target**: Extract file path information for each video UUID
- **Expected Data**:
  - File path (e.g., `media/4cf362b1-3e05-4e85-81c7-c08a98c7e41b/video/2025/07/54c4666b56ff8b9dbb55abcafbb3c23f.mp4`)
  - Video metadata accessible through authenticated endpoints
- **Implementation**: Use authenticated API calls to retrieve video metadata like Flutter gallery

#### 3. **Integration with video_metadata_extractor.py**
- **Requirement**: Utilize existing video metadata extraction functionality
- **Source**: Extract relevant code from `video_metadata_extractor.py`
- **Target Data**:
  - Complete video metadata (duration, FPS, resolution, codec)
  - Frame count information
  - File properties (size, format, creation date)
- **Implementation**: Adapt video_metadata_extractor.py code for notebook usage

#### 4. **Batch Processing Workflow**
- **Requirement**: Process all videos in the UUID list systematically
- **Process**:
  1. Iterate through each UUID in the list
  2. Retrieve file path via authenticated API (Flutter gallery method)
  3. Extract comprehensive metadata using video_metadata_extractor functionality
  4. Store results in structured format
- **Error Handling**: Graceful handling of missing videos or extraction failures

#### 5. **Comprehensive Metadata Output**
- **Requirement**: Display detailed metadata for each processed video
- **Format**: Structured output showing:
  - Video UUID and file path
  - Technical specifications (resolution, duration, FPS, codec)
  - Frame information and file properties
  - Processing status and any errors
- **Implementation**: Clear, formatted output for each video

### Technical Specifications

#### Multi-Video Processing Cell Structure
```python
# Cell 5: Multi-Video Metadata Extraction
def process_multiple_videos(video_uuids: List[str], auth_token: str) -> Dict[str, Any]:
    """Process multiple videos and extract metadata for each."""
    
    results = {}
    
    for uuid in video_uuids:
        try:
            # 1. Get file path via Flutter gallery method
            file_path = get_video_file_path(uuid, auth_token)
            
            # 2. Extract metadata using video_metadata_extractor functionality
            metadata = extract_video_metadata(file_path)
            
            # 3. Store results
            results[uuid] = {
                'file_path': file_path,
                'metadata': metadata,
                'status': 'success'
            }
            
        except Exception as e:
            results[uuid] = {
                'error': str(e),
                'status': 'failed'
            }
    
    return results
```

#### Flutter Gallery API Integration
```python
def get_video_file_path(uuid: str, auth_token: str) -> str:
    """Retrieve video file path using Flutter gallery methodology."""
    
    # Use same endpoint as Flutter gallery
    metadata_url = f"{NGINX_BASE_URL}/api/v1/media/{uuid}/metadata"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = requests.get(metadata_url, headers=headers)
    
    if response.status_code == 200:
        metadata = response.json()
        return metadata.get('file_path')
    else:
        raise Exception(f"Failed to retrieve metadata for {uuid}")
```

#### Video Metadata Extraction Integration
```python
def extract_video_metadata(file_path: str) -> Dict[str, Any]:
    """Extract comprehensive video metadata using video_metadata_extractor functionality."""
    
    # Adapted from video_metadata_extractor.py
    # - Frame count extraction
    # - Technical specifications
    # - File properties
    # - Duration and timing information
    
    return {
        'duration': duration,
        'fps': fps,
        'frame_count': frame_count,
        'resolution': {'width': width, 'height': height},
        'codec': codec,
        'file_size': file_size,
        # Additional metadata...
    }
```

### Expected Notebook Structure Enhancement

```
Existing Cells (1-4): Configuration, Authentication, Database Access
NEW Cell 5: Multi-Video Metadata Extraction and Processing
Cell 6: Single Video Metadata (existing, now optional)
Cells 7+: Face Detection and Analysis (existing)
```

### Success Criteria

#### ✅ Multi-Video Support
- [ ] Successfully process multiple video UUIDs from a configurable list
- [ ] Retrieve file paths for each video using Flutter gallery methodology
- [ ] Handle missing videos or access errors gracefully

#### ✅ Metadata Extraction
- [ ] Extract comprehensive metadata for each video using video_metadata_extractor functionality
- [ ] Include frame count, technical specifications, and file properties
- [ ] Provide structured, detailed output for each video

#### ✅ Integration Quality
- [ ] Seamless integration with existing notebook workflow
- [ ] Maintain compatibility with single-video processing
- [ ] Clean, formatted output that's easy to analyze

#### ✅ Error Handling and Robustness
- [ ] Graceful handling of authentication failures
- [ ] Clear error messages for missing or inaccessible videos
- [ ] Continue processing remaining videos when individual videos fail

### Implementation Notes

#### Code Reuse Strategy
- Extract relevant functionality from `video_metadata_extractor.py`
- Adapt Flutter gallery API calls for programmatic access
- Maintain consistency with existing authentication workflow

#### Performance Considerations
- Efficient batch processing with progress indicators
- Minimal redundant API calls
- Proper resource management for video file access

#### Output Format
- Clear tabular or structured display of metadata
- Summary statistics across all processed videos
- Easy identification of processing failures

---

### Issue Status: **✅ RESOLVED**

This issue has been successfully implemented with complete multi-video metadata extraction functionality that mirrors Flutter gallery methodology and integrates video_metadata_extractor.py capabilities.

---

## Issue #003: Distance Calculations for Face Detection Points

### Overview
Enhance the face detection results from `execute_simple_complete_face_detection` by calculating real-world distance measurements for each detected face. This will provide depth perception and spatial analysis capabilities to the face detection system.

### Background
The `simple_complete_results` from the simplified complete face detection function contains face coordinate data with bounding box information. By applying distance calculation functions, we can enhance each face detection point with real-world distance values based on the face bounding box width (`rect_width`).

### Technical Approach

#### 1. **Data Source**
- **Input**: `simple_complete_results` from `execute_simple_complete_face_detection()`
- **Structure**: Face detection results with frame-by-frame face coordinates
- **Key Data**: Bounding box coordinates `[x, y, width, height]` for each detected face

#### 2. **Distance Calculation Functions**
Two core functions are available for distance calculations:

```python
def calculate_distance(rect_width, focal_length=4.74, sensor_width=5.76, 
                      real_world_width=0.15, sensor_width_pixels=1920):
    """
    Calculate distance based on face bounding box width using camera parameters.
    
    Args:
        rect_width: Width of face bounding box in pixels
        focal_length: Camera focal length in mm (default: 4.74)
        sensor_width: Camera sensor width in mm (default: 5.76)
        real_world_width: Average human face width in meters (default: 0.15)
        sensor_width_pixels: Sensor width in pixels (default: 1920)
    
    Returns:
        distance_pixels: Calculated distance in pixel units
    """

def adjust_distance_for_angle(distance_pixels, x_rect, frame_width=1920, fov=90):
    """
    Adjust distance calculation based on face position within frame (angle compensation).
    
    Args:
        distance_pixels: Base distance from calculate_distance()
        x_rect: X-coordinate of face center
        frame_width: Video frame width (default: 1920)
        fov: Camera field of view in degrees (default: 90)
    
    Returns:
        adjusted_distance_pixels: Angle-compensated distance
        horizontal_distance_pixels: Horizontal offset distance
        y_horizontal_value_pixels: Y-component of adjusted distance
    """
```

#### 3. **Implementation Steps**

##### Step 1: Extract Face Detection Data
- Parse `simple_complete_results["frame_results"]`
- Extract face bounding boxes from each frame
- Identify `rect_width` (bounding box width) for each face

##### Step 2: Apply Distance Calculations
- For each detected face:
  - Calculate base distance using `calculate_distance(rect_width)`
  - Apply angle compensation using `adjust_distance_for_angle()`
  - Store enhanced coordinates with distance data

##### Step 3: Enhanced Data Structure
Create enhanced face detection results with distance information:

```python
enhanced_face_data = {
    "frame_number": int,
    "face_id": int,
    "original_bbox": [x, y, width, height],
    "coordinates": {
        "x": int, "y": int, 
        "center_x": float, "center_y": float,
        "width": int, "height": int
    },
    "distance_calculations": {
        "rect_width": int,
        "base_distance_pixels": float,
        "adjusted_distance_pixels": float,
        "horizontal_distance_pixels": float,
        "y_horizontal_value_pixels": float,
        "angle_compensation": float
    },
    "confidence": float,
    "method": str,
    "timestamp": float
}
```

### Requirements

#### ✅ Data Processing
- [ ] Extract all face detection points from `simple_complete_results`
- [ ] Calculate `rect_width` from bounding box data for each face
- [ ] Apply `calculate_distance()` function to each face
- [ ] Apply `adjust_distance_for_angle()` for position-based corrections

#### ✅ Distance Enhancement
- [ ] Enhance each face detection point with distance values
- [ ] Preserve original coordinate data alongside distance calculations
- [ ] Handle edge cases (very small/large faces, frame boundaries)
- [ ] Validate distance calculations for reasonableness

#### ✅ Output Structure
- [ ] Create enhanced dataset with original + distance data
- [ ] Maintain compatibility with existing visualization functions
- [ ] Provide summary statistics for distance measurements
- [ ] Enable filtering/analysis by distance ranges

#### ✅ Visualization Support
- [ ] Update coordinate visualization to include distance data
- [ ] Create distance-based color coding for face plots
- [ ] Add distance distribution charts
- [ ] Show distance vs. confidence correlations

### Expected Outcomes

#### 1. **Enhanced Face Detection Dataset**
- All faces from `simple_complete_results` enhanced with distance calculations
- Real-world spatial awareness for each detected face
- Position-compensated distance measurements

#### 2. **Distance Analytics**
- Distance distribution across video frames
- Correlation between face size and calculated distance
- Spatial positioning analysis with depth perception

#### 3. **Improved Visualizations**
- Distance-aware coordinate plotting
- Depth-based face clustering analysis
- Temporal distance tracking across video timeline

### Implementation Notes

#### Camera Parameters
- **Focal Length**: 4.74mm (default smartphone camera)
- **Sensor Width**: 5.76mm (typical smartphone sensor)
- **Real-World Face Width**: 0.15m (15cm average human face width)
- **Frame Resolution**: 1920x1080 (video metadata)

#### Validation Strategy
- Cross-reference distance calculations with face size expectations
- Validate angle compensation against frame position
- Compare distance trends across video timeline

#### Performance Considerations
- Process all faces in batch for efficiency
- Cache calculation parameters to avoid redundant computations
- Optimize for large datasets from complete video analysis

---

### Issue Status: **✅ RESOLVED**

This issue has been successfully implemented with complete distance calculation enhancement for face detection points. The implementation includes:

#### ✅ **Completed Implementation Features:**
- **Distance Calculation Integration**: Both `calculate_distance()` and `adjust_distance_for_angle()` functions successfully applied to all faces from `simple_complete_results`
- **Enhanced Data Structure**: Each detected face now includes comprehensive distance measurements with original coordinates preserved
- **Angle Compensation**: Position-based distance adjustments working correctly for faces across the video frame
- **Statistical Analysis**: Complete distance distribution analysis with min/max/average calculations and standard deviation
- **Real-World Context**: Approximate meter conversions providing practical distance understanding
- **Error Handling**: Robust processing with detailed error reporting and validation

#### ✅ **Technical Implementation:**
- **Data Source**: Successfully processes `simple_complete_results` from `execute_simple_complete_face_detection()`
- **Enhancement Function**: `enhance_faces_with_distance_calculations()` implemented in cell 13
- **Output Variable**: Enhanced dataset available in `enhanced_distance_results` variable
- **Processing Pipeline**: Complete frame-by-frame face enhancement with progress tracking

#### ✅ **Enhanced Data Structure Per Face:**
```python
{
    "coordinates": {x, y, center_x, center_y, width, height, area},
    "distance_calculations": {
        "rect_width": int,                    # Bounding box width used for calculation
        "base_distance_pixels": float,        # Base distance from calculate_distance()
        "adjusted_distance_pixels": float,    # Angle-compensated distance
        "horizontal_distance_pixels": float,  # Horizontal offset component
        "y_horizontal_value_pixels": float,   # Y-component of adjusted distance
        "angle_degrees": float,               # Face position angle from center
        "angle_compensation_factor": float    # Compensation multiplier applied
    },
    "detection_metadata": {confidence, method, original_frame_data}
}
```

#### ✅ **Execution Results:**
- **Complete Integration**: All faces from simplified face detection enhanced with distance data
- **Statistical Output**: Distance range, average, and distribution analysis completed
- **Performance**: Efficient processing of all detected faces with detailed progress output
- **Data Preservation**: Original detection data maintained alongside distance enhancements

#### ✅ **Deliverables Completed:**
- [x] Extract all face detection points from `simple_complete_results`
- [x] Calculate `rect_width` from bounding box data for each face
- [x] Apply `calculate_distance()` function to each face
- [x] Apply `adjust_distance_for_angle()` for position-based corrections
- [x] Enhance each face detection point with distance values
- [x] Preserve original coordinate data alongside distance calculations
- [x] Handle edge cases and validate distance calculations
- [x] Create enhanced dataset with original + distance data
- [x] Maintain compatibility with existing visualization functions
- [x] Provide summary statistics for distance measurements
- [x] Enable filtering/analysis by distance ranges

**Implementation Location**: Cell 13 in `person_trails.ipynb`  
**Result Variable**: `enhanced_distance_results`  
**Resolution Date**: January 26, 2025

---

## Issue #015: Classification Results Dictionary Output and Global Accessibility

### Overview
Enhanced the face classification and tracking system (Cell 15) to print the complete classification results dictionary and store it globally for access in subsequent cells, enabling comprehensive data inspection and cross-cell analysis.

### Problem Statement
The face classification system in Cell 15 (`classify_and_track_faces()` function) was generating comprehensive tracking data but:
- **Limited Output Visibility**: Classification results dictionary was returned but not displayed for inspection
- **Isolated Data**: Results were only available within the cell execution scope
- **No Cross-Cell Access**: Other cells couldn't access the detailed classification data for table creation or further analysis
- **Debugging Challenges**: Difficult to inspect the complete data structure and validate classification accuracy

### ✅ **Solution Implemented**

#### ✅ **Dictionary Output Enhancement:**
- **Complete JSON Display**: Added pretty-printed JSON output of the entire `classification_results` dictionary
- **Structured Output**: 80-character separator lines and clear section headers for readability
- **Statistics Summary**: Display of key metrics (total faces, unique individuals, dictionary structure)
- **Error Handling**: Graceful fallback with structure information if JSON printing fails

#### ✅ **Global Data Storage:**
- **`classification_json`**: JSON string representation stored globally for export and string operations
- **`classification_results_dict`**: Original Python dictionary stored globally for programmatic access
- **Persistent Access**: Data remains available across all subsequent notebook cells
- **Dual Format Support**: Both string and dictionary formats available for different use cases

#### ✅ **Dictionary Structure Printed:**
```json
{
  "classified_faces": [
    {
      "classification_id": 100,
      "frame_number": 110,
      "original_face": { /* complete face data */ },
      "position": {"x": 418, "y": 1384, "distance": 2842},
      "match_type": "new" || "tracked",
      "match_confidence": 1.0,
      "match_details": { /* tracking accuracy metrics */ }
    }
  ],
  "unique_track_ids": [100, 101, 102, ...],
  "total_faces": 12,
  "unique_individuals": 12,
  "tracked_instances": 0,
  "new_instances": 12,
  "frames_processed": 11,
  "tolerance_percent": 30,
  "classification_metadata": {
    "id_range": {"min": 100, "max": 111},
    "processing_timestamp": 1643234567.123
  }
}
```

#### ✅ **Cross-Cell Data Access:**
```python
# Access summary statistics
print(f"Total faces: {classification_results_dict['total_faces']}")
print(f"Unique individuals: {classification_results_dict['unique_individuals']}")

# Access individual face data
faces = classification_results_dict['classified_faces']
for face in faces:
    print(f"ID: {face['classification_id']}, Frame: {face['frame_number']}")

# Access JSON string for export
json_string = classification_json
```

#### ✅ **Enhanced Output Format:**
- **Section Headers**: Clear visual separation with emoji indicators (📋, 📊, 💾)
- **Progress Indicators**: Status confirmations for successful storage operations
- **Multiple Access Methods**: Instructions for both dictionary and JSON string usage
- **Validation Messages**: Confirmation of global variable creation and accessibility

#### ✅ **Technical Implementation:**
- **Location**: Cell 15 `classify_and_track_faces()` function
- **Trigger**: Executes automatically during classification completion
- **Storage Method**: `globals()` function for universal notebook access
- **Fallback Protection**: Ensures data storage even if JSON conversion fails
- **Import Handling**: Automatic JSON module import within the function scope

#### ✅ **Benefits Achieved:**
- **Complete Transparency**: Full visibility into classification algorithm results
- **Data Validation**: Easy inspection of face tracking accuracy and classification assignments
- **Table Creation Ready**: Direct access to frame numbers, face IDs, and classification numbers
- **Export Capability**: JSON string format ready for external file export
- **Debugging Enhanced**: Immediate access to all classification metadata and tracking details
- **Development Workflow**: Seamless data flow between analysis cells

#### ✅ **Global Variables Created:**
- **`classification_json`** (str): Complete JSON string representation of results
- **`classification_results_dict`** (dict): Original Python dictionary with full data structure
- **Access Status**: ✅ Available in notebook kernel variables
- **Data Integrity**: ✅ Complete face tracking data preserved with all metadata

#### ✅ **Use Cases Enabled:**
1. **Table Generation**: Create comprehensive tables with frame numbers, face IDs, and classification numbers
2. **Data Export**: Save classification results to external JSON files
3. **Statistical Analysis**: Perform cross-cell analysis of tracking performance
4. **Visualization Enhancement**: Access detailed data for custom plotting and analysis
5. **Debugging Support**: Inspect specific face tracking decisions and match confidence scores

**Implementation Location**: Cell 15 in `person_trails.ipynb`  
**Global Variables**: `classification_json`, `classification_results_dict`  
**Resolution Date**: January 27, 2025
