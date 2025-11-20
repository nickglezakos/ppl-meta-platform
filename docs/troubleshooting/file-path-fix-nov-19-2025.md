# File Path Mismatch Fix - November 19, 2025

## Problem Summary

Videos uploaded from Camera service to Media service were stored in database but physical files were not accessible to Vision service, causing "Media not found" errors during face detection.

---

## Root Cause

**Path Mismatch:**
- **Database stores:** `media/4cf362b1-.../video/2025/11/filename.mp4`
- **Old code saved to:** `storage/media/4cf362b1-.../video/2025/11/filename.mp4`
- **Vision service reads from:** Database path (no `storage/` prefix)
- **Result:** Vision cannot find files → Face detection fails → Pipeline stops

---

## Fix Applied

**File:** `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/services/media_service.py`

**Line 1067** - Changed `_save_file_to_storage()`:
```python
# OLD CODE (incorrect):
full_path = Path("storage") / storage_path

# NEW CODE (fixed):
full_path = Path(storage_path)  # Save at exact database path
```

**Additional updates:**
- Line 1116: Thumbnail service uses direct path
- Line 1213: Video metadata uses direct path  
- Line 1383: Removed fallback search logic

---

## API Endpoints Reference

### Authentication
```bash
# Login and get token
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'

# Response: { "access_token": "eyJ...", "token_type": "bearer" }
```

### Media Service (Port 8000)

**Search User's Media:**
```bash
# Endpoint: GET /api/v1/media/search
curl -s "http://localhost:8000/api/v1/media/search?page=1&page_size=10&collection_id=usb_camera_0" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Query Parameters:
# - media_types: Leave empty for all, use "video", "picture", etc. (lowercase)
# - collection_id: Filter by camera/collection
# - start_time / end_time: ISO 8601 date strings
# - page, page_size: Pagination
```

**Note:** Media type enum values are lowercase: `"video"`, `"picture"`, `"sound"`, etc.

### Orchestrator Service (Port 8002)

**Trigger Face Detection (Enhanced Logic V2):**
```bash
# Endpoint: GET /api/v1/media/{media_uuid}/faces/enhanced-v2
curl -s "http://localhost:8002/api/v1/media/{VIDEO_UUID}/faces/enhanced-v2" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Success Response:
# {
#   "success": true,
#   "session_uuid": "...",
#   "total_faces": 5,
#   "faces": [...]
# }

# Failure Response (file not found):
# {
#   "success": false,
#   "error": "Media not found: {uuid}"
# }
```

### Camera Service (Port 8005)

**Get Camera Recordings:**
```bash
# Endpoint: GET /api/v1/recordings/{camera_id}/latest
curl -s "http://localhost:8005/api/v1/recordings/usb_camera_0/latest" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Testing Procedure

### 1. Check Recent Uploads
```bash
export TOKEN="<your-token>"

# Get last 5 videos
curl -s "http://localhost:8000/api/v1/media/search?page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, v in enumerate(data, 1):
    print(f'{i}. UUID: {v[\"uuid\"]}')
    print(f'   Time: {v[\"created_at\"][:19]}')
    print(f'   Path: {v[\"file_path\"]}')
    print()
"
```

### 2. Verify File Exists on Disk
```bash
# Use path from database (e.g., media/4cf362b1-.../video/2025/11/filename.mp4)
ls -lh "/Users/nickgklezakos/Documents/ppl-meta-code/<DATABASE_PATH>"
```

### 3. Test Face Detection
```bash
# Replace VIDEO_UUID with actual UUID from step 1
curl -s "http://localhost:8002/api/v1/media/<VIDEO_UUID>/faces/enhanced-v2" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# SUCCESS if: "success": true, "total_faces": > 0
# FAILURE if: "error": "Media not found: ..."
```

### 4. Expected Results After Fix
- ✅ Files saved at: `/Users/nickgklezakos/Documents/ppl-meta-code/media/...`
- ✅ Face detection succeeds with faces found
- ✅ No "Media not found" errors
- ✅ Batch processing triggers after 5 videos

---

## Service Restart Commands

### Stop Old Services
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code
./scripts/stop-all-services.sh
```

### Start Services with Fix
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code
./scripts/start-all-services.sh

# Monitor logs:
tail -f logs/ppl-meta-media.log
tail -f logs/ppl-meta-cameras.log
tail -f logs/ppl-meta-orchestrator.log
```

---

## Test Recording Flow

1. **Start recording** from Flutter app (60-90 seconds = 2-3 segments)
2. **Monitor Camera logs:**
   ```bash
   tail -f logs/ppl-meta-cameras.log | grep -i "upload\|face_detection"
   ```
3. **Check Media uploads:**
   ```bash
   # After recording, query recent videos
   curl -s "http://localhost:8000/api/v1/media/search?page=1&page_size=5" \
     -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
   ```
4. **Verify files on disk:**
   ```bash
   ls -lh media/4cf362b1-3e05-4e85-81c7-c08a98c7e41b/video/2025/11/
   ```
5. **Test face detection manually:**
   ```bash
   curl -s "http://localhost:8002/api/v1/media/<UUID>/faces/enhanced-v2" \
     -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
   ```

---

## User Credentials

- **Email:** `fresh.user@example.com`
- **Password:** `NewPassword234!`
- **User ID (Integer):** `7`
- **User ID (UUID):** `4cf362b1-3e05-4e85-81c7-c08a98c7e41b`
- **Camera:** `usb_camera_0`

---

## November 19 Test Results

### Test 1: 11:40-11:43 AM (2:10 recording)
- ✅ 5 segments uploaded
- ❌ Face detection failed: "Media not found"
- **Issue:** Old code still running

### Test 2: 12:09-12:11 PM (2:12 recording)
- ✅ 5 segments uploaded (UUIDs: 91725759, 75ff21f6, bb4a5fbd, a2f81609, 12e20715)
- ❌ Face detection failed: "Media not found"
- **Issue:** Services running old code, fix not applied yet

**Next:** Restart services and test again

---

## Success Criteria

After fix is applied and services restarted:

1. ✅ Files exist at database path (no `storage/` prefix)
2. ✅ Face detection returns `"success": true`
3. ✅ Faces detected in videos
4. ✅ Batch processing triggers after 5 videos
5. ✅ Individuals and MVR people created

---

## Related Documentation

- **Pipeline Guide:** `/docs/guides/developer/continuous-individuals-and-mvr-pipeline.md`
- **Media Service:** `/ppl-meta-media/src/services/media_service.py`
- **Camera Service:** `/ppl-meta-cameras/src/services/camera_detection.py`
- **Service Scripts:** `/scripts/start-all-services.sh`, `/scripts/stop-all-services.sh`
