# PPL Meta Phase 1: Enhanced Person Detection System

## 🚀 Overview

Phase 1 delivers a comprehensive enhancement to the PPL Meta person detection system with session-based processing, 3D distance calculation, facial embeddings, and person routes analytics.

## ✨ Key Features Delivered

### 🔄 Session-Based Processing
- **No duplicate prevention** - Supports unlimited re-executions
- **Session UUID tracking** for every workflow execution
- **Master workflow lifecycle management** with detailed status tracking
- **Background task processing** for non-blocking operations

### 📏 3D Distance Calculation
- **Autonomous system methodology** using `1,000,000 / face_area` formula
- **Real-time distance estimation** from camera for every detected face
- **Distance-based analytics** for spatial understanding
- **Camera proximity tracking** for security applications

### 🧠 512-Dimensional Facial Embeddings
- **DeepFace integration** with Facenet512 model
- **Vector similarity search** using PostgreSQL pgvector extension
- **Face recognition capabilities** with configurable similarity thresholds
- **Embedding quality assessment** based on face image characteristics

### 🗺️ Person Routes Tracking
- **Movement analytics** with X, Y, distance coordinates
- **Velocity calculations** between consecutive detections
- **Spatial analysis** with heatmap generation
- **Direction tracking** with movement patterns
- **Time-in-frame analysis** for behavior understanding

### 🔍 Advanced Search & Analytics
- **Vector search** for finding similar faces across sessions
- **Spatial heatmaps** for movement pattern visualization
- **Movement statistics** including velocity, distance, and time metrics
- **Session-based analytics** for workflow performance tracking

## 📦 System Architecture

### Components

1. **Enhanced Vision Service** (`phase1_enhanced_vision_service.py`)
   - Face detection with distance calculation
   - DeepFace embedding generation
   - Person routes creation
   - Session-based processing

2. **Master Lifecycle Workflow Controller** (`phase1_orchestrator_workflow.py`)
   - Session management and tracking
   - Background workflow execution
   - REST API endpoints
   - Analytics and search capabilities

3. **Database Client** (`phase1_database_client.py`)
   - PostgreSQL with pgvector integration
   - Session-based data storage
   - Vector similarity search
   - Spatial analytics queries

4. **Integration Layer** (`phase1_integration.py`)
   - FastAPI application
   - Service coordination
   - Health monitoring
   - Development endpoints

### Database Schema

The system uses PostgreSQL with the pgvector extension:

- **`persons_lifecycle_master_workflows`** - Session management and tracking
- **`person_routes`** - Movement tracking with spatial coordinates
- **`face_detections`** - Enhanced face data with embeddings and distance
- **`person_objects`** - Person entities with movement summaries

## 🛠️ Installation & Deployment

### Quick Start

1. **Run the deployment script:**
   ```bash
   ./deploy_phase1.sh
   ```

2. **Start the system:**
   ```bash
   ./start_phase1.sh
   ```

3. **Check system health:**
   ```bash
   ./health_check_phase1.sh
   ```

### Manual Installation

#### Prerequisites
- Python 3.8+
- PostgreSQL 12+ with pgvector extension
- Required Python packages (see requirements below)

#### Database Setup
```bash
# Install pgvector extension
psql -d your_database -c "CREATE EXTENSION vector;"

# Deploy schema
psql -d your_database -f phase1_database_schema.sql
```

#### Python Dependencies
```bash
pip install fastapi uvicorn asyncpg python-multipart
pip install opencv-python pillow numpy deepface
pip install python-dotenv requests
```

#### Environment Configuration
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=ppl_meta
export DB_USER=ppl_user
export DB_PASSWORD=ppl_password
export API_PORT=8010
```

#### Start Application
```bash
python phase1_integration.py
```

## 🌐 API Usage

### Base URL
```
http://localhost:8010
```

### Core Endpoints

#### 1. Execute Workflow
```http
POST /api/v1/workflows/execute
Content-Type: application/json

{
  "source_identifier": "camera-lobby-main",
  "source_type": "camera_recording",
  "source_id": "media-12345",
  "execution_trigger": "automatic",
  "workflow_types": ["face_detection", "person_routes"],
  "configuration": {
    "confidence_threshold": 0.5,
    "frames_per_second": 3,
    "enable_distance_calculation": true,
    "enable_embedding_generation": true,
    "enable_route_tracking": true
  }
}
```

#### 2. Check Workflow Status
```http
GET /api/v1/workflows/status/{session_uuid}
```

#### 3. Person Routes Analytics
```http
POST /api/v1/workflows/analytics/person-routes
Content-Type: application/json

{
  "time_range_hours": 24,
  "confidence_threshold": 0.5,
  "include_spatial_analysis": true
}
```

#### 4. Search Similar Faces
```http
POST /api/v1/workflows/search/similar-faces
Content-Type: application/json

