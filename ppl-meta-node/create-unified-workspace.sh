#!/bin/bash
# PPL Meta Platform - Create Unified Workspace
# This script creates a proper monorepo structure for the entire infrastructure

set -e

echo "🏗️  Creating PPL Meta Platform Unified Workspace"
echo "================================================"

# Check if we're in the right location
CURRENT_DIR=$(basename "$PWD")
if [ "$CURRENT_DIR" != "ppl-meta-node" ]; then
    echo "❌ Please run this script from the ppl-meta-node directory"
    exit 1
fi

# Move up to create the unified workspace
cd ..

# Create the unified workspace structure
echo "📁 Creating unified workspace structure..."

# Create the main workspace directory if it doesn't exist
if [ ! -d "ppl-meta-code" ]; then
    mkdir ppl-meta-code
fi

cd ppl-meta-code

# Create the proper monorepo structure
echo "🏗️  Setting up monorepo structure..."

# Services directory
mkdir -p services/{gateway,user-management,media,orchestrator,vision}

# Infrastructure directory
mkdir -p infrastructure/{nginx,database,monitoring,vpn,scripts}

# Shared libraries directory
mkdir -p shared/{config,auth,logging,utils}

# Documentation directory
mkdir -p docs/{api,deployment,architecture,user-guides}

# Tools and scripts directory
mkdir -p tools/{dev,deployment,monitoring}

# Environment configurations
mkdir -p environments/{development,staging,production}

echo "📋 Creating workspace configuration files..."

# Root package.json for the workspace (if using Node.js tools)
cat > package.json << 'EOF'
{
  "name": "ppl-meta-platform",
  "version": "1.0.0",
  "description": "PPL Meta Platform - Complete Infrastructure Workspace",
  "private": true,
  "workspaces": [
    "services/*",
    "shared/*",
    "tools/*"
  ],
  "scripts": {
    "dev": "docker-compose -f infrastructure/docker-compose.dev.yml up -d",
    "prod": "docker-compose -f infrastructure/docker-compose.prod.yml up -d",
    "test": "npm run test --workspaces",
    "build": "npm run build --workspaces",
    "setup": "./tools/dev/setup-workspace.sh"
  },
  "devDependencies": {
    "concurrently": "^8.0.0",
    "nodemon": "^3.0.0"
  }
}
EOF

# Root requirements.txt for Python dependencies
cat > requirements.txt << 'EOF'
# PPL Meta Platform - Root Python Dependencies
# Shared dependencies across all services

# FastAPI and core web framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Database
sqlalchemy>=2.0.23
alembic>=1.12.0

# HTTP client for inter-service communication
httpx>=0.25.0
requests>=2.31.0

# Development and testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0

# Environment management
python-dotenv>=1.0.0

# Monitoring and logging
structlog>=23.0.0
prometheus-client>=0.17.0
EOF

# Root Docker Compose for the entire platform
cat > docker-compose.yml << 'EOF'
# PPL Meta Platform - Main Docker Compose
# This orchestrates the entire platform infrastructure

version: '3.8'

services:
  # Load balancer and reverse proxy
  nginx-gateway:
    build: ./infrastructure/nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/nginx/conf:/etc/nginx/conf.d
      - ./infrastructure/nginx/ssl:/etc/ssl
    depends_on:
      - api-gateway
      - user-management
      - media-service
    networks:
      - ppl-public
      - ppl-internal

  # API Gateway service
  api-gateway:
    build: ./services/gateway
    ports:
      - "8080:8080"
    environment:
      - SERVICE_NAME=api-gateway
      - CONSUL_HOST=consul
    depends_on:
      - consul
      - redis
    networks:
      - ppl-internal
    volumes:
      - ./shared:/app/shared

  # User Management service
  user-management:
    build: ./services/user-management
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/user_db
    depends_on:
      - postgres
    networks:
      - ppl-internal
    volumes:
      - ./shared:/app/shared

  # Media service
  media-service:
    build: ./services/media
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/media_db
    depends_on:
      - postgres
    networks:
      - ppl-internal
    volumes:
      - ./shared:/app/shared
      - media-storage:/app/media

  # Orchestrator service
  orchestrator:
    build: ./services/orchestrator
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/orchestrator_db
    depends_on:
      - postgres
      - user-management
      - media-service
    networks:
      - ppl-internal
    volumes:
      - ./shared:/app/shared

  # Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ppl_platform
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infrastructure/database/init:/docker-entrypoint-initdb.d
    networks:
      - ppl-internal

  # Redis for caching and sessions
  redis:
    image: redis:7-alpine
    networks:
      - ppl-internal
    volumes:
      - redis_data:/data

  # Service discovery
  consul:
    image: consul:1.16
    ports:
      - "8500:8500"
    networks:
      - ppl-internal
    volumes:
      - consul_data:/consul/data

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./infrastructure/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - ppl-internal

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - ppl-internal

