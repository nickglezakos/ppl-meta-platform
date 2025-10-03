#!/bin/bash

echo "🚀 Starting PPL Meta vmeta Service (Minimal Version)"
echo "================================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables if they exist
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

echo "🌐 vmeta Service will be available at: http://localhost:8008"
echo "📖 API Documentation: http://localhost:8008/docs"
echo ""

# Start the minimal vmeta service
cd src && python main_minimal.py