# Average Face Quality Analytics Endpoint

## Overview

New analytics endpoint that calculates the average image quality of individual data objects filtered by camera/collection and time range.

**Endpoint**: `GET /api/v1/analytics/quality-metrics`

**Location**: Gateway service (proxies to vmeta service)

**Purpose**: Provides quality metrics for the analytics dashboard at `http://localhost:3000/#/analytics`

---

## API Specification

### Gateway Endpoint

**URL**: `GET http://localhost:8080/api/v1/analytics/quality-metrics`

**Authentication**: Required (JWT Bearer token)

**Query Parameters**:
- `time_filter` (string, default: "today") - Time period filter
  - Options: `today`, `last_3_days`, `last_week`, `last_month`
- `collection_ids` (string, optional) - Comma-separated collection IDs
  - Example: `"camera1,camera2"`
  - If omitted, returns metrics for all collections

**Response**:
```json
{
  "time_filter": "today",
  "start_time": "2026-01-05T00:00:00",
  "end_time": "2026-01-05T14:30:00",
  "total_individuals": 156,
  "active_collections": 3,
  "overall_average_quality": 0.72,
  "quality_grade": "Good",
  "collection_breakdown": [
    {
      "collection_name": "Front Entrance",
      "average_quality": 0.85,
      "individual_count": 45,
      "min_quality": 0.62,
      "max_quality": 0.94,
      "quality_std_dev": 0.08
    },
    {
      "collection_name": "Lobby Camera",
      "average_quality": 0.68,
      "individual_count": 78,
      "min_quality": 0.42,
      "max_quality": 0.89,
      "quality_std_dev": 0.12
    },
    {
      "collection_name": "Exit Camera",
      "average_quality": 0.63,
      "individual_count": 33,
      "min_quality": 0.38,
      "max_quality": 0.81,
      "quality_std_dev": 0.11
    }
  ],
  "generated_at": "2026-01-05T14:30:15.123Z"
}
```

---

## Backend Architecture

### vmeta Service Endpoint

**URL**: `GET http://localhost:8008/api/v1/individuals/quality-metrics`

**Query Parameters**:
- `collection_name` (string, required) - Collection name to filter
- `start_time` (datetime, required) - Start time (ISO format)
- `end_time` (datetime, required) - End time (ISO format)

**Process Flow**:

1. **Query Individuals**: Retrieves individual_video_appearances from database filtered by time range
2. **Extract Video UUIDs**: Gets unique video UUIDs from appearances
3. **Filter by Collection**: Queries media service to verify which videos belong to target collection
4. **Extract Quality Scores**: Parses `representative_faces` JSONB field to extract face quality scores
5. **Calculate Statistics**: Computes average, min, max, and standard deviation

**Quality Score Extraction**:

The `representative_faces` JSONB field contains face data with quality scores:

```json
{
  "faces": [
    {
      "face_id": "face_001",
      "quality_score": 0.85,
      "bbox": [100, 200, 150, 250],
      "confidence": 0.92
    },
    {
      "face_id": "face_002",
      "quality_score": 0.78,
      "bbox": [110, 205, 155, 255],
      "confidence": 0.89
    }
  ]
}
```

**Normalization**: Quality scores are normalized to 0-1 range (if score > 1.0, divide by 100)

---

## Quality Grading System

The endpoint provides a quality grade based on the average quality score:

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 0.80 - 1.00 | Excellent | High-quality face detections, optimal conditions |
| 0.60 - 0.79 | Good | Acceptable quality, usable for identification |
| 0.40 - 0.59 | Fair | Moderate quality, may have lighting/angle issues |
| 0.20 - 0.39 | Poor | Low quality, limited usability |
| 0.00 - 0.19 | Very Poor | Very low quality, likely unusable |

---

## Usage Examples

### Get Quality Metrics for Today (All Collections)

```bash
curl -X GET "http://localhost:8080/api/v1/analytics/quality-metrics?time_filter=today" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Quality Metrics for Specific Collections (Last Week)

```bash
curl -X GET "http://localhost:8080/api/v1/analytics/quality-metrics?time_filter=last_week&collection_ids=Front%20Entrance,Lobby%20Camera" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Integration with Analytics Dashboard

The endpoint uses the same filtering mechanism as other analytics endpoints:

1. **Time Filters**: Consistent with `/analytics/summary`, `/analytics/demographics`, `/analytics/behavioral`
2. **Collection Filtering**: Same `collection_ids` parameter format
3. **Authentication**: Standard JWT token authentication
4. **Response Format**: Consistent structure with other analytics endpoints

### Frontend Integration

Add to Flutter analytics screen:

```dart
Future<Map<String, dynamic>> getQualityMetrics({
  required String timeFilter,
  List<String>? collectionIds,
}) async {
  final queryParams = <String, dynamic>{
    'time_filter': timeFilter,
  };
  
  if (collectionIds != null && collectionIds.isNotEmpty) {
    queryParams['collection_ids'] = collectionIds.join(',');
  }
  
  final response = await _apiClient.get(
    '/api/v1/analytics/quality-metrics',
    queryParameters: queryParams,
  );
  
  return response.data as Map<String, dynamic>;
}
```

---

## Database Schema

### Tables Used

**individuals**
- `individual_uuid` (UUID) - Primary key
- `created_at` (timestamp)
- `updated_at` (timestamp)

**individual_video_appearances**
- `individual_uuid` (UUID) - Foreign key to individuals
- `video_uuid` (UUID) - Reference to video in media service
- `start_timestamp` (timestamp) - Appearance start time
- `confidence` (float) - Confidence score
- `representative_faces` (JSONB) - Face data including quality scores

---

## Quality Score Sources

Quality scores come from the Vision service's face detection system and are based on:

- **Sharpness** (35% weight) - Focus and clarity
- **Exposure** (25% weight) - Lighting conditions
- **Contrast** (20% weight) - Detail visibility
- **Noise** (10% weight) - Image noise level
- **Face Size** (10% weight) - Face area in pixels

These are calculated by the `PersonQualityAnalyzer` in `ppl-meta-vision/src/person_objects/quality_analyzer.py`.

---

## Minimum Face Quality Threshold

Related setting: **Minimum Face Quality for MVR People Creation** (defaults to 20%)

- Located at: `http://localhost:3000/#/settings` → Workflow Settings → Face Detection section
- **Purpose**: Filters out low-quality faces during MVR-People creation
- **Effect**: Faces with quality < threshold do NOT participate in MVR people creation
- **Default**: 0.20 (20%)
- **Range**: 0.0 to 1.0 (0% to 100%)

This endpoint provides visibility into the actual quality distribution across collections, helping users understand if they need to adjust the threshold or improve camera conditions.

---

## Implementation Files

### Backend
- **Gateway**: `/ppl-meta-gateway/src/api/v1/analytics.py` (lines 1085+)
  - Function: `get_quality_metrics()`
  - Helper: `_get_quality_grade()`

- **vmeta Service**: `/ppl-meta-vmeta/src/api/v1/quality_metrics.py`
  - Function: `get_individuals_quality_metrics()`
  - Router registered in: `/ppl-meta-vmeta/src/main.py`

### Database
- **Schema**: `/ppl-meta-vmeta/src/database/migrations/002_cross_video_tracking_schema.sql`
  - Table: `individuals`
  - Table: `individual_video_appearances`

---

## Version

**Added in**: Version 2.22.3
**Date**: January 5, 2026
**Author**: PPL Meta Platform Team
