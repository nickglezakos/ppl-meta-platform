#!/bin/bash

# PPL Meta Frontend - Flutter Setup Script
# This script helps set up Flutter for local development

echo "🏗️  PPL Meta Frontend - Flutter Setup"
echo "======================================"

# Check if Flutter is installed
if command -v flutter &> /dev/null; then
    echo "✅ Flutter is already installed:"
    flutter --version
else
    echo "❌ Flutter is not installed."
    echo ""
    echo "📋 To install Flutter:"
    echo "1. Visit: https://docs.flutter.dev/get-started/install/macos"
    echo "2. Download Flutter SDK"
    echo "3. Add Flutter to your PATH"
    echo "4. Run 'flutter doctor' to verify installation"
    echo ""
    echo "🚀 Quick install via Homebrew (if you have it):"
    echo "   brew install --cask flutter"
    echo ""
    exit 1
fi

echo ""
echo "🔍 Running Flutter Doctor..."
flutter doctor

echo ""
echo "📱 Setting up Frontend Dependencies..."
cd "$(dirname "$0")/ppl-meta-frontend" || exit 1

echo "📦 Installing dependencies..."
flutter pub get

echo "🏗️  Generating code..."
flutter packages pub run build_runner build --delete-conflicting-outputs

echo ""
echo "✅ Frontend setup complete!"
echo ""
echo "🚀 Next steps:"
echo "• Run 'flutter run -d chrome' to start web development"
echo "• Run 'flutter run -d macos' to start desktop development"
echo "• Use VS Code tasks for integrated development"
echo ""
echo "📋 Available VS Code tasks:"
echo "• 📱 Start Frontend (Web)"
echo "• 📱 Start Frontend (Desktop)"  
echo "• 🚀 Start Full Stack (Backend + Frontend)"
