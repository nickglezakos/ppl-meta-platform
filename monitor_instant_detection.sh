#!/bin/bash

echo "🎬 Monitor Instant Detection - Real-time"
echo "========================================"
echo ""
echo "Start camera recording NOW, then this script will monitor for 30 seconds..."
echo ""

for i in {1..30}; do
    echo "[$i/30] Checking Redis cache..."
    
    # Check Redis for instant detection keys
    cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras
    source venv/bin/activate
    python3 -c "
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, decode_responses=False)
keys = r.keys('instant_detection:*')

if keys:
    for key_bytes in keys:
        key = key_bytes.decode('utf-8')
        value_bytes = r.get(key_bytes)
        if value_bytes:
            value = json.loads(value_bytes.decode('utf-8'))
            camera_id = key.replace('instant_detection:', '')
            count = len(value.get('person_objects', []))
            timestamp = value.get('timestamp', 'N/A')
            demographics = value.get('demographics', {})
            print(f'✅ Found: {camera_id} - {count} people - {timestamp}')
            print(f'   Demographics: {demographics}')
else:
    print('❌ No instant_detection:* keys in Redis')
" 2>/dev/null || echo "❌ Redis check failed"
    
    echo ""
    sleep 1
done

echo ""
echo "✅ Monitoring complete"
