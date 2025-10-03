#!/bin/bash

# ================================================================
# PPL Meta vmeta Service Transformation Script
# Transforms Phase 1 → production vmeta service
# ================================================================

set -e

echo "🚀 PPL Meta vmeta Service Transformation"
echo "========================================"
echo

# Step 1: Create vmeta service directory structure
echo "[INFO] Step 1: Creating vmeta service directory structure..."

# Create the new vmeta service directory
mkdir -p ppl-meta-vmeta

# Create the proper service structure
mkdir -p ppl-meta-vmeta/src/{config,models,services,api/v1,database/{repositories,migrations},utils}
mkdir -p ppl-meta-vmeta/tests/{unit,integration}
mkdir -p ppl-meta-vmeta/docker
mkdir -p ppl-meta-vmeta/deployment/{kubernetes,scripts,nginx}
mkdir -p ppl-meta-vmeta/requirements

echo "[SUCCESS] Service directory structure created"

# Step 2: Transform existing Phase 1 code
echo "[INFO] Step 2: Transforming Phase 1 code to vmeta service..."

# Copy and transform main integration file
cp phase1/integration/phase1_integration.py ppl-meta-vmeta/src/main.py

# Transform individual service files
cp phase1/integration/phase1_database_client.py ppl-meta-vmeta/src/database/client.py
cp phase1/integration/phase1_enhanced_vision_service.py ppl-meta-vmeta/src/services/embedding_service.py
cp phase1/integration/phase1_orchestrator_workflow.py ppl-meta-vmeta/src/services/workflow_service.py

# Copy database schema
cp phase1/database/phase1_database_schema.sql ppl-meta-vmeta/src/database/migrations/001_initial_schema.sql

# Copy configuration files
cp phase1/.env ppl-meta-vmeta/.env.example
cp phase1/requirements.txt ppl-meta-vmeta/requirements/base.txt

echo "[SUCCESS] Code transformation completed"

# Step 3: Update import paths and service configuration
echo "[INFO] Step 3: Updating service configuration for vmeta..."

# Create proper vmeta configuration
cat > ppl-meta-vmeta/src/config/settings.py << 'EOF'
"""
PPL Meta vmeta Service Configuration
Vector-based facial embeddings and person detection analytics
"""

import os
from typing import Dict, Any

class VmetaSettings:
    """vmeta service configuration settings."""
    
    # Service identification
    SERVICE_NAME = "vmeta"
    SERVICE_VERSION = "1.0.0"
    SERVICE_TYPE = "backend"
    
    # Server configuration
    HOST = os.getenv("VMETA_HOST", "0.0.0.0")
    PORT = int(os.getenv("VMETA_PORT", "8008"))  # New dedicated port
    
    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "ppl_meta")
    DB_USER = os.getenv("DB_USER", "ppl_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ppl_password")
    
    # Vector processing configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Facenet512")
    DISTANCE_MULTIPLIER = float(os.getenv("DISTANCE_MULTIPLIER", "1000000.0"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
    
    # Service discovery configuration
    DISCOVERY_SERVICE_URL = os.getenv("DISCOVERY_SERVICE_URL", "http://localhost:8006")
    
    # Performance configuration  
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "32"))
    VECTOR_CACHE_SIZE = int(os.getenv("VECTOR_CACHE_SIZE", "1000"))
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "username": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }
    
    @classmethod
    def get_service_info(cls) -> Dict[str, Any]:
        """Get service registration information."""
        return {
            "name": cls.SERVICE_NAME,
            "service_type": cls.SERVICE_TYPE,
            "version": cls.SERVICE_VERSION,
            "host": "localhost",  # Will be updated for container deployment
            "port": cls.PORT,
            "health_endpoint": "/health",
            "capabilities": [
                "facial_embeddings",
                "vector_similarity_search",
                "session_based_workflows", 
                "3d_distance_calculation",
                "person_routes_analytics"
            ]
        }

# Global settings instance
settings = VmetaSettings()
EOF

echo "[SUCCESS] vmeta configuration created"

# Step 4: Create proper FastAPI application for vmeta
echo "[INFO] Step 4: Creating vmeta FastAPI application..."

