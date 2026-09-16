#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path('/Users/nickgklezakos/Documents/ppl-meta-code')

# Cameras Redis defaults
for rel in [
    'ppl-meta-cameras/src/tasks/instant_detection_tasks.py',
    'ppl-meta-cameras/src/services/instant_detection.py',
]:
    p = ROOT / rel
    t = p.read_text()
    t2 = t
    for a, b in [
        ("getenv('REDIS_HOST','localhost')", "getenv('REDIS_HOST','redis')"),
        ('getenv("REDIS_HOST","localhost")', 'getenv("REDIS_HOST","redis")'),
        ("getenv('REDIS_HOST', 'localhost')", "getenv('REDIS_HOST', 'redis')"),
        ('getenv("REDIS_HOST", "localhost")', 'getenv("REDIS_HOST", "redis")'),
    ]:
        t2 = t2.replace(a, b)
    if t2 != t:
        p.write_text(t2)
        print('updated', rel)
    else:
        print('no change', rel)

# Orchestrator service clients / main defaults
for rel in [
    'ppl-meta-orchestrator/src/service_clients.py',
    'ppl-meta-orchestrator/src/main.py',
]:
    p = ROOT / rel
    t = p.read_text()
    t2 = (t
          .replace('http://localhost:8003', 'http://ppl-meta-vision:8003')
          .replace('http://localhost:8005', 'http://ppl-meta-cameras:8005')
          .replace('http://localhost:8000', 'http://ppl-meta-media:8000'))
    p.write_text(t2)
    print(rel, 'localhost left', t2.count('localhost:800'))

# Validate face_detection_endpoints replacements
p = ROOT / 'ppl-meta-orchestrator/src/face_detection_endpoints.py'
t = p.read_text()
bad = re.findall(r'(?<![fF])"[^"]*\{_vision_base_url\(\)\}[^"]*"', t)
print('face_detection bad non-f strings', len(bad))
for b in bad[:5]:
    print(' ', b[:100])
print('localhost:8003 left', t.count('localhost:8003'))
