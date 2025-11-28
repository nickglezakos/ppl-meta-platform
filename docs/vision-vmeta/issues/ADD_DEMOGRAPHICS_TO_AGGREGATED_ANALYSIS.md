# Issue: Add Demographics Data to Cross-Video Aggregated Analysis Endpoint

**Type:** Enhancement  
**Priority:** High  
**Component:** Backend API (vmeta service)  
**Affects:** Cross-Video Individual Analysis Screen (Frontend)

---

## Summary

The Cross-Video Individual Analysis endpoint (`/api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis`) currently does not include demographic data (gender, age) in its response, even though this data exists in the `mvr_people` table.

The Frontend Statistics tab requires:
- Gender breakdown (Men/Women counts)
- Average age
- Age confidence
- Gender confidence

---

## Current Behavior

### API Response (Missing Data)
```json
{
  "individual_uuid": "...",
  "total_appearances": 15,
  "unique_videos": 3,
  "average_confidence": 0.876,
  "total_duration_seconds": 3456.78,
  // ❌ NO DEMOGRAPHICS
}
```

### Database Query (Incomplete)
```sql
-- Current query does NOT join mvr_people table
SELECT
    iva.individual_uuid,
    i.individual_id,
    iva.video_uuid,
    iva.confidence
FROM individual_video_appearances iva
JOIN individuals i ON iva.individual_uuid = i.individual_uuid
WHERE iva.individual_uuid = $1
```

**Problem:** The query joins `individual_video_appearances` and `individuals` but skips `individual_mvr_mapping` and `mvr_people` tables where demographic data resides.

---

## Expected Behavior

### Enhanced API Response (With Demographics)
```json
{
  "individual_uuid": "...",
  "total_appearances": 15,
  "unique_videos": 3,
  "average_confidence": 0.876,
  "total_duration_seconds": 3456.78,
  
  // ✅ NEW: Demographics section
  "demographics": {
    "gender": "male",
    "gender_confidence": 0.89,
    "age_min": 28,
    "age_max": 35,
    "age_mean": 31.5,
    "age_confidence": 0.82
  },
  
  // ✅ NEW: Aggregate statistics
  "aggregate_demographics": {
    "total_individuals": 5,
    "gender_breakdown": {
      "male": 3,
      "female": 2,
      "unknown": 0
    },
    "age_statistics": {
      "average_age": 32.4,
      "min_age": 25,
      "max_age": 45,
      "age_range": 20
    }
  }
}
```

---

## Implementation Plan

### Phase 1: Basic Demographics (Required)

#### Step 1: Modify SQL Query

**For MVR Person UUID Input:**
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
    -- NEW: Add demographics from MVR people
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
    AND mvr.is_orphaned = FALSE  -- Exclude orphaned MVR records
WHERE imm.mvr_people_uuid = $1
ORDER BY iva.start_timestamp ASC
```

**For Individual UUID Input:**
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
    -- NEW: Add demographics from MVR people
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

**Key Changes:**
- ✅ Add `LEFT JOIN` with `individual_mvr_mapping` table
- ✅ Add `LEFT JOIN` with `mvr_people` table
- ✅ Filter out orphaned MVR records (`is_orphaned = FALSE`)
- ✅ Select gender, age, and confidence fields

#### Step 2: Update Response Model

**File:** `/ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`

Add to response dictionary:
```python
# Calculate demographics aggregates
demographics_data = []
for appearance in appearances:
    if appearance.get('gender'):
        demographics_data.append({
            'gender': appearance['gender'],
            'age_min': appearance['age_min'],
            'age_max': appearance['age_max'],
            'age_mean': (appearance['age_min'] + appearance['age_max']) / 2 if appearance['age_min'] and appearance['age_max'] else None
        })

# Aggregate demographics
gender_counts = {'male': 0, 'female': 0, 'unknown': 0}
ages = []

for demo in demographics_data:
    gender_counts[demo.get('gender', 'unknown')] += 1
    if demo.get('age_mean'):
        ages.append(demo['age_mean'])

