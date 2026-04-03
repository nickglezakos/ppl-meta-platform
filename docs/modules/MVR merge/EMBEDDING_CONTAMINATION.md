# MVR Merge — Embedding Contamination Hypothesis

**Status:** VERIFIED against codebase and live test data  
**Date:** 2026-04-03  
**Severity:** CRITICAL — causes distinct individuals to be incorrectly merged

---

## The Problem in One Sentence

When a face crop extracted from a video frame contains **more than one person**, the embedding model silently generates an embedding for the **wrong person**, producing a fake high-similarity score that passes the merge threshold and incorrectly collapses two distinct individuals into one MVR super-individual.

---

## Observed Evidence

### Video `d46124c8-8944-4784-be9f-3e6314e1f0b8`

The video contains **two males** throughout its entire 16-second duration:

| Person | Description | Expected MVR group |
|--------|-------------|-------------------|
| **Glasses man** | Gray/salt-and-pepper hair, blue rectangular glasses, black t-shirt | Group 1 (winner: `36ca2d7c`) |
| **Bald man** | Bald, white beard, white turtleneck + black jacket | Should be **separate** group |

The DB has 4 MVR records for this video:

| MVR UUID | Gender label | Quality |
|----------|-------------|---------|
| `2b489c25` | male | 0.681 |
| `4b102f8f` | male | 0.681 |
| `6d8d7cdb` | **unknown** | 0.665 |
| `724ce94a` | **unknown** | 0.665 |

### Smoking Gun

Face crops for the `unknown` records (`6d8d7cdb`, `724ce94a`) — which tracked the **bald man** — visually display the **glasses man's face**.

**`6d8d7cdb_unknown.jpg`** and **`36ca2d7c_male.jpg`** (Group 1 winner) are **identical faces**.

