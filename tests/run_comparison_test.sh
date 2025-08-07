#!/usr/bin/env bash
# Quick test script to compare Mini vs Media service face detection

echo "🚀 Running Mini vs Media Service Comparison Test"
echo "================================================"

# Make sure the mini service is running
echo "📋 Checking services..."
curl -s http://localhost:8004/ > /dev/null && echo "✅ Mini service is running" || echo "❌ Mini service not responding"
curl -s http://localhost:8000/health > /dev/null && echo "✅ Media service is running" || echo "❌ Media service not responding"

echo ""
echo "🧪 Running comparison test..."
python3 test_comparison.py

echo ""
echo "📊 Check comparison_results.json for detailed results"
