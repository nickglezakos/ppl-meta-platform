#!/bin/bash
# PPL Meta Platform - Development Environment Setup
# Quick setup script for development

set -e

echo "🔧 PPL Meta Platform - Development Setup"
echo "========================================"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Setup environment
if [ ! -f .env ]; then
    echo "📝 Setting up environment configuration..."
    cp .env.template .env
    
    # Generate secure keys
    SECRET_KEY=$(openssl rand -hex 32)
    RESET_SECRET=$(openssl rand -hex 32)
    SERVICE_SECRET=$(openssl rand -hex 32)
    
    # Update .env with generated secrets
    sed -i.bak "s/your-very-secure-secret-key-here-change-this/$SECRET_KEY/" .env
    sed -i.bak "s/your-password-reset-secret-here-change-this/$RESET_SECRET/" .env
    sed -i.bak "s/your-service-communication-secret-here-change-this/$SERVICE_SECRET/" .env
    
    rm .env.bak 2>/dev/null || true
    
    echo "🔑 Generated secure keys automatically"
    echo "⚠️  Please update email settings in .env file!"
else
    echo "📄 Using existing .env file"
fi

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p nginx/ssl nginx/logs logs/media logs/orchestrator monitoring

# Generate SSL certificates
if [ ! -f nginx/ssl/ppl-meta.crt ]; then
    echo "🔐 Generating SSL certificates for development..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/ppl-meta.key \
        -out nginx/ssl/ppl-meta.crt \
        -subj "/C=US/ST=Development/L=Local/O=PPL Meta/CN=localhost" \
        2>/dev/null
    echo "✅ SSL certificates generated"
fi

# Create networks
echo "🌐 Setting up Docker networks..."
docker network create ppl-network 2>/dev/null || echo "   Network ppl-network already exists"

# Make scripts executable
chmod +x database/init/01-init-multiple-databases.sh

# Start core services first
echo "🚀 Starting PPL Meta Platform..."
echo "   Starting core infrastructure..."

# Start only the current service and its dependencies for now
docker-compose up -d postgres redis

echo "⏳ Waiting for database to be ready..."
sleep 15

# Check database health
if docker exec -it ppl-postgres pg_isready -U nickadmin -d ppl_db > /dev/null 2>&1; then
    echo "✅ Database is ready"
else
    echo "❌ Database startup failed"
    exit 1
fi

# Start the user management service
echo "🔧 Starting User Management Service..."
docker-compose up -d ppl-meta-node

# Wait for service to be ready
echo "⏳ Waiting for service to start..."
sleep 10

# Test service health
if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "✅ User Management Service is running"
else
    echo "⚠️  User Management Service may still be starting..."
fi

echo ""
echo "🎉 PPL Meta Platform Setup Complete!"
echo ""
echo "📊 Available Services:"
echo "   User Management API:  http://localhost:8001"
echo "   API Documentation:    http://localhost:8001/docs"
echo "   Health Check:         http://localhost:8001/api/v1/health"
echo "   Database:             localhost:5433"
echo ""
echo "🔧 Next Steps:"
echo "   1. Update email settings in .env file"
echo "   2. Test the API: curl http://localhost:8001/api/v1/health"
echo "   3. Visit documentation: http://localhost:8001/docs"
echo "   4. When ready, run full infrastructure: ./start-infrastructure.sh"
echo ""
echo "🛠️  Development Commands:"
echo "   View logs:     docker-compose logs -f ppl-meta-node"
echo "   Stop service:  docker-compose down"
echo "   Restart:       docker-compose restart ppl-meta-node"
echo ""
echo "📝 Configuration:"
echo "   Environment:   .env"
echo "   SSL Certs:     nginx/ssl/"
echo "   Logs:          logs/"
echo ""
