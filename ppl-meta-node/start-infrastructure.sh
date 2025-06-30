#!/bin/bash
# PPL Meta Platform Infrastructure Startup Script
# This script initializes and starts the complete microservices infrastructure

set -e

echo "🚀 Starting PPL Meta Platform Infrastructure..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Please update the .env file with your actual configuration values!"
    echo "   Especially the SECRET_KEY, email settings, and domain name."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p nginx/ssl
mkdir -p nginx/logs
mkdir -p logs/media
mkdir -p logs/orchestrator
mkdir -p monitoring

# Generate SSL certificates for development (self-signed)
if [ ! -f nginx/ssl/ppl-meta.crt ]; then
    echo "🔐 Generating self-signed SSL certificates for development..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/ppl-meta.key \
        -out nginx/ssl/ppl-meta.crt \
        -subj "/C=US/ST=State/L=City/O=PPL Meta/CN=localhost"
fi

# Create external networks
echo "🌐 Creating Docker networks..."
docker network create ppl-network 2>/dev/null || echo "Network ppl-network already exists"

# Make database init script executable
chmod +x database/init/01-init-multiple-databases.sh

# Start the infrastructure
echo "🐳 Starting PPL Meta Platform infrastructure..."
docker-compose -f docker-compose.infrastructure.yml up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🏥 Checking service health..."

services=("nginx-gateway" "ppl-meta-gateway" "ppl-meta-node" "ppl-postgres" "consul")
for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" | grep -q $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
    fi
done

echo ""
echo "🎉 PPL Meta Platform Infrastructure Started!"
echo ""
echo "📊 Service URLs:"
echo "   Main Gateway:      https://localhost (or http://localhost)"
echo "   User Management:   http://localhost/users/"
echo "   Media Service:     http://localhost/media/"
echo "   API Documentation: http://localhost/api/docs"
echo "   Prometheus:        http://localhost:9090"
echo "   Grafana:           http://localhost:3000 (admin/admin)"
echo "   Consul UI:         http://localhost:8500"
echo ""
echo "🔧 Configuration:"
echo "   Update .env file with your settings"
echo "   SSL certificates in nginx/ssl/ (self-signed for development)"
echo "   Logs in nginx/logs/ and logs/"
echo ""
echo "🛠️  Development Commands:"
echo "   View logs:    docker-compose -f docker-compose.infrastructure.yml logs -f [service]"
echo "   Stop all:     docker-compose -f docker-compose.infrastructure.yml down"
echo "   Restart:      docker-compose -f docker-compose.infrastructure.yml restart [service]"
echo ""

# Show important security notice
echo "⚠️  SECURITY NOTICE:"
echo "   1. Change all default passwords in .env file"
echo "   2. Generate proper SSL certificates for production"
echo "   3. Update domain names and firewall rules"
echo "   4. Configure WireGuard VPN for edge devices"
echo ""
