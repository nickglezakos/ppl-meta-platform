#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

echo "🚀 Starting PPL Meta Phase 1 Enhanced Person Detection System"
echo "📊 Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo "🌐 API Server: http://0.0.0.0:$API_PORT"
echo "📖 API Documentation: http://localhost:$API_PORT/docs"
echo ""

# Start the Phase 1 application
export PYTHONPATH="$SCRIPT_DIR/integration:$PYTHONPATH"
python integration/phase1_integration.py
