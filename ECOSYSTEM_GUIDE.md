# PPL Meta Platform - Ecosystem Management Guide

This guide provides comprehensive walkthroughs for starting and stopping the complete PPL Meta Platform ecosystem using multiple deployment approaches: direct Python execution, minimal Docker setup, and full infrastructure Docker deployment.

## Overview

The PPL Meta Platform consists of multiple microservices and infrastructure components:

### Core Services
- **ppl-meta-gateway**: API Gateway service (FastAPI) - Port 8080
- **ppl-meta-node**: User Management service (FastAPI) - Port 8001
- **ppl-meta-media**: Media processing service (FastAPI) - Port 8000
- **ppl-postgres**: PostgreSQL database - Port 5433
- **ppl-redis**: Redis cache - Port 6379

### Optional Infrastructure (Full deployment)
- **nginx-gateway**: Reverse proxy and load balancer
- **consul**: Service discovery (when available)
- **prometheus**: Metrics collection (when available) 
- **grafana**: Monitoring dashboard (when available)
- **wireguard**: VPN server for mesh networking (when available)

## Deployment Options

1. **Python Direct** - Development mode with local Python execution
2. **Docker Minimal** - Core services only in containers
3. **Docker Full** - Complete infrastructure stack (when images available)

## Prerequisites

### Common Requirements
- Python 3.9+
- Git
- Environment variables configuration

### Docker Requirements (Options 2 & 3)
- Docker Desktop or Docker Engine
- Docker Compose v2.0+

### Python Direct Requirements (Option 1)
- PostgreSQL 12+ (or Docker PostgreSQL)
- Redis 6+ (or Docker Redis)
- Virtual environment tools (venv/conda)

---

## Option 1: Running with Python Interpreter (Development)

This approach runs each service directly with Python, ideal for development and debugging.

### 1. Initial Setup

#### Clone and Setup

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Ensure all submodules are available
git submodule update --init --recursive
```

#### Environment Configuration

Create a `.env` file in the root directory:

```bash
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@localhost:5433/ppl_db

# JWT and Security
SECRET_KEY=super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024
RESET_PASSWORD_SECRET=your-reset-secret-here
SERVICE_SECRET=your-service-secret-here

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Service URLs
PPL_MEDIA_SERVICE_URL=http://localhost:8000
PPL_GATEWAY_URL=http://localhost:8080
USER_SERVICE_URL=http://localhost:8001
MEDIA_SERVICE_URL=http://localhost:8000

# Email Configuration (Optional)
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=
MAIL_SERVER=
MAIL_PORT=587

# Environment
DEBUG=true
ENVIRONMENT=development
EOF

# Load environment variables
source .env
export $(cut -d= -f1 .env)
```

### 2. Infrastructure Setup

#### Start PostgreSQL

```bash
# Option A: Using Docker (Recommended)
docker run -d \
  --name ppl-postgres \
  -p 5433:5432 \
  -e POSTGRES_DB=ppl_db \
  -e POSTGRES_USER=nickadmin \
  -e POSTGRES_PASSWORD=Kodikos@23 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Option B: Using Homebrew (macOS)
brew install postgresql@15
brew services start postgresql@15
createdb ppl_db
```

#### Start Redis

```bash
# Option A: Using Homebrew (macOS)
brew services start redis

# Option B: Using Docker (cross-platform)
docker run -d \
  --name ppl-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 3. Service Setup and Startup

#### Setup Node Service (User Management)

```bash
cd ppl-meta-node

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations (if applicable)
# alembic upgrade head

# Start the service
python src/main.py
```

*Expected output*: `Uvicorn running on http://0.0.0.0:8001`

#### Setup Media Service (in a new terminal)

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the service
python src/main.py
```

*Expected output*: `Uvicorn running on http://0.0.0.0:8000`

#### Setup Gateway Service (in a new terminal)

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables and start
export SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024"
python src/main.py
```

*Expected output*: `Uvicorn running on http://0.0.0.0:8080`

### 4. Verify Services

#### Health Checks

```bash
# Gateway Health
curl http://localhost:8080/health

# Node Service Health
curl http://localhost:8001/health

# Media Service Health  
curl http://localhost:8000/health
```

*Expected responses*: JSON with `"status": "healthy"`

### 5. Stopping Services (Python Method)

#### Stop Services

