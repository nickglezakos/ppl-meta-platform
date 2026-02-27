#!/bin/bash

# Cleanup script for RPi
# Removes Docker containers, images, and old files

set -e

echo "🧹 PPL Meta RPi Cleanup"
echo "======================="
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

# Old build artifacts and logs
echo "📂 Local Cleanup"

# Clean ppl-meta-deploy logs (but keep recent)
if [ -d "ppl-meta-deploy/logs" ]; then
    echo "  Removing logs older than 7 days..."
    find ppl-meta-deploy/logs -type f -mtime +7 -delete 2>/dev/null || true
fi

# Remove old tar/zip files
echo "  Removing old archives..."
find ~ -maxdepth 2 -type f \( -name "*.tar" -o -name "*.tar.gz" -o -name "*.zip" \) -mtime +30 -delete 2>/dev/null || true

# Python cache
echo "  Removing Python cache files..."
find ~ -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find ~ -type f -name "*.pyc" -delete 2>/dev/null || true

# Temporary files
echo "  Removing temporary files..."
rm -rf /tmp/*.tar* 2>/dev/null || true
rm -rf /tmp/*.zip 2>/dev/null || true

echo "  ✅ Local cleanup complete"
echo ""

# Show disk space
echo "💾 Disk Space Summary"
echo "  Available space:"
df -h / | tail -1
echo ""
echo "  Docker usage:"
docker system df
echo ""

# Optional aggressive cleanup
echo "⚠️  Optional aggressive cleanup (only if space critical):"
echo "  • Remove all unused images: sudo docker image prune -a"
echo "  • Remove all unused volumes: sudo docker volume prune -a"
echo "  • Clear apt cache: sudo apt-get clean && sudo apt-get autoclean"
echo "  • Remove old journal logs: sudo journalctl --vacuum=2w"
echo ""

echo "✅ Cleanup complete!"
