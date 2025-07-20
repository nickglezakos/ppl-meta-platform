# PPL Meta Vision Service

Face detection microservice for the PPL Meta Platform - Pure Python Development.

## Overview

The PPL Meta Vision Service provides face detection capabilities using multiple detection methods (Haar cascades, Dlib, MTCNN). This service is part of the PPL Meta Platform microservices ecosystem.

## Features

- **Multiple Detection Methods**: Haar cascades, Dlib, MTCNN
- **RESTful API**: FastAPI-based with automatic documentation
- **High Performance**: Async processing and optimized models
- **Scalable**: Designed for horizontal scaling
- **Pure Python**: No Docker required for development

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /models` - Available detection models
- `POST /detect` - Face detection (JSON payload)
- `POST /detect/file` - Face detection (file upload)
- `GET /docs` - Interactive API documentation

## Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to service directory
cd ppl-meta-vision

# Setup Python virtual environment and install dependencies
./setup_env.sh
```

### 2. Prepare Face Detection Models

```bash
# Copy face detector from notebooks (if not already done)
cp ../notebooks/extracted_face_detector.py src/
```

### 3. Start the Service

```bash
# Using the start script (recommended)
./start_service.sh

# Or manually
source venv/bin/activate
python src/main.py
```

### 4. Test the Service

```bash
# Health check
curl http://localhost:8003/health

# API documentation
open http://localhost:8003/docs
```

## Development Mode

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service with auto-reload
uvicorn src.main:app --host 0.0.0.0 --port 8003 --reload
```

### Integration with PPL Meta Platform

This service integrates with:
- **PPL Meta Gateway** (port 8080) - Request routing and authentication
- **PPL Meta Orchestrator** (port 8002) - Service coordination
- **PPL Meta Node Service** (port 8001) - Data processing
- **PPL Meta Media Service** (port 8000) - Media handling

## Configuration

Service configuration is in `src/main.py`:
- Service port: 8003
- Service name: ppl-meta-vision
- API version: 1.0.0

## Integration with Existing PPL Meta Tasks

This service can be started using the existing PPL Meta Platform tasks. Add to `.vscode/tasks.json`:

```json
{
    "label": "🎯 Start Vision Service (Local Python)",
    "type": "shell",
    "command": "cd ppl-meta-vision && source venv/bin/activate && python src/main.py",
    "group": "build",
    "isBackground": true
}
```

## Testing

### Run Test Suite

```bash
# Activate environment
source venv/bin/activate

# Run tests
python test_service.py

# Or with wait time for startup
python test_service.py --wait 10
```

### Manual Testing

```bash
# Test with curl
curl -X POST http://localhost:8003/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "base64_encoded_image_here",
    "methods": ["haar"],
    "confidence_threshold": 0.5
  }'
```

## Generated from VIS-001.3

This service was generated from the VIS-001.3 Microservice Implementation phase,
building on the face detection code extracted in VIS-001.2.

---

**Development Philosophy**: Pure Python development for rapid iteration, Docker deployment later for production.
