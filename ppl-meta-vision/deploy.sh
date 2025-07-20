#!/bin/bash
# PPL Meta Vision Service Deployment Script

echo "🚀 Deploying PPL Meta Vision Service..."

# Build Docker image
echo "📦 Building Docker image..."
docker-compose build

# Start the service
echo "🏃 Starting service..."
docker-compose up -d

# Wait for service to start
echo "⏳ Waiting for service to be ready..."
sleep 10

# Health check
echo "🏥 Checking service health..."
curl -f http://localhost:8003/health || echo "❌ Health check failed"

echo "✅ PPL Meta Vision Service deployment complete!"
echo "📊 Service available at: http://localhost:8003"
echo "📚 Documentation at: http://localhost:8003/docs"