{
  "embedding_vector": [0.1, 0.2, 0.3, ...], // 512 dimensions
  "similarity_threshold": 0.8,
  "limit": 10
}
```

#### 5. System Health
```http
GET /health
```

#### 6. System Metrics
```http
GET /metrics
```

### Development Endpoints

#### Quick Test
```http
POST /dev/quick-test
```

#### Example Routes
```http
GET /dev/example-routes
```

## 📊 Configuration Options

### Vision Service Configuration
```python
{
  "distance_multiplier": 1000000.0,     # Autonomous system formula
  "embedding_model": "Facenet512",      # DeepFace model
  "detector_backend": "opencv",         # Face detection backend
  "confidence_threshold": 0.5,          # Minimum detection confidence
  "frames_per_second": 3,               # Processing frame rate
  "enable_distance_calculation": true,  # 3D distance feature
  "enable_embedding_generation": true,  # Facial embeddings
  "enable_route_tracking": true         # Person routes
}
```

### Database Configuration
```python
{
  "host": "localhost",
  "port": 5432,
  "database": "ppl_meta",
  "username": "ppl_user",
  "password": "ppl_password"
}
```

## 📈 Monitoring & Analytics

### Health Monitoring
- **Service status** for all components
- **Database health metrics** including connection status
- **Active session tracking** with real-time counts
- **Performance metrics** for processing times

### Analytics Dashboard
- **Embedding statistics** (total embeddings, confidence scores)
- **Route analytics** (movement patterns, velocities)
- **Session metrics** (completion rates, processing times)
- **Spatial analysis** (heatmaps, movement patterns)

### System Metrics
```json
{
  "system_metrics": {
    "active_sessions": 3,
    "completed_sessions_today": 15,
    "total_faces_detected_today": 247,
    "total_route_points_today": 1834,
    "embeddings_generated_today": 198
  },
  "embedding_metrics": {
    "total_embeddings": 5420,
    "unique_sessions": 89,
    "avg_confidence": 0.85
  },
  "route_analytics": {
    "unique_persons": 42,
    "total_route_points": 3256,
    "avg_velocity": 15.3,
    "max_velocity": 87.2
  }
}
```

## 🧪 Testing & Development

### Development Quick Test
```bash
curl -X POST http://localhost:8010/dev/quick-test
```

### Integration Testing
```bash
# Health check
curl http://localhost:8010/health

# System metrics
curl http://localhost:8010/metrics

# Workflow execution
curl -X POST http://localhost:8010/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "source_identifier": "test-camera",
    "source_type": "camera_recording",
    "source_id": "test-media",
    "workflow_types": ["face_detection", "person_routes"]
  }'
```

### Database Testing
```sql
-- Check workflow sessions
SELECT * FROM persons_lifecycle_master_workflows ORDER BY started_at DESC LIMIT 10;

-- Check person routes
SELECT * FROM person_routes ORDER BY created_at DESC LIMIT 10;

-- Check face detections with embeddings
SELECT id, session_uuid, confidence, distance_from_camera, 
       embedding_confidence 
FROM face_detections 
WHERE facial_embedding IS NOT NULL 
ORDER BY created_at DESC LIMIT 10;

-- Vector similarity search
SELECT id, confidence, 1 - (facial_embedding <=> '[0.1,0.2,0.3,...]'::vector) as similarity
FROM face_detections 
WHERE facial_embedding IS NOT NULL 
ORDER BY similarity DESC LIMIT 5;
```

## 🔧 Management Scripts

### Start System
```bash
./start_phase1.sh
```

### Stop System
```bash
./stop_phase1.sh
```

### Health Check
```bash
./health_check_phase1.sh
```

### Deployment
```bash
./deploy_phase1.sh
```

## 📚 API Documentation

### Interactive Documentation
Visit `http://localhost:8010/docs` for the complete interactive API documentation with:
- **Request/response schemas**
- **Try-it-out functionality**
- **Authentication details**
- **Example requests and responses**

### OpenAPI Specification
The complete OpenAPI 3.0 specification is available at:
`http://localhost:8010/openapi.json`

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check PostgreSQL status
pg_isready -h localhost -p 5432

# Check database exists
psql -h localhost -p 5432 -U ppl_user -l | grep ppl_meta

# Check pgvector extension
psql -h localhost -p 5432 -U ppl_user -d ppl_meta -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

#### DeepFace Import Error
```bash
# Install DeepFace dependencies
pip install deepface tensorflow

# For Apple Silicon Macs
pip install tensorflow-macos tensorflow-metal
```

#### Port Already in Use
```bash
# Find process using port 8010
lsof -i :8010

# Kill the process
kill -9 <PID>
```

### Logs and Debugging
- **Application logs** are printed to console
- **Database logs** can be found in PostgreSQL log directory
- **Health endpoint** provides real-time system status
- **Metrics endpoint** provides detailed performance data

## 🛣️ Roadmap

### Phase 1 ✅ (Current)
- Session-based processing
- 3D distance calculation
- Facial embeddings
- Person routes tracking
- Vector search
- Spatial analytics

### Phase 2 🔄 (Next)
- Vision Service integration
- Real-time streaming
- Advanced AI workflows
- Performance optimization

### Phase 3 📋 (Planned)
- Frontend integration
- Real-time dashboards
- Advanced analytics
- Production optimization

### Phase 4 🚀 (Future)
- Comprehensive testing
- Production deployment
- Performance tuning
- Documentation finalization

### Phase 5 🎯 (Final)
- System optimization
- Final integration
- Production readiness
- Complete documentation

## 📞 Support

For issues, questions, or contributions:

1. **Check the health endpoint**: `GET /health`
2. **Review system metrics**: `GET /metrics`
3. **Check application logs** for detailed error information
4. **Verify database connectivity** and schema deployment
5. **Ensure all dependencies** are properly installed

## 📄 License

PPL Meta Platform - Phase 1 Enhanced Person Detection System

---

**Phase 1 Status**: ✅ **DEPLOYED AND OPERATIONAL**

**Features Delivered**: 8/8 ✅
- ✅ Session-based processing (no duplicate prevention)
- ✅ 3D distance calculation using autonomous system methodology
- ✅ 512-dimensional facial embeddings with DeepFace
- ✅ Person routes tracking with movement analytics
- ✅ Vector similarity search with pgvector
- ✅ Spatial analysis and heatmap generation
- ✅ Master workflow lifecycle management
- ✅ Complete REST API for all features