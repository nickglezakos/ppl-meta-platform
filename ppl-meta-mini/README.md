# PPL Meta Mini - Standalone Face Analytics Microservice

A lightweight, self-contained microservice for advanced face detection analysis and age estimation with complete TensorFlow + DeepFace integration.

## Current Production Build: Beta085

This is the **production-ready beta085** build with complete age detection capabilities using:
- **TensorFlow 2.12.0** + **DeepFace 0.0.75** for age estimation
- **Cython compilation** for performance optimization
- **Multi-stage Docker build** for minimal runtime footprint
- **Linux AMD64** platform with Windows Docker Desktop compatibility

## Features

- **Age Detection**: Complete DeepFace integration for adult/underaged classification
- **Advanced Face Grouping**: Sophisticated percentage-based tolerance matching (20% tolerance)
- **Video Preprocessing**: Aggressive compression for optimal face detection accuracy
- **Cython Performance**: Compiled core modules for native C speed
- **Standalone Operation**: No external service dependencies required

## Quick Start

### Local Development

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the Service**:
```bash
python src/main.py
```

The service will start on `http://localhost:8004`

## Production Files (Beta085)

The current production build uses these files at the root level:

- **`Dockerfile.tensorflow`** - Multi-stage Docker build with TensorFlow + DeepFace
- **`requirements.tensorflow.txt`** - Complete dependencies (TensorFlow 2.12.0, DeepFace 0.0.75)
- **`requirements.runtime.txt`** - Minimal runtime dependencies
- **`setup_cython_dlib.py`** - Cython compilation setup for performance optimization
- **`build.sh`** - Official build script for beta085
- **`docker-compose.yml`** - Production docker-compose configuration
- **`ppl-meta-mini-beta085.tar`** - Production Docker image (1.5GB)

### Legacy Files Archive

All legacy/experimental files have been moved to `./archive/`:
- `./archive/docker-legacy/` - Legacy Dockerfiles and docker-compose files
- `./archive/requirements-legacy/` - Legacy dependency files
- `./archive/build-scripts-legacy/` - Legacy build scripts
- `./archive/docker-tar-files/` - Legacy Docker images (beta081, beta083)

See `./archive/README.md` for detailed archive documentation.

### Docker Deployment

1. **Build Image**:
```bash
./build.sh
```

2. **Run Container**:
```bash
docker run -d --name ppl-meta-mini -p 8004:8004 nickglezakos/ppl-meta-mini-beta085:latest

## API Endpoints

### Health Check
- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed system information

### Analytics
- `POST /api/v1/analytics/group-faces` - Apply advanced face grouping
- `POST /api/v1/analytics/visualize-trajectories` - Generate 3D visualizations
- `POST /api/v1/analytics/analyze-coordinates` - Analyze face coordinates
- `GET /api/v1/analytics/demo-data` - Get sample data for testing

### Documentation
- `/docs` - Interactive API documentation (Swagger)
- `/redoc` - Alternative API documentation

## Usage Examples

### Face Grouping

```bash
curl -X POST "http://localhost:8004/api/v1/analytics/group-faces" \
  -H "Content-Type: application/json" \
  -d '{
    "face_data": [
      {"Frame_Number": 1, "Face_ID": "A", "Position_X": 100, "Position_Y": 200},
      {"Frame_Number": 1, "Face_ID": "B", "Position_X": 300, "Position_Y": 180}
    ],
    "max_faces_per_frame": 2,
    "proximity_threshold": 50.0
  }'
```

### 3D Visualization

```bash
curl -X POST "http://localhost:8004/api/v1/analytics/visualize-trajectories" \
  -H "Content-Type: application/json" \
  -d '{
    "face_data": [...],
    "visualization_type": "3d_trajectory",
    "x_axis": "Position_X",
    "y_axis": "Position_Y",
    "z_axis": "Frame_Number",
    "reverse_z": false
  }'
```

## Architecture

```
ppl-meta-mini/
├── src/
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   ├── health.py        # Health endpoints
│   │   └── analytics.py     # Analytics endpoints
│   ├── core/
│   │   ├── face_grouping.py # Face grouping algorithms
│   │   └── visualization.py # Visualization engine
│   └── models/
│       └── schemas.py       # Pydantic models
├── Dockerfile               # Container configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Configuration

The service uses the following default settings:

- **Port**: 8004 (configurable via `PORT` environment variable)
- **Host**: 0.0.0.0 (binds to all interfaces)
- **CORS**: Enabled for all origins (configure for production)

## Environment Variables

- `PORT`: Service port (default: 8004)

## Dependencies

- FastAPI: Web framework
- Pandas: Data processing
- Plotly: Interactive visualizations
- Pydantic: Data validation
- Uvicorn: ASGI server

## Production Considerations

1. **Security**: Configure CORS origins for production
2. **Monitoring**: Add logging and metrics collection
3. **Scaling**: Use multiple worker processes with Gunicorn
4. **Persistence**: Add database for storing analysis results

## License

Part of the PPL Meta Platform project.
