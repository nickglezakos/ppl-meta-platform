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

### Issue Status: **READY FOR IMPLEMENTATION**

This issue provides a complete specification for transforming the person trails notebook into a fully functional, independent testing environment for progressive face detection capabilities.