response = {
    # ... existing fields ...
    
    # NEW: Add demographics section
    "demographics": {
        "gender": most_common_gender,
        "gender_confidence": average_gender_confidence,
        "age_min": min(age_min_values) if age_min_values else None,
        "age_max": max(age_max_values) if age_max_values else None,
        "age_mean": sum(ages) / len(ages) if ages else None,
        "age_confidence": average_age_confidence
    },
    
    # NEW: Aggregate statistics
    "aggregate_demographics": {
        "total_individuals": len(unique_individual_uuids),
        "gender_breakdown": {
            "male": gender_counts['male'],
            "female": gender_counts['female'],
            "unknown": gender_counts['unknown']
        },
        "age_statistics": {
            "average_age": sum(ages) / len(ages) if ages else None,
            "min_age": min(ages) if ages else None,
            "max_age": max(ages) if ages else None,
            "age_range": max(ages) - min(ages) if ages else None
        }
    }
}
```

#### Step 3: Update Frontend Model

**File:** `/ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`

```dart
class AggregatedIndividualAnalysis {
  final String individualUuid;
  final String individualId;
  final String sessionUuid;
  final int totalAppearances;
  final int uniqueVideos;
  final DateTime firstSeen;
  final DateTime lastSeen;
  final double totalDurationSeconds;
  final double averageConfidence;
  final List<IndividualAppearance> appearances;
  final List<String> personObjectUuids;
  final DateTime analysisTimestamp;
  
  // NEW: Demographics
  final Demographics? demographics;
  final AggregateDemographics? aggregateDemographics;

  // ... constructor and fromJson ...
}

class Demographics {
  final String? gender;
  final double? genderConfidence;
  final int? ageMin;
  final int? ageMax;
  final double? ageMean;
  final double? ageConfidence;

  Demographics({
    this.gender,
    this.genderConfidence,
    this.ageMin,
    this.ageMax,
    this.ageMean,
    this.ageConfidence,
  });

  factory Demographics.fromJson(Map<String, dynamic> json) {
    return Demographics(
      gender: json['gender'] as String?,
      genderConfidence: (json['gender_confidence'] as num?)?.toDouble(),
      ageMin: json['age_min'] as int?,
      ageMax: json['age_max'] as int?,
      ageMean: (json['age_mean'] as num?)?.toDouble(),
      ageConfidence: (json['age_confidence'] as num?)?.toDouble(),
    );
  }
}

class AggregateDemographics {
  final int totalIndividuals;
  final GenderBreakdown genderBreakdown;
  final AgeStatistics ageStatistics;

  AggregateDemographics({
    required this.totalIndividuals,
    required this.genderBreakdown,
    required this.ageStatistics,
  });

  factory AggregateDemographics.fromJson(Map<String, dynamic> json) {
    return AggregateDemographics(
      totalIndividuals: json['total_individuals'] as int,
      genderBreakdown: GenderBreakdown.fromJson(json['gender_breakdown']),
      ageStatistics: AgeStatistics.fromJson(json['age_statistics']),
    );
  }
}

class GenderBreakdown {
  final int male;
  final int female;
  final int unknown;

  GenderBreakdown({
    required this.male,
    required this.female,
    required this.unknown,
  });

  factory GenderBreakdown.fromJson(Map<String, dynamic> json) {
    return GenderBreakdown(
      male: json['male'] as int? ?? 0,
      female: json['female'] as int? ?? 0,
      unknown: json['unknown'] as int? ?? 0,
    );
  }
}

class AgeStatistics {
  final double? averageAge;
  final double? minAge;
  final double? maxAge;
  final double? ageRange;

  AgeStatistics({
    this.averageAge,
    this.minAge,
    this.maxAge,
    this.ageRange,
  });

  factory AgeStatistics.fromJson(Map<String, dynamic> json) {
    return AgeStatistics(
      averageAge: (json['average_age'] as num?)?.toDouble(),
      minAge: (json['min_age'] as num?)?.toDouble(),
      maxAge: (json['max_age'] as num?)?.toDouble(),
      ageRange: (json['age_range'] as num?)?.toDouble(),
    );
  }
}
```

#### Step 4: Update Frontend Statistics Display

**File:** `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

Add to `_buildStatisticsTabCrossVideo()` method:

