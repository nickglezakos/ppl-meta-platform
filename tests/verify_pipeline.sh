#!/bin/bash

# Simple pipeline verification script
# Checks if face detection and pipeline ran after the 8-minute recording

TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "=================================="
echo "Pipeline Verification"
echo "=================================="
echo ""

# Step 1: Count videos
echo "Step 1: Checking videos..."
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/videos?limit=20" > /tmp/videos.json
VIDEO_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/videos.json')); print(len(d.get('videos', [])))")
echo "Found $VIDEO_COUNT videos"
echo ""

# Step 2: Get first video UUID and check individuals
echo "Step 2: Checking individuals on first video..."
FIRST_UUID=$(python3 -c "import json; d=json.load(open('/tmp/videos.json')); print(d['videos'][0]['uuid'] if d.get('videos') else '')")

if [ -n "$FIRST_UUID" ]; then
    echo "First video UUID: $FIRST_UUID"
    curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8008/api/v1/individuals/video/${FIRST_UUID}" > /tmp/individuals.json
    
    python3 << EOF
import json
try:
    with open('/tmp/individuals.json') as f:
        data = json.load(f)
    
    if 'detail' in data:
        print(f"  ⚠️  {data['detail']}")
    elif 'individuals' in data:
        individuals = data['individuals']
        print(f"  ✅ Found {len(individuals)} individuals")
        for i, ind in enumerate(individuals[:3], 1):
            print(f"     {i}. Individual {ind.get('individual_id', 'N/A')}")
    else:
        print(f"  Response: {list(data.keys())}")
except Exception as e:
    print(f"  ⚠️  Error: {e}")
EOF
else
    echo "  ❌ No video UUID found"
fi

echo ""

# Step 3: Check MVR people
echo "Step 3: Checking MVR people..."
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8008/api/v1/mvr-people" > /tmp/mvr.json

python3 << 'EOF'
import json
try:
    with open('/tmp/mvr.json') as f:
        data = json.load(f)
    
    if 'detail' in data:
        print(f"  ⚠️  {data['detail']}")
    elif isinstance(data, list):
        print(f"  ✅ Found {len(data)} MVR people")
        for i, person in enumerate(data[:5], 1):
            mvr_id = person.get('mvr_id', person.get('id', 'N/A'))
            name = person.get('person_name', person.get('name', 'Unknown'))
            print(f"     {i}. MVR {mvr_id}: {name}")
    elif 'mvr_people' in data or 'people' in data:
        people = data.get('mvr_people', data.get('people', []))
        print(f"  ✅ Found {len(people)} MVR people")
        for i, person in enumerate(people[:5], 1):
            mvr_id = person.get('mvr_id', person.get('id', 'N/A'))
            name = person.get('person_name', person.get('name', 'Unknown'))
            print(f"     {i}. MVR {mvr_id}: {name}")
    else:
        print(f"  Response keys: {list(data.keys())}")
except Exception as e:
    print(f"  ⚠️  Error: {e}")
EOF

echo ""
echo "=================================="
echo "Verification complete"
echo "=================================="