1. **Stop each Python service**: Press `Ctrl+C` in each terminal running a service
2. **Deactivate virtual environments**: Run `deactivate` in each terminal
3. **Stop infrastructure**:

```bash
# Stop PostgreSQL
brew services stop postgresql@15
# OR stop Docker container
docker stop ppl-postgres && docker rm ppl-postgres

# Stop Redis
brew services stop redis
# OR stop Docker container
docker stop ppl-redis && docker rm ppl-redis
```

---

## Option 2: Docker Minimal Setup (Core Services Only)

This approach uses Docker for all services but includes only the essential components for basic functionality. This is ideal when you want containerization but some infrastructure images are unavailable.

### 1. Initial Setup

#### Verify Docker Installation

```bash
docker --version
docker-compose --version
```

#### Environment Configuration

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Set required environment variable
export SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024"

# Optional: Create .env file for persistence
echo "SECRET_KEY=super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" > .env
```

### 2. Build Docker Images

#### Build All Service Images

```bash
# Build Gateway Service
cd ppl-meta-gateway
docker build -t ppl-meta-gateway:latest .

# Build Node Service  
cd ../ppl-meta-node
docker build -t ppl-meta-node:latest .

# Build Media Service
cd ../ppl-meta-media
docker build -t ppl-meta-media:latest .

# Return to root
cd ..
```

### 3. Start Minimal Ecosystem

#### Start Core Services Only

```bash
# Start the minimal ecosystem (core services only)
SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" \
docker-compose -f docker-compose.minimal.yml up -d
```

*Expected output*:

```
✔ Container ppl-postgres      Started
✔ Container ppl-redis         Started  
✔ Container ppl-meta-node     Started
✔ Container ppl-meta-media    Started
✔ Container ppl-meta-gateway  Started
```

#### Monitor Startup

```bash
# Watch all services start
docker-compose -f docker-compose.minimal.yml logs -f

# Check specific service logs
docker logs ppl-meta-gateway
docker logs ppl-meta-node
docker logs ppl-meta-media
```

### 4. Verify Services

#### Health Checks

```bash
# Gateway Health (main entry point)
curl http://localhost:8080/health

# Direct service health checks
curl http://localhost:8001/health  # Node service
curl http://localhost:8000/health  # Media service
```

#### Service Status

```bash
# Check all container status
docker-compose -f docker-compose.minimal.yml ps
```

### 5. Stopping Services (Docker Minimal)

#### Stop All Services

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Stop and remove all containers
docker-compose -f docker-compose.minimal.yml down

# Stop with volume cleanup (removes database data)
docker-compose -f docker-compose.minimal.yml down -v
```

---

## Option 3: Docker Full Infrastructure (When Available)

This approach uses the complete infrastructure stack including monitoring, service discovery, and VPN capabilities. Note: Some images may not be available and require building or alternative sources.

### 1. Full Infrastructure Setup

#### Start Complete Ecosystem

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Attempt to start the full ecosystem
SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" \
MAIL_USERNAME="" \
MAIL_PASSWORD="" \
MAIL_FROM="" \
MAIL_SERVER="" \
docker-compose -f docker-compose.ecosystem.yml up -d
```

**Note**: This may fail if infrastructure images (consul, prometheus, grafana, wireguard) are unavailable. In that case, use Option 2 (Minimal Setup) instead.

### 2. Verify Full Infrastructure

If the full infrastructure starts successfully:

```bash
# Core Services
curl http://localhost:8080/health  # Gateway
curl http://localhost:8001/health  # Node service
curl http://localhost:8000/health  # Media service

# Infrastructure Services (if running)
curl http://localhost:8500/v1/status/leader  # Consul
curl http://localhost:9090/-/healthy          # Prometheus
curl http://localhost:3000/api/health         # Grafana
```

### 3. Stopping Full Infrastructure

```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Stop the complete ecosystem
docker-compose -f docker-compose.ecosystem.yml down

# Stop with volume cleanup
docker-compose -f docker-compose.ecosystem.yml down -v
```
DATABASE_URL=postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_db
POSTGRES_USER=ppl_user
POSTGRES_PASSWORD=ppl_password
POSTGRES_DB=ppl_meta_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Service Configuration
ENVIRONMENT=development
DEBUG=true

# Gateway Configuration
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080

# Node Service Configuration
NODE_HOST=0.0.0.0
NODE_PORT=8000

# Media Service Configuration
MEDIA_HOST=0.0.0.0
MEDIA_PORT=8001
EOF
```

