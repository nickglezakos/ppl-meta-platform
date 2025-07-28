# PPL Meta Mini - Standalone Face Analytics Microservice

A lightweight, self-contained microservice for advanced face detection analysis and trajectory visualization.

## Features

- **Advanced Face Grouping**: Merge face groups when unique face IDs exceed frame capacity
- **3D Trajectory Visualization**: Interactive 3D plotting of face movements
- **Coordinate Analysis**: Statistical analysis of face detection coordinates
- **Standalone Operation**: No authentication or proxy dependencies required

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

### Docker Deployment

1. **Build Image**:
```bash
docker build -t ppl-meta-mini .
```

2. **Run Container**:
```bash
docker run -p 8004:8004 ppl-meta-mini
```

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
