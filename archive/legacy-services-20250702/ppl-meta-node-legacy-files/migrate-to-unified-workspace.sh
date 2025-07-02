#!/bin/bash
# PPL Meta Platform - Migrate to Unified Workspace
# This script migrates existing services to the unified workspace structure

set -e

echo "🔄 Migrating to PPL Meta Platform Unified Workspace"
echo "==================================================="

# Check current location
CURRENT_DIR=$(basename "$PWD")
if [ "$CURRENT_DIR" != "ppl-meta-node" ]; then
    echo "❌ Please run this script from the ppl-meta-node directory"
    exit 1
fi

# First create the unified workspace
echo "🏗️  Creating unified workspace structure..."
./create-unified-workspace.sh

# Move to the parent directory where we now have the unified workspace
cd ../ppl-meta-code

echo "📦 Migrating existing services..."

# Migrate User Management service (current ppl-meta-node)
if [ -d "../ppl-meta-node" ]; then
    echo "   Migrating User Management service..."
    
    # Copy the user management service
    cp -r ../ppl-meta-node/src services/user-management/
    cp ../ppl-meta-node/Dockerfile services/user-management/
    cp ../ppl-meta-node/requirements.txt services/user-management/
    
    # Create service-specific files
    cat > services/user-management/README.md << 'EOF'
# User Management Service

Handles user authentication, authorization, and user operations for the PPL Meta Platform.

## Features

- User registration and authentication
- JWT token management
- Role-based access control
- Password reset functionality
- Email verification
- User action logging

## API Endpoints

- `/api/v1/users/` - User management
- `/api/v1/auth/` - Authentication
- `/api/v1/health` - Health check

## Development

```bash
cd services/user-management
uvicorn src.main:app --reload --port 8001
```
EOF

    echo "   ✅ User Management service migrated"
fi

# Migrate Gateway service (from docs folder)
if [ -d "../ppl-meta-node/docs/ppl-meta-geteway" ]; then
    echo "   Migrating API Gateway service..."
    
    # Copy the gateway service
    cp -r "../ppl-meta-node/docs/ppl-meta-geteway/"* services/gateway/
    
    cat > services/gateway/README.md << 'EOF'
# API Gateway Service

Central API gateway for routing, authentication, and service discovery in the PPL Meta Platform.

## Features

- Request routing to microservices
- Authentication and authorization
- Rate limiting
- Service discovery integration
- Monitoring and metrics

## Development

```bash
cd services/gateway
uvicorn src.main:app --reload --port 8080
```
EOF

    echo "   ✅ API Gateway service migrated"
fi

# Create placeholder services for Media and Orchestrator
echo "📁 Creating placeholder services..."

# Media Service
mkdir -p services/media/src
cat > services/media/README.md << 'EOF'
# Media Service

Handles file upload, processing, and storage for the PPL Meta Platform.

## Features

- File upload and storage
- Image processing and resizing
- Video processing
- Media streaming
- Storage management

## Development

```bash
cd services/media
uvicorn src.main:app --reload --port 8000
```
EOF

cat > services/media/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Orchestrator Service
mkdir -p services/orchestrator/src
cat > services/orchestrator/README.md << 'EOF'
# Orchestrator Service

Coordinates business logic and workflows across the PPL Meta Platform.

## Features

- Workflow orchestration
- Business rule engine
- Inter-service coordination
- Task scheduling
- Event processing

## Development

```bash
cd services/orchestrator
uvicorn src.main:app --reload --port 8002
```
EOF

cat > services/orchestrator/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
EOF

# Vision Service
mkdir -p services/vision/src
cat > services/vision/README.md << 'EOF'
# Vision Service

Machine vision and AI processing service for the PPL Meta Platform.

## Features

- Image recognition
- Object detection
- Video analysis
- AI model inference
- Edge device integration

## Development

```bash
cd services/vision
uvicorn src.main:app --reload --port 8003
```
EOF

# Migrate infrastructure components
echo "🏗️  Migrating infrastructure components..."