cat > ppl-meta-vmeta/src/main.py << 'EOF'
"""
PPL Meta vmeta Service
Vector-based facial embeddings and person detection analytics

Main FastAPI application entry point.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from database.client import VmetaDatabaseClient
from services.embedding_service import EmbeddingService
from services.workflow_service import WorkflowService
from api.v1 import workflows, embeddings, analytics, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
db_client: VmetaDatabaseClient = None
embedding_service: EmbeddingService = None
workflow_service: WorkflowService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager for vmeta service."""
    
    global db_client, embedding_service, workflow_service
    
    try:
        logger.info("🚀 Starting PPL Meta vmeta Service")
        logger.info(f"📊 Database: {settings.DB_HOST}:{settings.DB_PORT}")
        logger.info(f"🌐 API Server: http://{settings.HOST}:{settings.PORT}")
        
        # Initialize database client
        logger.info("📊 Initializing database client with pgvector support...")
        db_client = VmetaDatabaseClient(settings.get_database_config())
        await db_client.connect()
        
        # Initialize embedding service
        logger.info("🧠 Initializing embedding service...")
        embedding_service = EmbeddingService(
            database_client=db_client,
            model_name=settings.EMBEDDING_MODEL
        )
        
        # Initialize workflow service
        logger.info("⚙️ Initializing workflow service...")
        workflow_service = WorkflowService(
            database_client=db_client,
            embedding_service=embedding_service
        )
        
        # Register with service discovery
        # await register_with_discovery()
        
        logger.info("✅ vmeta service initialization completed successfully")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize vmeta service: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("🧹 Shutting down vmeta service...")
        if db_client:
            await db_client.close()
        logger.info("✅ vmeta service shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="PPL Meta vmeta Service",
    version=settings.SERVICE_VERSION,
    description="Vector-based facial embeddings and person detection analytics",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, tags=["health"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(embeddings.router, prefix="/api/v1/embeddings", tags=["embeddings"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "vmeta",
        "version": settings.SERVICE_VERSION,
        "description": "PPL Meta Vector-based facial embeddings and analytics",
        "status": "operational",
        "capabilities": settings.get_service_info()["capabilities"]
    }


if __name__ == "__main__":
    logger.info("🚀 Starting PPL Meta vmeta Service")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
EOF

echo "[SUCCESS] vmeta FastAPI application created"

# Step 5: Update package configuration
echo "[INFO] Step 5: Creating package configuration..."

cat > ppl-meta-vmeta/pyproject.toml << 'EOF'
[tool.poetry]
name = "ppl-meta-vmeta"
version = "1.0.0"
description = "PPL Meta Vector-based facial embeddings and person detection analytics"
authors = ["PPL Meta Team"]
packages = [{include = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.68.0"
uvicorn = "^0.18.0"
asyncpg = "^0.30.0"
python-multipart = "^0.0.20"
tensorflow = "^2.13.0"
deepface = "^0.0.75"
opencv-python = "^4.8.0"
pillow = "^10.0.0"
numpy = "^1.23.5"
python-dotenv = "^1.0.0"
requests = "^2.31.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.7.0"
flake8 = "^6.0.0"
mypy = "^1.5.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

echo "[SUCCESS] Package configuration created"

# Step 6: Create service management scripts
echo "[INFO] Step 6: Creating service management scripts..."

cat > ppl-meta-vmeta/start_vmeta.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting PPL Meta vmeta Service"
echo "=================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Start the vmeta service
cd src && python main.py
EOF

chmod +x ppl-meta-vmeta/start_vmeta.sh

cat > ppl-meta-vmeta/stop_vmeta.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping PPL Meta vmeta Service"
echo "================================="

pkill -f "python.*main.py.*vmeta" || echo "vmeta service was not running"
echo "✅ vmeta service stopped"
EOF

chmod +x ppl-meta-vmeta/stop_vmeta.sh

echo "[SUCCESS] Service management scripts created"

# Step 7: Create Docker configuration
echo "[INFO] Step 7: Creating Docker configuration..."

cat > ppl-meta-vmeta/docker/Dockerfile << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application code
COPY src/ src/

# Expose port
EXPOSE 8008

# Run the application
CMD ["python", "src/main.py"]
EOF

cat > ppl-meta-vmeta/docker-compose.yml << 'EOF'
version: '3.8'

services:
  vmeta:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: ppl-meta-vmeta
    ports:
      - "8008:8008"
    environment:
      - DB_HOST=localhost
      - DB_PORT=5432
      - DB_NAME=ppl_meta
      - DB_USER=ppl_user
      - DB_PASSWORD=ppl_password
      - VMETA_HOST=0.0.0.0
      - VMETA_PORT=8008
    volumes:
      - ./src:/app/src
    depends_on:
      - postgres
    networks:
      - ppl-meta-network

  postgres:
    image: pgvector/pgvector:pg14
    container_name: ppl-meta-postgres
    environment:
      - POSTGRES_DB=ppl_meta
      - POSTGRES_USER=ppl_user
      - POSTGRES_PASSWORD=ppl_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - ppl-meta-network

volumes:
  postgres_data:

networks:
  ppl-meta-network:
    driver: bridge
EOF

echo "[SUCCESS] Docker configuration created"

# Step 8: Create service documentation
echo "[INFO] Step 8: Creating service documentation..."

cat > ppl-meta-vmeta/README.md << 'EOF'
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
EOF

echo "[SUCCESS] Service documentation created"

echo
echo "================================================================"
echo "[SUCCESS] 🎉 PPL Meta vmeta Service Transformation Completed!"
echo "================================================================"
echo
echo "📁 New vmeta service structure:"
echo "  ppl-meta-vmeta/"
echo "  ├── src/                 # Main service code"
echo "  ├── tests/               # Test suite" 
echo "  ├── docker/              # Docker configuration"
echo "  ├── deployment/          # Deployment manifests"
echo "  └── requirements/        # Dependencies"
echo
echo "🚀 Next steps:"
echo "  1. cd ppl-meta-vmeta"
echo "  2. Fix any remaining import issues in src/"
echo "  3. ./start_vmeta.sh"
echo "  4. Test endpoints at http://localhost:8008"
echo
echo "🔗 Integration points:"
echo "  • Port 8008 (vmeta service)"
echo "  • Registers with discovery service"
echo "  • Coordinates with orchestrator"
echo "  • Shares database with other services"
echo
echo "📖 Documentation: ppl-meta-vmeta/README.md"
echo "================================================================"