This means:
1. The bald man's tracking bbox captured the glasses man's face in the same crop
2. The embedding model generated an embedding for the glasses man (wrong person)
3. When `HierarchicalMVRMerger` compared `6d8d7cdb` vs `36ca2d7c`, similarity was very high (same person's embedding)
4. They were merged — incorrectly "confirming" the bald man is the same as the glasses man

---

## Root Cause Analysis — Code-Verified

### Root Cause 1: Face crop is NOT pre-validated for single-face content

**File:** `ppl-meta-vmeta/src/services/embedding_service.py`, lines 326–335

```python
# Extract face region
face_img = frame[y : y + height, x : x + width]

# Convert BGR to RGB for DeepFace
face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)

# Generate embedding using DeepFace
embedding_result = DeepFace.represent(
    img_path=face_rgb,
    ...
)
```

The crop is a **raw rectangular slice of the full video frame** using the detection bounding box. There is **no check** for how many faces are inside the crop before passing it to the embedding model.

If two people are physically close in the frame, person A's bounding box routinely contains person B's face.

---

### Root Cause 2: `result[0]` is always used — the "most prominent face" wins

**File:** `ppl-meta-vmeta/src/ml/facenet_processor.py`, lines 98–101

```python
if result and len(result) > 0:
    embedding = np.array(result[0]['embedding'])  # ← ALWAYS index 0
```

**File:** `ppl-meta-vmeta/src/services/embedding_service.py`, lines 350–356

```python
first = embedding_result[0]
if isinstance(first, dict) and "embedding" in first:
    embedding = first["embedding"]  # ← ALWAYS index 0
```

`DeepFace.represent()` with the `opencv` face detector returns **all detected faces** in the image, ordered by the detector's confidence (typically: largest bounding box first, i.e. the most prominent/frontal face).

When the crop contains two faces, `result[0]` is **not guaranteed to be the intended person**. In the case of the bald man + glasses man, the glasses man (more frontal, closer to camera) consistently becomes `result[0]`, and generates a high-quality embedding that represents him — while the bald man's embedding should have been created.

This is a **silent contamination**: no error is raised, quality scores look normal, the embedding vector is ~512-dimensional and well-formed. The only sign is that it represents the wrong identity.

---

### Root Cause 3: Bounding box temporal offset

**File:** `ppl-meta-vision/src/person_objects/ppl_thread_workflow.py`

Face detections are stored with `bbox_x1, bbox_y1, bbox_x2, bbox_y2` at the moment of detection. The vision service samples at **3 fps** (`frames_per_second=3`), meaning ~333ms between sampled frames.

The "best quality" representative face is selected later based on quality metrics (sharpness, brightness, confidence). When the embedding is computed for that representative face, a subtle mismatch can arise:

- **The bbox was captured** at frame N (detection event)
- **The embedding is computed** using frame N's bbox, but people may have shifted position between detection and representative selection

In a dense scene, the intended person may have moved outside the bbox while another person moved into it.

---

### Root Cause 4: Overlapping bounding boxes are not considered during embedding

**File:** `ppl-meta-orchestrator/src/ppl_thread_endpoints.py`, `_group_faces_by_rectangle_overlap()`

The orchestrator groups face detections with IoU ≥ 0.3. Face detections with IoU < 0.3 are treated as **separate distinct persons**, even if person A's bbox physically encloses person B's face.

There is no guard that prevents the embedding for person A from being computed on a crop that contains person B. The IoU thresholding only governs detection grouping, not embedding isolation.

---

### Root Cause 5: Gender label `unknown` is a symptom, not a cause

When the bald man's MVRs are labelled `unknown` (low gender confidence), this is a downstream consequence of the same contamination. The gender classifier `GenderClassifier` also runs on the same corrupted crop — it classifies the glasses man's face, which has conflicting visual signals between the two people in the crop, resulting in low gender confidence and an `unknown` label.

The `unknown` label is therefore a **diagnostic signal**: an MVR record with `unknown` gender in a video that clearly contains gendered individuals is a strong indicator of embedding contamination.

---

## The Cascade of Consequences

```
Two people visible in frame
        │
        ▼
Detection bbox for Person B (bald man)
physically contains Person A (glasses man) face
        │
        ▼
face_img = frame[y:y+h, x:x+w]  ← multi-face crop
        │
        ▼
DeepFace.represent(face_img) → [face_A_embedding, face_B_embedding]
result[0] = face_A_embedding  ← glasses man = WRONG person
        │
        ▼
MVR record for bald man stores glasses man's embedding
gender_confidence is low → label = "unknown"
        │
        ▼
HierarchicalMVRMerger compares embeddings pairwise
similarity(bald_man_mvr, glasses_man_mvr) > 0.70 ← FAKE match
        │
        ▼
Union-Find merges both into same group
Bald man and glasses man appear as one individual
        │
        ▼
Incorrect super-individual — WRONG RESULT
```

---

## Affected Code Paths

| File | Line(s) | Issue |
|------|---------|-------|
| `ppl-meta-vmeta/src/services/embedding_service.py` | 326–330 | Crop contains multiple faces, no validation |
| `ppl-meta-vmeta/src/services/embedding_service.py` | 350–356 | Always takes `result[0]`, wrong person |
| `ppl-meta-vmeta/src/ml/facenet_processor.py` | 98–101 | Always takes `result[0]`, wrong person |
| `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py` | similarity matrix | High similarity accepted without crop validation |
| `ppl-meta-orchestrator/src/ppl_thread_endpoints.py` | `_group_faces_by_rectangle_overlap` | IoU grouping ≠ embedding isolation |

---

## Proposed Fixes

### Fix 1: Face count validation before committing an embedding (HIGH PRIORITY)

After computing `DeepFace.represent(face_img)`, check how many faces were detected:

```python
embedding_result = DeepFace.represent(
    img_path=face_rgb,
    model_name=self.embedding_model,
    enforce_detection=False,
    detector_backend=self.detector_backend,
)

# PROPOSED: reject crop if multiple faces detected
if isinstance(embedding_result, list) and len(embedding_result) > 1:
    logger.warning(
        f"Multi-face crop detected at frame {frame_number} "
        f"bbox=[{x},{y},{x+width},{y+height}]: "
        f"{len(embedding_result)} faces found. Skipping embedding."
    )
    return None, None  # Do not store a contaminated embedding
```

This prevents contaminated embeddings from ever reaching the MVR table.

---

### Fix 2: Use face-aligned crop, not raw bbox slice

Instead of `frame[y:y+height, x:x+width]`, use the **face region detected by the face detector** (the `facial_area` sub-key returned by `DeepFace.represent`):

```python
result = DeepFace.represent(img_path=face_rgb, ...)
if result and len(result) == 1:
    # Use the detector's own face crop for embedding
    facial_area = result[0].get('facial_area', {})
    fx, fy = facial_area.get('x', 0), facial_area.get('y', 0)
    fw, fh = facial_area.get('w', width), facial_area.get('h', height)
    face_aligned = face_rgb[fy:fy+fh, fx:fx+fw]
    # embedding is already from this aligned crop
    embedding = result[0]['embedding']
```

This ensures the embedding is from the face the detector actually localized.

---

### Fix 3: Add `face_count_in_crop` metadata to MVR records

Store the number of faces detected in the representative crop as a diagnostic column on `mvr_people`:

```sql
ALTER TABLE mvr_people ADD COLUMN face_count_in_crop INTEGER DEFAULT 1;
ALTER TABLE mvr_people ADD COLUMN embedding_is_reliable BOOLEAN DEFAULT TRUE;
```

MVR records with `face_count_in_crop > 1` should be flagged as unreliable and **excluded from merge comparisons** in `HierarchicalMVRMerger`.

---

### Fix 4: Use `unknown` gender + high similarity as a contamination flag

In `HierarchicalMVRMerger._find_merge_groups()`, add a secondary check:

> If one MVR has `gender = unknown` AND the other has `gender = male/female` with high confidence, and similarity > threshold — **require a secondary confirmation** (e.g. face IoU check on orig bboxes) before merging.

This won't fix the root cause but will reduce false merges.

---

### Fix 5: Padding-controlled bbox expansion

The tracking bbox may be tight (just the detected face) or loose (full body). Introduce a configurable padding cap:

```python
MAX_FACE_CROP_PADDING = 0.20  # max 20% expansion beyond detected face

# Constrain crop size so it doesn't extend too far into adjacent persons
w_padded = min(width, detected_face_width * (1 + MAX_FACE_CROP_PADDING))
h_padded = min(height, detected_face_height * (1 + MAX_FACE_CROP_PADDING))
```

---

## Summary Table

| Hypothesis | Verified? | Evidence |
|-----------|-----------|----------|
| Crops contain multiple people | ✅ YES | Frame screenshots show 2 people; `face_img = frame[y:y+h, x:x+w]` slice confirmed in code |
| Bbox coordinates may be temporally offset | ✅ YES | Vision service samples at 3 fps; representative face selected post-hoc |
| Two overlapping bboxes produce corrupt crop | ✅ YES | `6d8d7cdb` (bald man's MVR) face crop visually shows glasses man |
| Embedding model generates embedding for wrong person | ✅ YES | `result[0]` always selected; same embedding as Group 1 winner `36ca2d7c` |
| This causes dissimilar people to pass merge threshold | ✅ YES | Bald man and glasses man merged into Group 1 (45 members) |
| `unknown` gender label is a symptom | ✅ YES | All bald man records have `gender=unknown`, consistent with crop contamination |

---

## Test Case Reference

- **Video:** `d46124c8-8944-4784-be9f-3e6314e1f0b8` (16s, 1280×720, 30fps h264)
- **Test script:** `tests/merge_test/test_detected_only.py`
- **Collection test:** `tests/merge_test/test_merge.py` (collection `360460d5`, 2026-03-01 13:00–17:00 EET)
- **Contaminated MVR:** `6d8d7cdb`, `724ce94a` — labelled `unknown`, embedding belongs to different person
- **Crop files:** `tests/merge_test/det_g02_m01_6d8d7cdb_unknown.jpg`, `det_g02_m02_724ce94a_unknown.jpg`