```dart
// Gender breakdown section
if (analysis.aggregateDemographics != null) {
  final genderBreakdown = analysis.aggregateDemographics!.genderBreakdown;
  final totalWithGender = genderBreakdown.male + genderBreakdown.female;
  
  Wrap(
    spacing: 8.0,
    runSpacing: 8.0,
    children: [
      _buildStatChip(
        icon: Icons.male,
        label: 'Men',
        value: '${genderBreakdown.male}',
        subtitle: totalWithGender > 0 
          ? '${((genderBreakdown.male / totalWithGender) * 100).toStringAsFixed(1)}%'
          : 'N/A',
        color: Colors.blue,
      ),
      _buildStatChip(
        icon: Icons.female,
        label: 'Women',
        value: '${genderBreakdown.female}',
        subtitle: totalWithGender > 0
          ? '${((genderBreakdown.female / totalWithGender) * 100).toStringAsFixed(1)}%'
          : 'N/A',
        color: Colors.pink,
      ),
      if (genderBreakdown.unknown > 0)
        _buildStatChip(
          icon: Icons.help_outline,
          label: 'Unknown',
          value: '${genderBreakdown.unknown}',
          color: Colors.grey,
        ),
    ],
  ),
}

// Age statistics section
if (analysis.aggregateDemographics?.ageStatistics != null) {
  final ageStats = analysis.aggregateDemographics!.ageStatistics;
  
  if (ageStats.averageAge != null) {
    _buildStatChip(
      icon: Icons.cake,
      label: 'Average Age',
      value: '${ageStats.averageAge!.toStringAsFixed(1)} years',
      subtitle: ageStats.ageRange != null
        ? 'Range: ${ageStats.ageRange!.toStringAsFixed(0)} years'
        : null,
      color: Colors.orange,
    );
  }
}
```

---

### Phase 2: Enhanced Velocity Metrics (Optional)

Currently, velocity is calculated in the frontend as:
```dart
double velocity = totalAppearances / (totalDurationSeconds / 60);
```

**Enhancement Options:**

1. **Backend calculates velocity** (more accurate):
   - Calculate appearances per minute
   - Calculate spatial velocity (pixels/second)
   - Calculate movement entropy

2. **Keep frontend calculation** (simpler, current approach works):
   - No backend changes needed
   - Frontend has all necessary data

**Recommendation:** Keep frontend calculation for now unless more complex velocity metrics are needed.

---

## Database Schema Reference

### mvr_people Table
```sql
CREATE TABLE mvr_people (
    mvr_people_uuid UUID PRIMARY KEY,
    face_embedding vector(512) NOT NULL,
    
    -- Demographics (REQUIRED FOR THIS ISSUE)
    age_min INTEGER CHECK (age_min >= 0 AND age_min <= 120),
    age_max INTEGER CHECK (age_max >= 0 AND age_max <= 120),
    age_confidence FLOAT CHECK (age_confidence >= 0.0 AND age_confidence <= 1.0),
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'unknown')),
    gender_confidence FLOAT CHECK (gender_confidence >= 0.0 AND gender_confidence <= 1.0),
    
    -- Tracking
    featured_individual_uuid UUID NOT NULL,
    is_orphaned BOOLEAN DEFAULT FALSE,
    quality_score FLOAT NOT NULL,
    ...
);
```

### individual_mvr_mapping Table
```sql
CREATE TABLE individual_mvr_mapping (
    mapping_uuid UUID PRIMARY KEY,
    individual_uuid UUID REFERENCES individuals(individual_uuid),
    mvr_people_uuid UUID REFERENCES mvr_people(mvr_people_uuid),
    mapping_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(individual_uuid, mvr_people_uuid)
);
```

---

## Edge Cases to Handle

### 1. Individual Without MVR Mapping
- Some individuals may not have MVR people records
- Use `LEFT JOIN` to handle missing data
- Return `null` for demographics fields

### 2. Multiple Individuals → Single MVR Person
- Multiple video individuals can map to same MVR person
- Aggregate statistics should handle this correctly
- Use DISTINCT when counting individuals

