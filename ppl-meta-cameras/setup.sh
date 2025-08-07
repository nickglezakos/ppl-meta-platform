#!/bin/bash

# PPL Meta Cameras Microservice Setup Script

echo "🎥 Setting up PPL Meta Cameras Microservice"
echo "==========================================="

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✅ Docker found"
    DOCKER_AVAILABLE=true
else
    echo "❌ Docker not found"
    DOCKER_AVAILABLE=false
fi

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 found"
    PYTHON_AVAILABLE=true
else
    echo "❌ Python 3 not found"
    PYTHON_AVAILABLE=false
fi

echo ""
echo "Choose setup method:"
echo "1) Docker Compose (Recommended)"
echo "2) Local Development"
echo "3) Just show usage examples"

read -p "Enter choice (1-3): " CHOICE

case $CHOICE in
    1)
        if [ "$DOCKER_AVAILABLE" = true ]; then
            echo ""
            echo "🐳 Setting up with Docker Compose..."
            
            # Check if docker-compose.yml exists
            if [ -f "docker-compose.yml" ]; then
                echo "✅ docker-compose.yml found"
                
                echo ""
                echo "Starting services..."
                docker-compose up -d
                
                echo ""
                echo "Waiting for services to start..."
                sleep 10
                
                echo ""
                echo "Running tests..."
                ./test_service.sh
                
            else
                echo "❌ docker-compose.yml not found"
                exit 1
            fi
        else
            echo "❌ Docker not available"
            exit 1
        fi
        ;;
    2)
        if [ "$PYTHON_AVAILABLE" = true ]; then
            echo ""
            echo "🐍 Setting up for local development..."
            
            # Create virtual environment if it doesn't exist
            if [ ! -d "venv" ]; then
                echo "Creating virtual environment..."
                python3 -m venv venv
            fi
            
            # Activate virtual environment
            echo "Activating virtual environment..."
            source venv/bin/activate
            
            # Install dependencies
            echo "Installing dependencies..."
            pip install -r requirements.txt
            
            echo ""
            echo "✅ Local development setup complete!"
            echo ""
            echo "To run the service:"
            echo "1. source venv/bin/activate"
            echo "2. export DATABASE_URL=postgresql://postgres:password@localhost:5432/ppl_meta_cameras"
            echo "3. export JWT_SECRET_KEY=your-secret-key"
            echo "4. cd src && python main.py"
            echo ""
            echo "Service will be available at: http://localhost:8005"
            
        else
            echo "❌ Python 3 not available"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo "📚 Usage Examples"
        echo "================"
        echo ""
        echo "Docker Compose:"
        echo "  docker-compose up -d"
        echo "  docker-compose logs -f"
        echo "  docker-compose down"
        echo ""
        echo "Local Development:"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        echo "  cd src && python main.py"
        echo ""
        echo "API Usage:"
        echo "  # Get demo token"
        echo "  curl -X POST 'http://localhost:8005/api/v1/auth/demo-token?role=administrator'"
        echo ""
        echo "  # List cameras"
        echo "  curl -H 'Authorization: Bearer <token>' 'http://localhost:8005/api/v1/cameras/'"
        echo ""
        echo "  # Detect cameras"
        echo "  curl -H 'Authorization: Bearer <token>' -X POST 'http://localhost:8005/api/v1/cameras/detect'"
        echo ""
        echo "Documentation:"
        echo "  Swagger UI: http://localhost:8005/docs"
        echo "  ReDoc: http://localhost:8005/redoc"
        echo ""
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "============="
echo "• API Documentation: http://localhost:8005/docs"
echo "• Health Check: http://localhost:8005/health/"
echo "• Test Script: ./test_service.sh"
echo "• View Logs: docker-compose logs -f (Docker) or check src/logs/ (Local)"
echo ""
echo "🔧 Configuration:"
echo "• Default port: 8005"
echo "• Database: PostgreSQL (via Docker Compose)"
echo "• Camera access: Requires /dev/video* devices"
echo ""
echo "For production deployment, update environment variables in docker-compose.yml"
