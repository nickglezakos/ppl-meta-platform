# Cross-Video Analysis API Data Flow Documentation

**Version:** 2.19.40  
**Date:** November 28, 2025  
**Endpoint:** `GET /api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis`

## Overview

This document describes the exact data flow and structure for the Cross-Video Individual Analysis screen in the Flutter frontend. It details what data is currently fetched, what is displayed, and what data is missing.

---

## API Endpoint Details

### Request

```
GET /api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis?session_uuid={session_uuid}
```

**Parameters:**
- `individual_uuid` (path): UUID of the individual OR MVR person UUID
- `session_uuid` (query): UUID of the tracking session

**Authentication:** Required (Bearer token in headers)

---

## Current Implementation

### Database Queries Executed

The endpoint performs the following queries:

#### 1. Session Validation
```sql
SELECT status FROM tracking_sessions
WHERE session_uuid = $1
```

#### 2. MVR Person Check
```sql
SELECT mvr_people_uuid FROM mvr_people
WHERE mvr_people_uuid = $1
```

#### 3A. If MVR Person UUID - Get All Mapped Individuals
```sql
SELECT
    iva.individual_uuid,
    i.individual_id,
    iva.video_uuid,
    iva.person_object_uuid,
    iva.start_timestamp,
    iva.end_timestamp,
    iva.entry_bbox,
    iva.exit_bbox,
    iva.confidence
FROM individual_mvr_mapping imm
JOIN individual_video_appearances iva
    ON imm.individual_uuid = iva.individual_uuid
JOIN individuals i
    ON iva.individual_uuid = i.individual_uuid
WHERE imm.mvr_people_uuid = $1
ORDER BY iva.start_timestamp ASC
```

#### 3B. If Individual UUID - Get Direct Appearances
```sql
SELECT
    iva.individual_uuid,
    i.individual_id,
    iva.video_uuid,
    iva.person_object_uuid,
    iva.start_timestamp,
    iva.end_timestamp,
    iva.entry_bbox,
    iva.exit_bbox,
    iva.confidence
FROM individual_video_appearances iva
JOIN individuals i
    ON iva.individual_uuid = i.individual_uuid
WHERE iva.individual_uuid = $1
ORDER BY iva.start_timestamp ASC
```

### Data Returned (Current)

**Response Structure:**
```json
{
  "individual_uuid": "uuid-string",
  "individual_id": "ind_12345678",
  "session_uuid": "session-uuid",
  "total_appearances": 15,
  "unique_videos": 3,
  "first_seen": "2025-11-24T11:24:00.000Z",
  "last_seen": "2025-11-28T11:24:00.000Z",
  "total_duration_seconds": 3456.78,
  "average_confidence": 0.876,
  "appearances": [
    {
      "individual_uuid": "uuid",
      "video_uuid": "video-uuid",
      "person_object_uuid": "person-object-uuid",
      "start_timestamp": "2025-11-24T11:24:00.000Z",
      "end_timestamp": "2025-11-24T11:25:30.000Z",
      "entry_bbox": [x, y, w, h],
      "exit_bbox": [x, y, w, h],
      "confidence_score": 0.92
    }
  ],
  "person_object_uuids": ["uuid1", "uuid2", ...],
  "analysis_timestamp": "2025-11-28T14:30:00.000Z"
}
```

---

## Flutter Frontend Usage

### Data Displayed in UI

#### Statistics Tab
- ✅ Total Individuals
- ✅ Total Appearances (`total_appearances`)
- ✅ Unique Videos (`unique_videos`)
- ✅ Average Confidence (`average_confidence * 100%`)
- ✅ Average Velocity (calculated: `appearances / (duration / 60)` app/min)
- ✅ Total Duration (`total_duration_seconds` formatted as days/hours/minutes)
- ✅ Time Span (calculated: `last_seen - first_seen` in days)
- ✅ First Appearance (`first_seen` formatted)
- ✅ Last Appearance (`last_seen` formatted)

#### Routes Tab
- ✅ Individual appearances grouped by video
- ✅ Timestamps for each appearance
- ✅ Bounding boxes (`entry_bbox`, `exit_bbox`)
- ✅ Confidence scores

#### Individuals Tab
- ✅ List of all individuals
- ✅ Individual UUID and ID
- ✅ Total appearances per individual
- ✅ Videos per individual
- ✅ Confidence per individual
- ✅ Duration per individual

