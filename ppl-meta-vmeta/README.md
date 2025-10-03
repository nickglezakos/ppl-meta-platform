# PPL Meta vmeta Service

Vector-based facial embeddings and person detection analytics service.

## Overview

The vmeta service provides advanced person detection capabilities using:
- 512-dimensional facial embeddings (DeepFace Facenet512)
- Vector similarity search (PostgreSQL pgvector)
- 3D distance calculations
- Session-based workflow management
- Person movement analytics

## Quick Start

### Development Mode
```bash
# Start the service
./start_vmeta.sh

# Stop the service  
./stop_vmeta.sh
```

### Docker Mode
```bash
# Build and start with Docker Compose
docker-compose up --build

# Stop
docker-compose down
```

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /` - Service information

### Workflows
- `POST /api/v1/workflows/execute` - Execute face processing workflow
- `GET /api/v1/workflows/status/{session_uuid}` - Get workflow status

### Embeddings
- `POST /api/v1/embeddings/generate` - Generate facial embeddings
- `POST /api/v1/embeddings/search` - Vector similarity search

### Analytics
- `POST /api/v1/analytics/person-routes` - Person movement analytics
- `GET /api/v1/analytics/heatmap` - Spatial heatmap generation

## Configuration

Environment variables:
- `VMETA_HOST` - Service host (default: 0.0.0.0)
- `VMETA_PORT` - Service port (default: 8008)
- `DB_HOST` - Database host
- `DB_PORT` - Database port
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

## Integration

### Service Discovery
The vmeta service automatically registers with ppl-meta-discovery:

```json
{
    "name": "vmeta",
    "service_type": "backend",
    "version": "1.0.0",
    "host": "localhost",
    "port": 8008,
    "capabilities": [
        "facial_embeddings",
        "vector_similarity_search",
        "session_based_workflows",
        "3d_distance_calculation", 
        "person_routes_analytics"
    ]
}
```

### Orchestrator Integration
The orchestrator coordinates with vmeta for enhanced processing:

```python
# Basic face detection (vision service)
faces = await vision_service.detect_faces(media_id)

# Enhanced processing (vmeta service)
enhanced_results = await vmeta_service.process_with_embeddings(faces)
```

## Development

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests
pytest
```

### API Documentation
- OpenAPI docs: http://localhost:8008/docs
- Redoc: http://localhost:8008/redoc
