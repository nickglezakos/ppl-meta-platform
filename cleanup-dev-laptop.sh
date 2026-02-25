#!/bin/bash

# Cleanup script for dev laptop (macOS)
# Removes Docker containers, images, build artifacts, and old files

set -e

echo "🧹 PPL Meta Dev Laptop Cleanup"
echo "=============================="
echo ""

# Docker cleanup
echo "🐳 Docker Cleanup"
echo "  Removing stopped containers..."
docker container prune -f

echo "  Removing dangling images..."
docker image prune -f

echo "  Removing dangling build cache..."
docker builder prune -f

echo "  ✅ Docker cleanup complete"
echo ""

# Old build artifacts
echo "🏗️  Build Artifacts Cleanup"

# Flutter build cache
if [ -d "ppl-meta-signage-simple-player/build" ]; then
    echo "  Removing Flutter build directory..."
    rm -rf ppl-meta-signage-simple-player/build
fi

if [ -d "ppl-meta-signage-simple-player/.dart_tool" ]; then
    echo "  Removing Dart tool cache..."
    rm -rf ppl-meta-signage-simple-player/.dart_tool
fi

if [ -d "ppl-meta-frontend/build" ]; then
    echo "  Removing frontend build directory..."
    rm -rf ppl-meta-frontend/build
fi

if [ -d "ppl-meta-frontend/.dart_tool" ]; then
    echo "  Removing frontend Dart cache..."
    rm -rf ppl-meta-frontend/.dart_tool
fi

# Python cache
echo "  Removing Python cache files..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true

echo "  ✅ Build artifacts cleanup complete"
echo ""

# Old zip files and archives
echo "📦 Archive Cleanup"
if [ -d "archive" ]; then
    echo "  Listing old archives in archive/ directory:"
    ls -lh archive/ | grep -E "\.zip|\.tar|\.gz" || echo "  No archives found"
    echo "  (Skipping deletion - review first with: ls -lh archive/)"
fi

echo "  Removing old Docker build tars..."
rm -f /tmp/ppl-meta-*.tar 2>/dev/null || true

echo "  ✅ Archive cleanup checked"
echo ""

# Logs cleanup (optional - keep recent logs)
echo "📂 Logs Cleanup"
if [ -d "logs" ]; then
    echo "  Listing log files:"
    ls -lh logs/ 2>/dev/null | head -10 || echo "  No logs directory"
    echo "  (Skipping deletion - logs may be needed for debugging)"
fi

echo "  ✅ Logs checked"
echo ""

# Show disk space saved
echo "💾 Disk Space Summary"
echo "  Docker system info:"
docker system df
echo ""

echo "✅ Cleanup complete!"
echo ""
echo "To cleanup more aggressively, you can also:"
echo "  • Remove unused Docker images: docker image prune -a"
echo "  • Remove all Docker volumes: docker volume prune -a"
echo "  • Clean npm cache: npm cache clean --force (if Node.js used)"
echo "  • Clean Flutter cache: flutter clean (for signage app)"
echo "  • Remove old archives in archive/ directory"
