#!/usr/bin/env python3
"""
Check Redis for instant detection cached data
"""

import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, decode_responses=False)

print("🔍 Checking Redis for instant_detection:* keys...\n")

# Find all instant detection keys
keys = r.keys("instant_detection:*")

if not keys:
    print("✅ No instant_detection:* keys found in Redis (clean state)\n")
else:
    print(f"⚠️ Found {len(keys)} instant_detection keys:\n")
    
    for key_bytes in keys:
        key = key_bytes.decode('utf-8')
        ttl = r.ttl(key_bytes)
        value_bytes = r.get(key_bytes)
        
        if value_bytes:
            try:
                value = json.loads(value_bytes.decode('utf-8'))
                
                # Extract key info
                camera_id = key.replace("instant_detection:", "")
                timestamp = value.get('timestamp', 'N/A')
                person_objects = value.get('person_objects', [])
                count = len(person_objects)
                demographics = value.get('demographics', {})
                
                # Calculate age
                age_str = "unknown age"
                if timestamp != 'N/A':
                    try:
                        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        age_seconds = (datetime.utcnow().replace(tzinfo=ts.tzinfo) - ts).total_seconds()
                        age_str = f"{age_seconds:.1f}s ago"
                    except:
                        pass
                
                print(f"📦 Key: {key}")
                print(f"   Camera ID: {camera_id}")
                print(f"   Person Count: {count}")
                print(f"   Timestamp: {timestamp} ({age_str})")
                print(f"   TTL: {ttl}s remaining")
                print(f"   Demographics: {demographics}")
                print()
                
            except Exception as e:
                print(f"❌ Could not parse {key}: {e}\n")

print("\n🧹 To clear all stale data, run:")
print("   python3 -c \"import redis; r = redis.Redis(); r.delete(*r.keys('instant_detection:*'))\"")
