#!/bin/bash
# Setup script for Individual Headless Testing
# PPL Meta Platform - Cross-Video Individual Tracking

echo "🧪 Setting up Individual Headless Testing Environment"
echo "=================================================="

# Check if Python 3.9+ is available
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
required_version="3.9"

if [[ $(echo "$python_version $required_version" | awk '{print ($1 >= $2)}') == 1 ]]; then
    echo "✅ Python $python_version found (required: $required_version+)"
else
    echo "❌ Python $required_version+ required. Found: $python_version"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📋 Installing requirements..."
pip install -r requirements.txt

# Make the testing script executable
echo "🔧 Making testing script executable..."
chmod +x individual_headless_testing.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To run the testing script:"
echo "   source venv/bin/activate"
echo "   python individual_headless_testing.py"
echo ""
echo "📋 Optional arguments:"
echo "   --api-url http://localhost:8001    # API server URL"
echo "   --auth-token YOUR_TOKEN           # Authentication token" 
echo "   --timeout 30                      # Request timeout (seconds)"
echo "   --debug                           # Enable debug mode"
echo ""
echo "💡 Example usage:"
echo "   python individual_headless_testing.py --api-url http://localhost:8001 --debug"
echo ""