### 2. Infrastructure Setup

#### Start PostgreSQL
```bash
# Option A: Using Homebrew (macOS)
brew services start postgresql@14

# Option B: Using Docker (cross-platform)
docker run -d \
  --name ppl-postgres \
  -e POSTGRES_USER=ppl_user \
  -e POSTGRES_PASSWORD=ppl_password \
  -e POSTGRES_DB=ppl_meta_db \
  -p 5432:5432 \
  postgres:14-alpine

# Create database if needed
psql -h localhost -U ppl_user -d postgres -c "CREATE DATABASE ppl_meta_db;"
```

#### Start Redis
```bash
# Option A: Using Homebrew (macOS)
brew services start redis

# Option B: Using Docker (cross-platform)
docker run -d \
  --name ppl-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 3. Service Setup and Startup

#### Setup Node Service (User Management)
```bash
cd ppl-meta-node

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations (if applicable)
# alembic upgrade head

# Start the service
python src/main.py
```
*Expected output*: `Uvicorn running on http://0.0.0.0:8000`

#### Setup Media Service (in a new terminal)
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the service
python src/main.py
```
*Expected output*: `Uvicorn running on http://0.0.0.0:8001`

#### Setup Gateway Service (in a new terminal)
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables and start
export SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024"
python src/main.py
```
*Expected output*: `Uvicorn running on http://0.0.0.0:8080`

### 4. Verify Services

#### Health Checks
```bash
# Gateway Health
curl http://localhost:8080/health

# Node Service Health
curl http://localhost:8000/health

# Media Service Health  
curl http://localhost:8001/health
```

*Expected responses*: JSON with `"status": "healthy"`

### 5. Stopping Services (Python Method)

#### Stop Services
1. **Stop each Python service**: Press `Ctrl+C` in each terminal running a service
2. **Deactivate virtual environments**: Run `deactivate` in each terminal
3. **Stop infrastructure**:
```bash
# Stop PostgreSQL
brew services stop postgresql@14
# OR stop Docker container
docker stop ppl-postgres && docker rm ppl-postgres

# Stop Redis
brew services stop redis
# OR stop Docker container
docker stop ppl-redis && docker rm ppl-redis
```

---

## Option 2: Running with Docker (Production-Ready)

This approach uses Docker containers for all services, ideal for production deployments and consistent environments.

### 1. Initial Setup

#### Verify Docker Installation
```bash
docker --version
docker-compose --version
```

#### Environment Configuration
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Set required environment variable
export SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024"

# Optional: Create .env file for persistence
echo "SECRET_KEY=super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" > .env
```

### 2. Build Docker Images

#### Build All Service Images
```bash
# Build Gateway Service
cd ppl-meta-gateway
docker build -t ppl-meta-gateway:latest .

# Build Node Service  
cd ../ppl-meta-node
docker build -t ppl-meta-node:latest .

# Build Media Service
cd ../ppl-meta-media
docker build -t ppl-meta-media:latest .

# Return to root
cd ..
```

### 3. Start Complete Ecosystem

#### Start All Services
```bash
# Start the complete ecosystem
SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" \
docker-compose -f docker-compose.ecosystem.yml up -d

# Alternative: Using environment file
docker-compose -f docker-compose.ecosystem.yml up -d
```

*Expected output*:
```
✔ Container ppl-postgres      Started
✔ Container ppl-redis         Started  
✔ Container ppl-meta-node     Started
✔ Container ppl-meta-media    Started
✔ Container ppl-meta-gateway  Started
```

#### Monitor Startup
```bash
# Watch all services start
docker-compose -f docker-compose.ecosystem.yml logs -f

# Check specific service logs
docker logs ppl-meta-gateway
docker logs ppl-meta-node
docker logs ppl-meta-media
```

### 4. Verify Services

#### Health Checks
```bash
# Gateway Health (main entry point)
curl http://localhost:8080/health

# Direct service health checks
curl http://localhost:8000/health  # Node service
curl http://localhost:8001/health  # Media service
```

#### Service Status
```bash
# Check all container status
docker-compose -f docker-compose.ecosystem.yml ps