#### Vision Tab
- ⚠️ Placeholder for face images (not yet implemented)

---

## Missing Data

### ❌ Data NOT Currently Fetched

The following data exists in the `mvr_people` table but is **NOT** included in the API response:

#### 1. Gender Information
**Database Fields Available:**
```sql
gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'unknown'))
gender_confidence FLOAT CHECK (gender_confidence >= 0.0 AND gender_confidence <= 1.0)
```

**What's Missing:**
- Gender classification (male/female/unknown)
- Gender confidence score
- Breakdown: Number of men vs. women in the analysis

#### 2. Age Information
**Database Fields Available:**
```sql
age_min INTEGER CHECK (age_min >= 0 AND age_min <= 120)
age_max INTEGER CHECK (age_max >= 0 AND age_max <= 120)
age_confidence FLOAT CHECK (age_confidence >= 0.0 AND age_confidence <= 1.0)
```

**What's Missing:**
- Age range estimate (min/max)
- Average age across all individuals
- Age confidence score

#### 3. Velocity Information
**What's Missing:**
- Pre-calculated velocity metrics
- Movement patterns
- Spatial coverage data

**Current Workaround:** Frontend calculates velocity as `appearances / (duration_seconds / 60)` but this is a simplistic metric.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Flutter Frontend                                             │
│ Cross-Video Individual Analysis Screen                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ GET /aggregated-analysis?session_uuid=...
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ vmeta API Endpoint                                          │
│ /api/v1/cross-video/.../aggregated-analysis                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Queries PostgreSQL
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Database Tables (Current)                                   │
│                                                             │
│  ✅ tracking_sessions                                       │
│  ✅ individuals                                             │
│  ✅ individual_video_appearances                            │
│  ✅ individual_mvr_mapping                                  │
│  ❌ mvr_people (NOT JOINED - Missing gender/age)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Required Query Modification

To include gender and age data, the query needs to JOIN with `mvr_people`:

### Proposed Enhanced Query (Option A - For MVR Person UUID)

```sql
SELECT
    iva.individual_uuid,
    i.individual_id,
    iva.video_uuid,
    iva.person_object_uuid,
    iva.start_timestamp,
    iva.end_timestamp,
    iva.entry_bbox,
    iva.exit_bbox,
    iva.confidence,
    -- NEW: Add MVR people demographics
    mvr.gender,
    mvr.gender_confidence,
    mvr.age_min,
    mvr.age_max,
    mvr.age_confidence
FROM individual_mvr_mapping imm
JOIN individual_video_appearances iva
    ON imm.individual_uuid = iva.individual_uuid
JOIN individuals i
    ON iva.individual_uuid = i.individual_uuid
LEFT JOIN mvr_people mvr
    ON imm.mvr_people_uuid = mvr.mvr_people_uuid
WHERE imm.mvr_people_uuid = $1
  AND mvr.is_orphaned = FALSE
ORDER BY iva.start_timestamp ASC
```

### Proposed Enhanced Query (Option B - For Individual UUID)

```sql
SELECT
    iva.individual_uuid,
    i.individual_id,
    iva.video_uuid,
    iva.person_object_uuid,
    iva.start_timestamp,
    iva.end_timestamp,
    iva.entry_bbox,
    iva.exit_bbox,
    iva.confidence,
    -- NEW: Add MVR people demographics
    mvr.gender,
    mvr.gender_confidence,
    mvr.age_min,
    mvr.age_max,
    mvr.age_confidence
FROM individual_video_appearances iva
JOIN individuals i
    ON iva.individual_uuid = i.individual_uuid
LEFT JOIN individual_mvr_mapping imm
    ON iva.individual_uuid = imm.individual_uuid
LEFT JOIN mvr_people mvr
    ON imm.mvr_people_uuid = mvr.mvr_people_uuid
    AND mvr.is_orphaned = FALSE
WHERE iva.individual_uuid = $1
ORDER BY iva.start_timestamp ASC
```

---

## Enhanced Response Structure (Proposed)

