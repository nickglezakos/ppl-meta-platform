# Instant Detection - Quick Start Guide

Get instant face detection running in 5 minutes!

## Prerequisites

**Two services must be running:**

1. **Vision Service** (port 8003) - Face detection (Haar + Dlib)
2. **VMeta Service** (port 8008) - Age/gender detection (DeepFace)

Instant detection uses existing service APIs - no model downloads needed!

## Step 1: Start Services

```bash
# Terminal 1: Vision Service
cd ppl-meta-vision
source venv/bin/activate
python src/main.py

# Terminal 2: VMeta Service  
cd ppl-meta-vmeta/src
source ../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8008 --reload
```

Wait for both services to start

## Step 2: Start Camera Service

```bash
cd ppl-meta-cameras
source venv/bin/activate
python src/main.py
```

## Step 3: Start Instant Detection

```bash
# Replace 'usb_camera_0' with your camera ID
curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
```

## Step 4: Get Results

```bash
# Wait 6 seconds for first results, then:
curl http://localhost:8005/api/v1/instant-detection/results/usb_camera_0 | jq
```

**Results are kept in memory** until replaced by the next iteration (every 5 seconds).
This means you can access the latest instant results anytime while recording is active.

## Step 5: Access from Other Hooks

```python
# From any other module in Camera Service:
from src.services.instant_detection import get_latest_instant_results

# Get latest results for a camera
results = get_latest_instant_results("usb_camera_0")
if results:
    for person in results["person_objects"]:
        print(f"{person['age_gender']['gender']}, {person['age_gender']['age_range']}")
```

```bash
# Run this to see updates every 6 seconds
watch -n 6 "curl -s http://localhost:8005/api/v1/instant-detection/results/usb_camera_0 | jq '.person_objects[] | {age: .age_gender.age_range, gender: .age_gender.gender, confidence: .avg_confidence}'"
```

---

## Python Example

```python
import requests
import time

# Start
requests.post("http://localhost:8005/api/v1/instant-detection/start/usb_camera_0")

# Poll for results
while True:
    response = requests.get(
        "http://localhost:8005/api/v1/instant-detection/results/usb_camera_0"
    )
    
    if response.status_code == 200:
        result = response.json()
        for person in result['person_objects']:
            print(f"{person['age_gender']['gender']}, {person['age_gender']['age_range']}")
    
    time.sleep(6)
```

---

## Troubleshooting

**"Vision Service not responding"**
→ Ensure Vision Service is running on port 8003
→ Check: `curl http://localhost:8003/health`

**"Camera not found"**
→ Check camera ID with `GET /api/v1/cameras`

**"Age/gender shows 'unknown'"**
→ Age/gender models not yet implemented in Vision Service (placeholder data returned)
→ Face detection and person grouping still work correctly

**"No recent results"**
→ Wait 10 seconds for first results

**"Thread not starting"**
→ Stop existing instance: `POST /stop`

---

## Done! 🎉

You now have instant face detection running parallel to your main recording pipeline!

- **Every 5 seconds**: New results with faces, people, age, and gender
- **~0.5 seconds**: Processing time per iteration
- **Zero impact**: Main pipeline untouched

See full documentation in `docs/guides/developer/instant-detection-implementation.md`