# Expected output:
# NAME              IMAGE                 STATUS         PORTS
# ppl-meta-gateway  ppl-meta-gateway     Up            0.0.0.0:8080->8080/tcp
# ppl-meta-node     ppl-meta-node        Up            0.0.0.0:8000->8000/tcp
# ppl-meta-media    ppl-meta-media       Up            0.0.0.0:8001->8001/tcp
# ppl-postgres      postgres:14-alpine   Up            0.0.0.0:5432->5432/tcp
# ppl-redis         redis:7-alpine       Up            0.0.0.0:6379->6379/tcp
```

### 5. Stopping Services (Docker Method)

#### Stop All Services
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Stop and remove all containers
docker-compose -f docker-compose.ecosystem.yml down

# Stop with volume cleanup (removes database data)
docker-compose -f docker-compose.ecosystem.yml down -v

# Stop and remove everything including images
docker-compose -f docker-compose.ecosystem.yml down --rmi all -v
```

*Expected output*:
```
✔ Container ppl-meta-gateway  Removed
✔ Container ppl-meta-node     Removed
✔ Container ppl-meta-media    Removed
✔ Container ppl-redis         Removed
✔ Container ppl-postgres      Removed
✔ Network ppl-meta-code_ppl-network   Removed
✔ Network ppl-meta-code_ppl-internal  Removed
```

---

## Service Endpoints

### Gateway Service (Port 8080)

- **Health**: `GET http://localhost:8080/health`
- **API Documentation**: `GET http://localhost:8080/docs`
- **OpenAPI Spec**: `GET http://localhost:8080/openapi.json`

### Node Service (Port 8001)

- **Health**: `GET http://localhost:8001/health`
- **Users**: `GET http://localhost:8001/api/v1/users`
- **API Documentation**: `GET http://localhost:8001/docs`

### Media Service (Port 8000)

- **Health**: `GET http://localhost:8000/health`
- **Media**: `GET http://localhost:8000/api/v1/media`
- **API Documentation**: `GET http://localhost:8000/docs`

---

## VS Code Tasks Integration

The workspace includes predefined VS Code tasks for easy ecosystem management:

### Available Tasks

1. **Setup Development Environment**: `Ctrl+Shift+P` → "Tasks: Run Task" → "Setup Development Environment"
2. **Start Infrastructure**: Starts Docker infrastructure services
3. **Stop Infrastructure**: Stops Docker infrastructure services
4. **Start Gateway Service**: Runs gateway with Python
5. **Start User Management Service**: Runs node service with Python
6. **Start Media Service**: Runs media service with Python

### Using VS Code Tasks

```bash
# Using Command Palette
Ctrl+Shift+P (Cmd+Shift+P on Mac)
Type: "Tasks: Run Task"
Select the desired task
```

---

## Troubleshooting

### Common Issues

#### Port Conflicts

```bash
# Check what's using ports
lsof -i :8080  # Gateway
lsof -i :8001  # Node
lsof -i :8000  # Media
lsof -i :5433  # PostgreSQL
lsof -i :6379  # Redis

# Kill processes if needed
kill -9 <PID>
```

#### Environment Variables Not Loading

```bash
# Verify environment variables
echo $SECRET_KEY

# For Docker, check container environment
docker exec ppl-meta-gateway env | grep SECRET_KEY
```

#### Docker Image Issues

```bash
# Check if images exist
docker images | grep ppl-meta

# Rebuild images if needed
cd ppl-meta-gateway && docker build -t ppl-meta-gateway:latest .
cd ppl-meta-node && docker build -t ppl-meta-node:latest .
cd ppl-meta-media && docker build -t ppl-meta-media:latest .
```

#### Database Connection Issues

```bash
# Test database connectivity
docker exec ppl-postgres psql -U nickadmin -d ppl_db -c "SELECT 1;"

# Check database logs
docker logs ppl-postgres
```

#### Service Health Check Failures

```bash
# Check service logs
docker logs ppl-meta-gateway --tail 50

# Check service status
docker ps | grep ppl-meta

# Check service configuration issues
docker exec ppl-meta-gateway env
```

#### Missing Infrastructure Services

If the full ecosystem fails due to missing images (consul, prometheus, etc.):

