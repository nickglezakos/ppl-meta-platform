#!/bin/bash
# PPL Meta Vision Service - Python Environment Setup

echo "🐍 Setting up PPL Meta Vision Service Python Environment..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Python environment setup complete!"
echo "🚀 To activate: source venv/bin/activate"
echo "🏃 To run service: python src/main.py"