### 3. Orphaned MVR Records
- Filter out orphaned records: `WHERE mvr.is_orphaned = FALSE`
- Orphaned records are low-quality or deprecated

### 4. Missing Age/Gender Data
- Some MVR records may have null age or gender
- Frontend should gracefully handle null values
- Display "N/A" or hide section if no data

---

## Testing Requirements

### Backend Tests
- [ ] Test endpoint with MVR person UUID (has demographics)
- [ ] Test endpoint with individual UUID (has demographics)
- [ ] Test endpoint with individual UUID (no demographics)
- [ ] Test endpoint with multiple individuals mapping to same MVR person
- [ ] Verify orphaned MVR records are excluded
- [ ] Verify backward compatibility (existing clients still work)
- [ ] Test aggregation logic (gender counts, average age)

### Frontend Tests
- [ ] Parse new demographics fields from API response
- [ ] Display gender breakdown correctly
- [ ] Display average age correctly
- [ ] Handle missing demographics gracefully
- [ ] Verify percentages calculate correctly
- [ ] Test with various data scenarios (all male, all female, mixed, unknown)

---

## Breaking Changes

**Risk Level:** ✅ **LOW** (Additive change only)

- Adding new fields to response is backward-compatible
- Existing clients ignore unknown fields
- No existing fields are modified or removed

---

## Performance Impact

**Impact Level:** ✅ **MINIMAL**

- Adding `LEFT JOIN` with `mvr_people` table
- Tables are already indexed on join keys
- Additional fields are small (strings, integers, floats)
- No significant query performance degradation expected

**Estimated Query Time Increase:** < 5ms

---

## Related Files

### Backend
- `/ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py:3384`
  - Function: `get_individual_aggregated_analysis()`
- `/ppl-meta-vmeta/migrations/002_mvr_people_schema.sql`
  - Schema with demographics fields

### Frontend
- `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart:4629`
  - Method: `_buildStatisticsTabCrossVideo()`
- `/ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`
  - Model: `AggregatedIndividualAnalysis`

### Documentation
- `/docs/vision-vmeta/CROSS_VIDEO_ANALYSIS_API_DATA_FLOW.md`
  - Complete data flow documentation

---

## Acceptance Criteria

### Backend
- [x] SQL query modified to JOIN `individual_mvr_mapping` and `mvr_people`
- [x] Response includes `demographics` object with gender/age
- [x] Response includes `aggregate_demographics` with counts and statistics
- [x] Orphaned MVR records are filtered out
- [x] Handles missing demographics gracefully (null values)
- [x] Backward compatible with existing clients
- [x] Unit tests pass
- [x] Integration tests pass

### Frontend
- [x] Data model updated to include demographics fields
- [x] Gender breakdown displayed in Statistics tab (Men/Women/Unknown)
- [x] Average age displayed in Statistics tab
- [x] Percentages calculated correctly
- [x] Handles missing data gracefully (shows "N/A" or hides)
- [x] UI tests pass

---

## Priority Justification

**Priority:** 🔴 **HIGH**

**Reasons:**
1. **User Request:** Explicit feature request for gender/age statistics
2. **Data Exists:** All required data is in database but not fetched
3. **Low Risk:** Additive change only, minimal breaking risk
4. **High Value:** Significant UX improvement for analytics screen
5. **Quick Win:** Estimated 4-8 hours of development time

---

## Estimated Effort

**Backend:** 3-4 hours
- Modify SQL query: 1 hour
- Update response model: 1 hour
- Testing: 1-2 hours

**Frontend:** 2-4 hours
- Update data model: 1 hour
- Update UI display: 1 hour
- Testing: 1-2 hours

**Total Estimated Time:** 5-8 hours

---

## Additional Notes

- Current implementation already handles MVR person UUID vs. individual UUID correctly
- The `individual_mvr_mapping` table exists and is populated
- Demographics data quality depends on Vision AI accuracy
- Consider adding confidence thresholds for filtering low-quality data
- Future enhancement: Add demographic filtering/sorting in UI

---

**Issue Status:** 🟡 Open  
**Created:** November 28, 2025  
**Author:** PPL Meta Development Team  
**Labels:** enhancement, backend, frontend, high-priority, analytics
