# Bug Analysis: Face Detection Overlays Only Show Last Group

## Problem Description

When playing back videos, green face detection rectangles only appear at the **END** of videos, not throughout the entire video where faces were actually detected. This happens consistently across all videos.

## Root Cause

### Location
`ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`

### Bug in `match_person_objects_within_group()` function

**Line 1052-1053:**
```python
individual_person_objects = {video_uuid: person_objs[0]}  # Use first person_object
```

**Line 1080:**
```python
individual_person_objects[next_uuid] = next_person_objs[0]
```

### What's Wrong

1. **Temporal Grouping Logic**: The function groups faces across multiple frame sequences into individuals
2. **Only First Person Object Stored**: For each video, only the **first** `person_object` is stored
3. **Representative Faces Lost**: Each `person_object` contains `representative_faces` with bounding boxes for that temporal group
4. **Database Storage**: When creating `individual_video_appearances` records (line 3031), only ONE person_object per video is available
5. **Result**: The `representative_faces` field in the database only contains faces from the LAST temporal group

### Example Scenario

Video has 3 temporal groups (face detection sequences):
- **Group 1** (frames 10-50): Person appears, faces detected → `person_obj_1` with representative_faces
- **Group 2** (frames 100-150): Person appears again → `person_obj_2` with representative_faces  
- **Group 3** (frames 200-250): Person appears again → `person_obj_3` with representative_faces

**Current Behavior:**
```python
individual_person_objects = {
    video_uuid: person_obj_1  # Only first object!
}
```

When stored in database:
```sql
INSERT INTO individual_video_appearances (
    representative_faces  -- Only contains faces from Group 1 or last processed group
)
```

**During Playback:**
- Frames 10-50: ❌ No green rectangles (data missing)
- Frames 100-150: ❌ No green rectangles (data missing)
- Frames 200-250: ✅ Green rectangles appear (only this group's data exists)

## Impact

### Frontend Display
- `simple_video_face_detection_overlay.dart` fetches face detections from database
- Database only has faces from last temporal group
- Green rectangles only drawn for frames in that group
- User sees incomplete face detection results

### Data Loss
- Multiple temporal groups of faces detected correctly
- All groups stored in person_objects by Orchestrator
- Only ONE group's faces preserved in individuals table
- Significant data loss during cross-video tracking

## Solution

### Option 1: Store All Person Objects (Recommended)

**Change from:**
```python
individual_person_objects = {video_uuid: person_objs[0]}
```

**To:**
```python
individual_person_objects = {video_uuid: person_objs}  # Store ALL objects as list
```

**Then aggregate representative_faces:**
```python
# When creating database record (line 3031)
all_representative_faces = []
person_objects_dict = individual_data.get('person_objects', {})
if video_uuid in person_objects_dict:
    person_objs_list = person_objects_dict[video_uuid]
    
    # Handle both single object and list
    if not isinstance(person_objs_list, list):
        person_objs_list = [person_objs_list]
    
    # Collect representative_faces from ALL person objects
    for person_obj in person_objs_list:
        if isinstance(person_obj, dict):
            rep_faces = person_obj.get('representative_faces', [])
            if rep_faces:
                all_representative_faces.extend(rep_faces)
    
    if all_representative_faces:
        representative_faces = json.dumps({'faces': all_representative_faces})
```

### Option 2: Merge Representative Faces During Grouping

Aggregate faces from all person_objects when creating the individual:

```python
# Collect all person objects
all_person_objs = []
for person_obj in person_objs:  # Iterate ALL, not just [0]
    all_person_objs.append(person_obj)

# Merge representative_faces
merged_faces = []
for obj in all_person_objs:
    faces = obj.get('representative_faces', [])
    merged_faces.extend(faces)

# Store merged data
individual_person_objects = {
    video_uuid: {
        'person_uuid': person_objs[0]['person_uuid'],
        'face_count': sum(obj['face_count'] for obj in all_person_objs),
        'representative_faces': merged_faces,  # All faces from all groups
        'merged_from': len(all_person_objs)  # Track merging
    }
}
```

## Testing Plan

### 1. Verify Problem
```bash
# Check database for representative_faces
psql -d ppl_meta_vmeta -c "
SELECT 
    individual_uuid,
    video_uuid,
    representative_faces::text,
    jsonb_array_length(representative_faces->'faces') as face_count
FROM individual_video_appearances
WHERE representative_faces IS NOT NULL
LIMIT 5;
"
```

### 2. After Fix - Verify Coverage
```bash
# Should see more faces per individual
# Face counts should match original person_objects totals
```

### 3. Frontend Testing
1. Play video with known multiple temporal groups
2. Verify green rectangles appear **throughout entire video**
3. Check all detected faces have overlays, not just last group

## Files to Modify

1. **`ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`**
   - Line ~1052: Change person_object storage to list
   - Line ~1080: Store all person_objects, not just first
   - Line ~3031: Aggregate representative_faces from all objects

2. **Testing Scripts**
   - Create test to verify all temporal groups preserved
   - Validate face counts before/after individual creation

## Expected Outcome

After fix:
- ✅ Green rectangles appear throughout entire video
- ✅ All detected faces have bounding box overlays
- ✅ No data loss during temporal grouping
- ✅ Database contains complete face detection information
- ✅ Playback experience matches detection reality
