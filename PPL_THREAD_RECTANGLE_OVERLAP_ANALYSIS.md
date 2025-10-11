# PPL Thread Rectangle Overlap Grouping Analysis
*PPL Meta Platform v2.19.4 - Algorithm Investigation*
*Date: October 8, 2025*

## 🔍 Current Implementation Analysis

### **What the Current `/person-objects/{media_id}` Endpoint Actually Does**

After examining the code, I found that the current PPL Thread endpoint in `/ppl-meta-orchestrator/src/ppl_thread_endpoints.py` **does NOT** use rectangle area overlap grouping. Instead, it uses:

```python
# Simple heuristic grouping (NOT rectangle overlap)
if total_faces == 0:
    total_persons = 0
elif total_faces <= 5:
    total_persons = 1  # Small group = likely 1 person
elif total_faces <= 20:
    total_persons = max(1, total_faces // 3)  # Medium group
else:
    total_persons = max(1, total_faces // 5)  # Large group
```

### **Available Rectangle Overlap Algorithm**

However, there IS a rectangle overlap function available in the Vision service (`/ppl-meta-vision/src/main.py`):

```python
def _faces_overlap(bbox1: List[int], bbox2: List[int], threshold: float = 0.3) -> bool:
    """Check if two face bounding boxes overlap significantly."""
    # Calculate intersection coordinates
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2) 
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    # Calculate areas
    intersection_area = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = area1 + area2 - intersection_area
    
    # Calculate IoU (Intersection over Union)
    iou = intersection_area / union_area if union_area > 0 else 0
    return iou >= threshold
```

## 🧮 Rectangle Area Overlap Grouping Algorithm

### **Step-by-Step Algorithm (If Implemented)**

Here's how a rectangle area overlap grouping method would work:

#### **Step 1: Data Preparation**
```
INPUT: List of face detections with bounding boxes
Each face: {
  "id": "face_001",
  "bbox_x1": 100, "bbox_y1": 150,
  "bbox_x2": 200, "bbox_y2": 250,
  "frame_number": 1,
  "confidence": 0.95
}
```

#### **Step 2: Calculate Intersection over Union (IoU)**
```
For each pair of faces (face_A, face_B):
  
  1. Extract bounding boxes:
     bbox_A = [x1_A, y1_A, x2_A, y2_A]
     bbox_B = [x1_B, y1_B, x2_B, y2_B]
  
  2. Calculate intersection rectangle:
     x1_intersection = max(x1_A, x1_B)
     y1_intersection = max(y1_A, y1_B)
     x2_intersection = min(x2_A, x2_B)
     y2_intersection = min(y2_A, y2_B)
  
  3. Check if rectangles overlap:
     if x1_intersection >= x2_intersection OR y1_intersection >= y2_intersection:
       intersection_area = 0  # No overlap
     else:
       intersection_area = (x2_intersection - x1_intersection) * (y2_intersection - y1_intersection)
  
  4. Calculate individual areas:
     area_A = (x2_A - x1_A) * (y2_A - y1_A)
     area_B = (x2_B - x1_B) * (y2_B - y1_B)
  
  5. Calculate union area:
     union_area = area_A + area_B - intersection_area
  
  6. Calculate IoU percentage:
     iou = intersection_area / union_area * 100
```

#### **Step 3: Apply Overlap Threshold**
```
For each face pair:
  if iou >= overlap_threshold (e.g., 30%):
    mark faces as "overlapping" (same person)
  else:
    mark faces as "separate" (different persons)
```

#### **Step 4: Group Creation**
```
1. Create groups using Union-Find algorithm:
   - Start with each face as its own group
   - For each overlapping pair: merge their groups
   - Result: Connected components = person groups

2. Count final groups:
   total_persons = number_of_unique_groups
   
3. Return results:
   {
     "total_faces": original_face_count,
     "total_persons": total_persons,
     "grouping_method": "rectangle_area_overlap",
     "overlap_threshold": threshold_percentage
   }
```

#### **Step 5: Quality Metrics**
```
Calculate grouping efficiency:
  efficiency = ((total_faces - total_persons) / total_faces) * 100
  
Track overlap statistics:
  - Average IoU per group
  - Maximum overlap detected
  - Number of merged groups
```

## 🎯 Algorithm Comparison

### **Current Simple Heuristic**
```
✅ Pros: Fast, simple, no computation required
❌ Cons: Inaccurate, no spatial awareness, fixed ratios
```

### **Rectangle Area Overlap (IoU-based)**
```
✅ Pros: Spatially aware, accounts for actual face positions
✅ Pros: Handles overlapping faces accurately  
❌ Cons: More computationally intensive
❌ Cons: Requires proper bounding box data
```

### **Position-based Tolerance (VisionFaceGroupingEngine)**
```
✅ Pros: Tracks faces across frames, handles movement
✅ Pros: Percentage-based tolerance, chronological processing
❌ Cons: Doesn't account for face size/overlap
❌ Cons: More complex implementation
```

## 📊 Implementation Status

### **Currently Used in PPL Thread Endpoint**
- ❌ **Rectangle Area Overlap**: NOT implemented
- ✅ **Simple Heuristic**: Currently active (faces ÷ 3 or ÷ 5)

### **Available but Not Used**
- ⚠️ **IoU Function**: Available in Vision service but not integrated
- ⚠️ **Position Tolerance**: Available in VisionFaceGroupingEngine but not used by simplified endpoint

## 🚀 Recommendation

To implement true rectangle area overlap grouping in the PPL Thread endpoint, we would need to:

1. **Modify `/ppl-meta-orchestrator/src/ppl_thread_endpoints.py`**
2. **Import the `_faces_overlap` function** from Vision service
3. **Implement the IoU-based grouping algorithm** as outlined above
4. **Replace the simple heuristic** with spatial overlap detection

This would provide more accurate person counting based on actual face rectangle overlap percentages rather than arbitrary division ratios.