# Migrate Nginx configuration
if [ -d "../ppl-meta-node/nginx" ]; then
    cp -r ../ppl-meta-node/nginx/* infrastructure/nginx/
    echo "   ✅ Nginx configuration migrated"
fi

# Migrate monitoring configuration
if [ -d "../ppl-meta-node/monitoring" ]; then
    cp -r ../ppl-meta-node/monitoring/* infrastructure/monitoring/
    echo "   ✅ Monitoring configuration migrated"
fi

# Migrate database configuration
if [ -d "../ppl-meta-node/database" ]; then
    cp -r ../ppl-meta-node/database/* infrastructure/database/
    echo "   ✅ Database configuration migrated"
fi

# Migrate VPN configuration
if [ -d "../ppl-meta-node/wireguard" ]; then
    cp -r ../ppl-meta-node/wireguard/* infrastructure/vpn/
    echo "   ✅ VPN configuration migrated"
fi

# Create shared libraries
echo "📚 Setting up shared libraries..."

# Shared configuration
mkdir -p shared/config
cat > shared/config/__init__.py << 'EOF'
"""Shared configuration utilities for PPL Meta Platform services."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class BaseServiceConfig(BaseSettings):
    """Base configuration for all PPL Meta Platform services."""
    
    # Service identity
    service_name: str
    service_version: str = "1.0.0"
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int
    debug: bool = False
    
    # Database
    database_url: str
    
    # Service discovery
    consul_host: str = "consul"
    consul_port: int = 8500
    service_discovery_enabled: bool = True
    
    # Security
    secret_key: str
    jwt_secret: str = ""
    
    # External services
    redis_url: str = "redis://redis:6379"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_service_config(service_name: str, default_port: int) -> BaseServiceConfig:
    """Get configuration for a specific service."""
    config = BaseServiceConfig(
        service_name=service_name,
        port=default_port
    )
    return config
EOF

# Shared authentication
mkdir -p shared/auth
cat > shared/auth/__init__.py << 'EOF'
"""Shared authentication utilities for PPL Meta Platform services."""

from .jwt_handler import JWTHandler
from .service_auth import ServiceAuthenticator

__all__ = ["JWTHandler", "ServiceAuthenticator"]
EOF

cat > shared/auth/jwt_handler.py << 'EOF'
"""JWT token handling utilities."""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class JWTHandler:
    """Handles JWT token creation and validation."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, payload: Dict[str, Any], expires_in: Optional[timedelta] = None) -> str:
        """Create a JWT token."""
        if expires_in:
            payload["exp"] = datetime.utcnow() + expires_in
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token."""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
    
    def is_token_valid(self, token: str) -> bool:
        """Check if a token is valid."""
        try:
            self.decode_token(token)
            return True
        except jwt.InvalidTokenError:
            return False
EOF

# Create development tools
echo "🛠️  Setting up development tools..."

mkdir -p tools/dev
cat > tools/dev/setup-workspace.sh << 'EOF'
#!/bin/bash
# Development workspace setup script

echo "🔧 Setting up PPL Meta Platform development workspace..."

# Create Python virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Python virtual environment created"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.development .env
    echo "✅ Environment file created"
fi

# Create Docker network
docker network create ppl-network 2>/dev/null || echo "Network already exists"

echo "✅ Workspace setup complete!"
echo "Run 'docker-compose up -d' to start the platform"
EOF

chmod +x tools/dev/setup-workspace.sh

# Create documentation structure
echo "📖 Setting up documentation..."

mkdir -p docs/{architecture,api,deployment,development}

cat > docs/README.md << 'EOF'
# PPL Meta Platform Documentation

## Architecture
- [Overview](architecture/overview.md)
- [Service Architecture](architecture/services.md)
- [Infrastructure](architecture/infrastructure.md)

## API Documentation
- [API Overview](api/README.md)
- [Authentication](api/authentication.md)
- [Service APIs](api/services.md)

## Deployment
- [Deployment Guide](deployment/README.md)
- [Environment Setup](deployment/environments.md)
- [Docker Configuration](deployment/docker.md)

## Development
- [Development Guide](development/README.md)
- [Service Development](development/services.md)
- [Testing](development/testing.md)
EOF

echo ""
echo "🎉 Migration Complete!"
echo ""
echo "📊 Unified Workspace Structure:"
echo "ppl-meta-code/"
echo "├── services/              # All microservices"
echo "│   ├── gateway/           # API Gateway"
echo "│   ├── user-management/   # User Management (migrated)"
echo "│   ├── media/             # Media Service"
echo "│   ├── orchestrator/      # Orchestrator"
echo "│   └── vision/            # Vision Service"
echo "├── infrastructure/        # Infrastructure components"
echo "├── shared/               # Shared libraries"
echo "├── docs/                 # Documentation"
echo "├── tools/                # Development tools"
echo "└── docker-compose.yml    # Main orchestration"
echo ""
echo "🚀 Next Steps:"
echo "1. cd ../ppl-meta-code"
echo "2. npm run setup (or ./tools/dev/setup-workspace.sh)"
echo "3. docker-compose up -d"
echo ""
echo "🎯 Benefits of unified workspace:"
echo "   ✅ Single repository for entire platform"
echo "   ✅ Shared code and configurations"
echo "   ✅ Consistent development environment"
echo "   ✅ Simplified dependency management"
echo "   ✅ Better CI/CD integration"
echo ""
