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
