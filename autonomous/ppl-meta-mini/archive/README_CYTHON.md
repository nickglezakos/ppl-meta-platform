# PPL Meta Mini - Cython Docker Build

This directory contains the configuration and scripts to build PPL Meta Mini as a Docker image with Cython-compiled Python code for Linux.

## 🎯 Overview

PPL Meta Mini is an autonomous microservice for face analytics. This Cython build creates a Docker image containing compiled Python code for better performance and security.

## 📁 Files

- `Dockerfile.cython` - Multi-stage Docker build with Cython compilation
- `setup_cython.py` - Cython setup script for compilation
- `requirements.cython.txt` - Python dependencies including Cython
- `docker-compose.cython.yml` - Docker Compose configuration
- `build_cython_docker.sh` - Build script
- `test_cython_build.py` - Test script for validation
- `.dockerignore.cython` - Docker ignore file

## 🚀 Quick Start

### Build the Docker Image

```bash
# Make the build script executable (if not already)
chmod +x build_cython_docker.sh

# Build the image
./build_cython_docker.sh
```

### Run with Docker

```bash
# Run directly
docker run -p 8004:8004 ppl-meta-mini:cython

# Or use Docker Compose
docker-compose -f docker-compose.cython.yml up -d
```

### Test the Service

```bash
# Health check
curl http://localhost:8004/health

# API documentation
open http://localhost:8004/docs
```

## 🔧 Manual Build Steps

### 1. Local Cython Compilation (Optional)

```bash
# Install dependencies
pip install -r requirements.cython.txt

# Compile with Cython
python setup_cython.py build_ext --inplace

# Check compiled files
find . -name "*.so"
```

### 2. Docker Build

```bash
# Build the image
docker build -f Dockerfile.cython -t ppl-meta-mini:cython .

# Check image size
docker images ppl-meta-mini:cython
```

### 3. Run and Test

```bash
# Start container
docker run -d --name ppl-meta-mini -p 8004:8004 ppl-meta-mini:cython

# Test health endpoint
curl http://localhost:8004/health

# View logs
docker logs ppl-meta-mini

# Stop container
docker stop ppl-meta-mini && docker rm ppl-meta-mini
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_cython_build.py
```

This will:
1. Test local Cython compilation
2. Verify compiled .so files
3. Build Docker image
4. Test container startup and health

## 📊 Performance Benefits

The Cython compilation provides:
- **Faster execution** - Compiled C extensions
- **Reduced memory footprint** - Optimized bytecode
- **Better security** - Source code protection
- **Single binary** - Easier deployment

## 🔍 Troubleshooting

### Build Issues

```bash
# Check Docker build logs
docker build -f Dockerfile.cython -t ppl-meta-mini:cython . --no-cache

# Check system dependencies
docker run --rm python:3.11-slim apt list --installed | grep -E "(gcc|build-essential)"
```

### Runtime Issues

```bash
# Check container logs
docker logs ppl-meta-mini

# Test inside container
docker exec -it ppl-meta-mini bash

# Check compiled modules
python -c "import src.main; print('Import successful')"
```

### Common Problems

1. **Cython compilation fails**
   - Ensure build-essential is installed
   - Check Python development headers
   - Verify Cython version compatibility

2. **Import errors in container**
   - Check PYTHONPATH environment variable
   - Verify all .so files are copied
   - Check file permissions

3. **Service not starting**
   - Check port availability (8004)
   - Verify all dependencies are installed
   - Check uvicorn configuration

## 📋 Service Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /docs` - API documentation
- `POST /api/v1/upload-and-analyze` - Face analytics

## 🌐 Integration

The Cython-compiled service is compatible with:
- PPL Meta Platform microservices
- Nginx reverse proxy
- Docker Swarm / Kubernetes
- CI/CD pipelines

## 📈 Monitoring

Monitor the service with:
- Health endpoint: `/health`
- Docker health checks
- Container metrics
- Application logs

---

For more information about PPL Meta Mini, see the main README.md file.