```json
{
  "individual_uuid": "uuid-string",
  "individual_id": "ind_12345678",
  "session_uuid": "session-uuid",
  "total_appearances": 15,
  "unique_videos": 3,
  "first_seen": "2025-11-24T11:24:00.000Z",
  "last_seen": "2025-11-28T11:24:00.000Z",
  "total_duration_seconds": 3456.78,
  "average_confidence": 0.876,
  
  // NEW: Demographics from MVR people
  "demographics": {
    "gender": "male",
    "gender_confidence": 0.89,
    "age_min": 28,
    "age_max": 35,
    "age_mean": 31.5,
    "age_confidence": 0.82
  },
  
  // NEW: Movement metrics
  "movement_metrics": {
    "average_velocity": 2.5,  // appearances per minute
    "spatial_coverage": 0.65,  // percentage of frame covered
    "movement_entropy": 0.42   // randomness of movement
  },
  
  "appearances": [
    {
      "individual_uuid": "uuid",
      "video_uuid": "video-uuid",
      "person_object_uuid": "person-object-uuid",
      "start_timestamp": "2025-11-24T11:24:00.000Z",
      "end_timestamp": "2025-11-24T11:25:30.000Z",
      "entry_bbox": [x, y, w, h],
      "exit_bbox": [x, y, w, h],
      "confidence_score": 0.92,
      
      // NEW: Per-appearance demographics (if available)
      "gender": "male",
      "age_estimate": 31
    }
  ],
  "person_object_uuids": ["uuid1", "uuid2", ...],
  "analysis_timestamp": "2025-11-28T14:30:00.000Z"
}
```

---

## Frontend Display (With Enhanced Data)

### Statistics Tab (Enhanced)

#### Demographics Section (NEW)
- 👨 Men: [count] ([percentage]%)
- 👩 Women: [count] ([percentage]%)
- ❓ Unknown: [count] ([percentage]%)
- 📅 Average Age: [age_mean] years (±[age_range])
- ✓ Age Confidence: [age_confidence * 100]%
- ✓ Gender Confidence: [gender_confidence * 100]%

#### Performance Metrics (Enhanced)
- 🏃 Average Velocity: [velocity] appearances/min
- 📍 Spatial Coverage: [coverage]%
- 🔀 Movement Entropy: [entropy]

---

## Implementation Priority

### Phase 1: Add Demographics (HIGH PRIORITY)
1. Modify SQL query to JOIN `mvr_people` table
2. Add `demographics` object to API response
3. Update Flutter model to include demographics
4. Display gender breakdown and average age in Statistics tab

### Phase 2: Enhanced Velocity Metrics (MEDIUM PRIORITY)
1. Calculate velocity per appearance
2. Add spatial coverage calculation
3. Add movement entropy metric
4. Display in Statistics tab

### Phase 3: Per-Appearance Demographics (LOW PRIORITY)
1. Include demographics in each appearance object
2. Allow filtering by age/gender
3. Add demographic visualization in Vision tab

---

## Related Files

**Backend:**
- `/ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py:3384`
  - Function: `get_individual_aggregated_analysis()`
- `/ppl-meta-vmeta/migrations/002_mvr_people_schema.sql`
  - Schema with gender/age fields

**Frontend:**
- `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
  - Lines 4629-4750: `_buildStatisticsTabCrossVideo()`
- `/ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`
  - Model: `AggregatedIndividualAnalysis`

**Database Tables:**
- `mvr_people` - Contains gender and age estimates
- `individual_mvr_mapping` - Links individuals to MVR people
- `individual_video_appearances` - Appearance timeline data
- `individuals` - Individual metadata
- `tracking_sessions` - Session context

---

## Testing Checklist

### Backend Changes
- [ ] Modify SQL query to include MVR demographics
- [ ] Add demographics to response model
- [ ] Test with MVR person UUID
- [ ] Test with individual UUID  
- [ ] Test with individuals without MVR mapping
- [ ] Verify backward compatibility

### Frontend Changes
- [ ] Update `AggregatedIndividualAnalysis` model
- [ ] Parse demographics from API response
- [ ] Display gender breakdown in Statistics tab
- [ ] Display average age in Statistics tab
- [ ] Handle missing/null demographics gracefully
- [ ] Test with real data

---

## Notes

- Current implementation works correctly for appearance data
- Gender and age data exists in database but is not fetched
- Frontend currently shows placeholders or calculated estimates
- Breaking change risk: LOW (additive change only)
- Performance impact: MINIMAL (single additional JOIN)

---

**Document Status:** ✅ Complete  
**Last Updated:** November 28, 2025  
**Author:** PPL Meta Development Team