volumes:
  postgres_data:
  redis_data:
  consul_data:
  media-storage:

networks:
  ppl-public:
    driver: bridge
  ppl-internal:
    driver: bridge
    internal: false
EOF

# Workspace README
cat > README.md << 'EOF'
# PPL Meta Platform

Complete infrastructure workspace for the PPL Meta Platform - a hybrid microservices architecture with cloud-to-edge capabilities.

## 🏗️ Workspace Structure

```
ppl-meta-code/
├── services/                    # All microservices
│   ├── gateway/                # API Gateway service
│   ├── user-management/        # User authentication & management
│   ├── media/                  # Media processing & storage
│   ├── orchestrator/           # Business logic coordination
│   └── vision/                 # Machine vision services
├── infrastructure/             # Infrastructure components
│   ├── nginx/                  # Reverse proxy configuration
│   ├── database/               # Database schemas and migrations
│   ├── monitoring/             # Prometheus, Grafana configs
│   └── vpn/                    # WireGuard VPN configuration
├── shared/                     # Shared libraries and utilities
│   ├── config/                 # Common configuration
│   ├── auth/                   # Authentication utilities
│   ├── logging/                # Logging utilities
│   └── utils/                  # Common utilities
├── docs/                       # Documentation
├── tools/                      # Development and deployment tools
├── environments/               # Environment-specific configurations
└── docker-compose.yml         # Main orchestration file
```

## 🚀 Quick Start

```bash
# Setup the workspace
npm run setup

# Start development environment
npm run dev

# Or manually with Docker
docker-compose up -d
```

## 📚 Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [API Documentation](docs/api/README.md)
- [Deployment Guide](docs/deployment/README.md)
- [Development Guide](docs/development/README.md)

## 🔧 Development

Each service is independently developable but shares common utilities and configurations through the `shared/` directory.

## 🌐 Service URLs

- Main Gateway: https://localhost
- API Gateway: http://localhost:8080
- User Management: http://localhost:8001
- Media Service: http://localhost:8000
- Orchestrator: http://localhost:8002
- Monitoring: http://localhost:3000 (Grafana)
- Service Discovery: http://localhost:8500 (Consul)
EOF

# Development environment file
cat > .env.development << 'EOF'
# PPL Meta Platform - Development Environment

# Application
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Database
POSTGRES_DB=ppl_platform
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
DATABASE_URL=postgresql://admin:password@postgres:5432/ppl_platform

# Services
SERVICE_DISCOVERY_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500

# Security (Development only - change for production!)
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET=dev-jwt-secret-change-in-production

# External Services
REDIS_URL=redis://redis:6379
PROMETHEUS_URL=http://prometheus:9090

# Email (for development)
MAIL_SERVER=localhost
MAIL_PORT=1025
MAIL_USERNAME=
MAIL_PASSWORD=
EOF

echo "✅ Unified workspace structure created!"
echo ""
echo "📁 Next steps:"
echo "1. Move your existing services to the services/ directory"
echo "2. Move shared code to the shared/ directory"
echo "3. Update import paths in your services"
echo "4. Run: npm run setup (or docker-compose up -d)"
echo ""
echo "🎯 Benefits of this structure:"
echo "   - Single workspace for entire platform"
echo "   - Shared code and configurations"
echo "   - Consistent development environment"
echo "   - Easier CI/CD and deployment"
echo "   - Better dependency management"
echo ""
