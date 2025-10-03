#!/bin/bash

if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

API_PORT=${API_PORT:-8010}

echo "🏥 PPL Meta Phase 1 Health Check"
echo "================================"
echo ""

# Check if service is running
if curl -s http://localhost:$API_PORT/health > /dev/null; then
    echo "✅ Phase 1 API is running"
    
    # Get health status
    echo ""
    echo "📊 Health Status:"
    curl -s http://localhost:$API_PORT/health | python3 -m json.tool
    
    echo ""
    echo "📈 System Metrics:"
    curl -s http://localhost:$API_PORT/metrics | python3 -m json.tool
    
else
    echo "❌ Phase 1 API is not running"
    echo "💡 Start it with: ./start_phase1.sh"
fi
