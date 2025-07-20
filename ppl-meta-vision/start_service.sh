#!/bin/bash
# PPL Meta Vision Service - Start Script

echo "🚀 Starting PPL Meta Vision Service..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Virtual environment not found. Running setup..."
    ./setup_env.sh
fi

# Activate virtual environment
source venv/bin/activate

# Check if face detector file exists
if [ ! -f "src/extracted_face_detector.py" ]; then
    echo "❌ Face detector file not found at src/extracted_face_detector.py"
    echo "   Please copy from notebooks/extracted_face_detector.py"
    exit 1
fi

# Start the service
echo "🏃 Starting PPL Meta Vision Service on port 8003..."
python src/main.py