```bash
# Use minimal setup instead
docker-compose -f docker-compose.minimal.yml up -d

# Or start services individually
docker run -d --name ppl-postgres -p 5433:5432 -e POSTGRES_DB=ppl_db postgres:15-alpine
docker run -d --name ppl-redis -p 6379:6379 redis:7-alpine
```

### Log Locations

#### Python Method

- Service logs: Terminal output where service was started
- Application logs: `./logs/` directory in each service folder

#### Docker Method

- Container logs: `docker logs <container-name>`
- Persistent logs: Volume mounts (if configured)

---

## Quick Reference Commands

### Docker Minimal Commands

```bash
# Start minimal ecosystem
SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" docker-compose -f docker-compose.minimal.yml up -d

# Stop minimal ecosystem
docker-compose -f docker-compose.minimal.yml down

# View logs
docker-compose -f docker-compose.minimal.yml logs -f

# Check status
docker-compose -f docker-compose.minimal.yml ps
```

### Docker Full Commands (when available)

```bash
# Start full ecosystem
SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" docker-compose -f docker-compose.ecosystem.yml up -d

# Stop full ecosystem
docker-compose -f docker-compose.ecosystem.yml down

# View logs
docker-compose -f docker-compose.ecosystem.yml logs -f

# Check status
docker-compose -f docker-compose.ecosystem.yml ps
```

### Development Commands

```bash
# Health checks
curl http://localhost:8080/health
curl http://localhost:8001/health  
curl http://localhost:8000/health

# API documentation
open http://localhost:8080/docs
open http://localhost:8001/docs
open http://localhost:8000/docs
```

### Individual Service Management

```bash
# Start individual services with Docker
docker run -d --name ppl-postgres -p 5433:5432 -e POSTGRES_DB=ppl_db postgres:15-alpine
docker run -d --name ppl-redis -p 6379:6379 redis:7-alpine
docker run -d --name ppl-meta-gateway -p 8080:8080 -e SECRET_KEY="your-key" ppl-meta-gateway:latest

# Stop individual services
docker stop ppl-postgres ppl-redis ppl-meta-gateway
docker rm ppl-postgres ppl-redis ppl-meta-gateway
```

---

## Environment Variables Reference

| Variable | Description | Default | Required | Used By |
|----------|-------------|---------|----------|---------|
| `SECRET_KEY` | JWT signing key for gateway | N/A | Yes | All Services |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://nickadmin:Kodikos%4023@localhost:5433/ppl_db` | Yes | Node, Media |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | Yes | Gateway, Media |
| `USER_SERVICE_URL` | Node service URL | `http://localhost:8001` | No | Gateway |
| `MEDIA_SERVICE_URL` | Media service URL | `http://localhost:8000` | No | Gateway, Node |
| `PPL_GATEWAY_URL` | Gateway service URL | `http://localhost:8080` | No | Node, Media |
| `DEBUG` | Enable debug mode | `false` | No | All Services |
| `ENVIRONMENT` | Deployment environment | `development` | No | All Services |
| `HOST` | Service bind address | `0.0.0.0` | No | All Services |
| `PORT` | Service port | Service-specific | No | All Services |
| `MAIL_USERNAME` | SMTP username | `` | No | Node |
| `MAIL_PASSWORD` | SMTP password | `` | No | Node |
| `MAIL_FROM` | Email sender address | `` | No | Node |
| `MAIL_SERVER` | SMTP server | `` | No | Node |
| `MAIL_PORT` | SMTP port | `587` | No | Node |

---

## Recommended Deployment Workflow

### For Development

1. **Start with Python Direct (Option 1)** for active development
2. **Use individual terminals** for each service to see real-time logs
3. **Use Docker for infrastructure** (PostgreSQL, Redis) to avoid local setup

### For Testing

1. **Use Docker Minimal (Option 2)** for integration testing
2. **Test all endpoints** using the health checks and API docs
3. **Verify service-to-service communication**

### For Production

1. **Use Docker Full (Option 3)** when all images are available
2. **Include monitoring and metrics** with Prometheus/Grafana
3. **Set up proper environment variables** and secrets management
4. **Configure reverse proxy** with nginx for load balancing

---

This guide provides everything needed to start and stop the PPL Meta Platform ecosystem using multiple deployment approaches. Choose the method that best fits your use case:

- **Development**: Python Direct (Option 1)
- **Testing/Staging**: Docker Minimal (Option 2)  
- **Production**: Docker Full (Option 3) when available
