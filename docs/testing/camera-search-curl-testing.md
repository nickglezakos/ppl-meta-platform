# Camera Search Feature - Backend Testing with cURL

## Prerequisites

### Service URLs
- **Gateway**: http://localhost:8080
- **VMeta**: http://localhost:8008
- **Media**: http://localhost:8000
- **Node**: http://localhost:8001

### Log File Locations
```bash
# VMeta logs (main service logs)
/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# Gateway logs
/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/logs/ppl-meta-gateway.log

# Media Service logs
/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/logs/ppl-meta-media.log
```

### Test Credentials
- **Email**: `fresh.user@example.com`
- **Password**: `NewPassword234!`

---

## Step 1: Authentication - Get JWT Token

### Command
```bash
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' \
  2>/dev/null | python3 -m json.tool
```

### Expected Response
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "user_id": 7,
    "email": "fresh.user@example.com",
    "username": "fresh.user"
  }
}
```

### Action: Store Token
```bash
# Extract and store the token
export TOKEN=$(curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' \
  2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Verify token is set
echo "Token: $TOKEN"
```

### Validation
- ✅ Response has `access_token` field
- ✅ Token is not empty
- ✅ No error messages

---

## Step 2: Verify Authentication - Get Collections

### Purpose
Verify the token works by making an authenticated request to the media service.

### Command
```bash
curl -s "http://localhost:8080/api/v1/media/collections" \
  -H "Authorization: Bearer $TOKEN" \
  2>/dev/null | python3 -m json.tool
```

### Expected Response
```json
{
  "collections": [
    {
      "collection_id": "...",
      "name": "usb_camera_0 Collection",
      "created_at": "..."
    }
  ],
  "total": 13
}
```

### Validation
- ✅ Response is JSON, not error HTML
- ✅ Status code is 200
- ✅ Collections array is present
- ✅ "usb_camera_0 Collection" exists

---

## Step 3: Get Group Details

### Purpose
Verify the group exists and retrieve member information.

### Command
```bash
# Get specific group
GROUP_ID="grp_9e3fd3d2995f"

curl -s "http://localhost:8080/api/v1/individual-groups/$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  2>/dev/null | python3 -m json.tool
```

### Expected Response
```json
{
  "group_id": "grp_9e3fd3d2995f",
  "name": "Test Group",
  "member_count": 2,
  "member_ids": [
    "b24ad688-26f0-4e1e-9484-4fecec18df9c",
    "27627db6-71bb-4ee5-a6d8-883a3bc35aab"
  ]
}
```

### Validation
- ✅ Group exists
- ✅ `member_ids` array has MVR people UUIDs
- ✅ `member_count` > 0

---

## Step 4: Test Media Service Search

### Purpose
Verify the media service returns videos for the collection and time range.

### Command
```bash
curl -s "http://localhost:8080/api/v1/media/search" \
  -H "Authorization: Bearer $TOKEN" \
  -G \
  --data-urlencode "collection=usb_camera_0 Collection" \
  --data-urlencode "start_time=2025-12-08T12:53:00" \
  --data-urlencode "end_time=2025-12-18T12:53:00" \
  --data-urlencode "page_size=10" \
  2>/dev/null | python3 -m json.tool
```

### Expected Response
```json
{
  "videos": [
    {
      "video_uuid": "...",
      "collection_id": "...",
      "start_time": "...",
      "end_time": "..."
    }
  ],
  "total": 119,
  "page": 1
}
```

### Validation
- ✅ Videos array is not empty
- ✅ Total count > 0
- ✅ Each video has `video_uuid`

---

## Implementation Architecture

### Camera Search Flow (Correct Approach)

The camera search feature uses **existing vmeta endpoints** instead of reimplementing comparison logic:

1. **Get Video UUIDs from Media Service** ✅
   - Call media service `/api/v1/media/search` with collection and time range
   - Returns list of video UUIDs that match the criteria
   
2. **Get MVR People from Videos** ✅
   - Query vmeta database for MVR people that appear in those videos
   - Uses `individual_video_appearances` table to find person_object_uuid values
   
3. **Match Each Group Member Using VMeta's Match Endpoint** 🔄
   - For each MVR person UUID found in step 2:
     - Call vmeta's `/api/v1/mvr-people/individuals/{mvr_uuid}/match` endpoint
     - Pass group member UUIDs to find matches
     - Endpoint uses `MVRMatcher` service with pgvector similarity search
     - Returns similarity scores for matches above threshold (0.6)
   
4. **Aggregate Results** 🔄
   - Collect all matches from step 3
   - Get appearance details (video_uuid, person_object_uuid, timestamps)
   - Build response with matched individuals and their appearances

### Why Use Existing Endpoints?

**Instead of reimplementing:**
- ❌ Cosine similarity calculation
- ❌ pgvector string parsing
- ❌ Database connection management
- ❌ Embedding normalization

**We use vmeta's battle-tested code:**
- ✅ `MVRMatcher.find_matching_mvr()` - handles all comparison logic
- ✅ Proper pgvector handling via asyncpg
- ✅ Connection pooling managed by repository
- ✅ Existing OpenAPI endpoint: `POST /api/v1/mvr-people/individuals/{uuid}/match`

---

## Step 5: Camera Search - Direct to VMeta

### Purpose
Test the camera search endpoint directly through VMeta (bypassing gateway).

### Command
```bash
curl -X POST "http://localhost:8008/api/v1/individual-groups/$GROUP_ID/camera-search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "usb_camera_0 Collection",
    "start_time": "2025-12-08T12:53:00",
    "end_time": "2025-12-18T12:53:00",
    "confidence_threshold": 0.6
  }' \
  2>&1 | python3 -m json.tool
```

### Check VMeta Logs
```bash
# Watch logs in real-time while running the command
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# Or check last 50 lines after running
tail -n 50 /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log
```

### Expected Response
```json
{
  "group_id": "grp_9e3fd3d2995f",
  "search_parameters": {
    "camera_id": "usb_camera_0 Collection",
    "start_time": "2025-12-08T12:53:00",
    "end_time": "2025-12-18T12:53:00"
  },
  "matched_individuals": [
    {
      "mvr_people_uuid": "...",
      "match_count": 5,
      "confidence": 0.85,
      "appearances": [
        {
          "video_uuid": "...",
          "person_object_uuid": "...",
          "timestamp": "..."
        }
      ]
    }
  ],
  "summary": {
    "total_members_searched": 2,
    "members_found": 2,
    "total_appearances": 10
  }
}
```

### What to Look For in Logs
```bash
# Success indicators:
grep "Camera search request - auth_token present" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log | tail -1
grep "Found.*videos in collection" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log | tail -1
grep "Found.*MVR people in camera footage" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log | tail -1

# Error indicators:
grep "ERROR" /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log | tail -5
```

### Validation
- ✅ Status code is 200
- ✅ `matched_individuals` array present
- ✅ VMeta logs show "auth_token present: True"
- ✅ VMeta logs show "Found X videos in collection"
- ✅ No Python errors in logs

---

## Step 6: Camera Search - Through Gateway

### Purpose
Test the full flow through the gateway (production path).

### Command
```bash
curl -X POST "http://localhost:8080/api/v1/individual-groups/$GROUP_ID/camera-search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "usb_camera_0 Collection",
    "start_time": "2025-12-08T12:53:00",
    "end_time": "2025-12-18T12:53:00",
    "confidence_threshold": 0.6
  }' \
  2>&1 | python3 -m json.tool
```

### Check Gateway Logs
```bash
tail -n 50 /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/logs/ppl-meta-gateway.log
```

### What to Look For in Gateway Logs
```bash
# Should show auth header present
grep "VMETA-PROXY.*camera-search.*Auth header" \
  /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/logs/ppl-meta-gateway.log | tail -1
```

### Validation
- ✅ Gateway logs show "Auth header: Present"
- ✅ Same response as Step 5
- ✅ No 403 or 500 errors

---

## Debugging Commands

### Monitor All Logs Simultaneously
```bash
# Terminal 1: VMeta logs
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log

# Terminal 2: Gateway logs
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/logs/ppl-meta-gateway.log

# Terminal 3: Media logs
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/logs/ppl-meta-media.log
```

### Check Service Health
```bash
# All services
for port in 8000 8001 8002 8003 8005 8006 8007 8008 8080; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null || echo "DOWN"
done
```

### Verify Token is Valid
```bash
# Decode JWT token (requires jwt_tool or jq)
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool
```

### Check Recent Errors
```bash
# VMeta errors in last 100 lines
tail -n 100 /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-vmeta.log | grep -i "error\|exception\|failed"

# Gateway errors
tail -n 100 /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/logs/ppl-meta-gateway.log | grep -i "error\|exception\|failed"
```

---

## Common Issues and Solutions

### Issue 1: "Auth header: MISSING"
**Symptom**: Gateway logs show missing auth header
**Solution**: 
- Verify token is set: `echo $TOKEN`
- Re-run Step 1 to get fresh token
- Check header syntax: `-H "Authorization: Bearer $TOKEN"`

### Issue 2: 403 Forbidden from Media Service
**Symptom**: VMeta logs show 403 from media service
**Solution**:
- Check auth token is being passed to media service
- Verify media service is running: `curl http://localhost:8000/health`
- Check VMeta logs for "auth=True" in media service call

### Issue 3: "cannot access local variable 'np'"
**Symptom**: Python error in VMeta logs about numpy
**Solution**: 
- Check if numpy import is present in individual_groups_manager.py
- Restart VMeta service after fixing

### Issue 4: No matched_individuals returned
**Symptom**: Empty array despite videos existing
**Solution**:
- Check embedding similarity threshold (try lowering to 0.5)
- Verify MVR people have embeddings: Check database
- Look for "Found X MVR people in camera footage" in logs
- Check cosine similarity comparison logs

---

## Success Criteria

All steps should complete with:
1. ✅ Valid JWT token obtained
2. ✅ Collections retrieved successfully
3. ✅ Group details retrieved
4. ✅ Media service returns videos
5. ✅ Camera search returns matched individuals
6. ✅ VMeta logs show no errors
7. ✅ Gateway forwards auth header correctly
8. ✅ Frontend can display results with video navigation
