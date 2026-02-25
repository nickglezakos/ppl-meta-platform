# Vision + VMeta JSON Objects (OpenSpec Extract)

This document lists the JSON objects for:
1. Face detections
2. Individual objects (person objects)
3. MVR people
4. Super individuals
5. MVR people analytics with routes

The shapes below are derived from the Vision and VMeta OpenSpec sources in this repo.

---

## 1) Face detections (Vision)

### FaceDetection
```json
{
  "face_id": "b1e7a2c6-4a0e-4f5c-9a7e-42d7b0a21b3e",
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "frame_number": 42,
  "timestamp": 1.4,
  "bbox": [100, 200, 300, 400],
  "confidence": 0.95,
  "method": "enhanced_logic_v2",
  "created_at": "2025-10-25T18:25:01.237726"
}
```

---

## 2) Individual objects (Vision person objects)

### PersonObject
```json
{
  "person_uuid": "uuid-1",
  "person_id": "person_1",
  "face_count": 15,
  "representative_faces": ["face_1", "face_7"],
  "all_face_ids": ["face_1", "face_2", "face_3", "face_7"],
  "average_confidence": 0.85,
  "quality_metrics": {
    "quality_score": 0.82,
    "best_face_id": "face_7"
  }
}
```

### GroupTrackingItem
```json
{
  "Merged_Group_ID": "person_1",
  "Original_Group_IDs": ["face_1", "face_3", "face_7"],
  "Face_Count": 3,
  "Average_Position": {"x": 245.5, "y": 156.2},
  "Y_Coordinate_Based": false,
  "Tracking_Based": true,
  "Tolerance_Percent": 20.0,
  "Merge_History": []
}
```

---

## 3) MVR people (VMeta)

### MVRPeople
```json
{
  "mvr_people_uuid": "b24ad688-26f0-4e1e-9484-4fecec18df9c",
  "status": "completed",
  "face_embedding": {
    "vector": [0.001, -0.014, 0.082, 0.112],
    "model_name": "facenet_512",
    "model_version": "1.0.0"
  },
  "age_estimate": {
    "min_age": 25,
    "max_age": 35,
    "mean_age": 29.8,
    "confidence": 0.86,
    "model_name": "age_estimator_v1",
    "model_version": "1.0.0"
  },
  "gender_estimate": {
    "gender": "male",
    "confidence": 0.91,
    "model_name": "gender_classifier_v1",
    "model_version": "1.0.0"
  },
  "representative_individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "representative_face_uuid": "2c8f6f52-1db8-4d74-9d1b-1b6f7f6b7a21",
  "quality_score": 0.88,
  "total_linked_individuals": 2,
  "linked_individuals": [
    {
      "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
      "is_representative": true,
      "linked_at": "2025-10-25T18:25:01.237726",
      "confidence_score": 0.92
    }
  ],
  "is_orphaned": false,
  "orphaned_at": null,
  "merged_into_mvr_uuid": null,
  "created_at": "2025-10-25T18:25:01.237726",
  "updated_at": "2025-10-25T18:25:01.237726"
}
```

---

## 4) Super individuals (VMeta hierarchical merge)

### SuperIndividualHierarchy
```json
{
  "super_individual": {
    "mvr_people_uuid": "11111111-2222-3333-4444-555555555555",
    "status": "completed",
    "quality_score": 0.93,
    "is_orphaned": false,
    "merged_into_mvr_uuid": null
  },
  "merged_mvr_people": [
    {
      "mvr_people_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      "quality_score": 0.81,
      "is_orphaned": true,
      "merged_into_mvr_uuid": "11111111-2222-3333-4444-555555555555"
    }
  ],
  "all_individuals": [
    {
      "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
      "mvr_people_uuid": "11111111-2222-3333-4444-555555555555",
      "video_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
      "person_object_uuid": "9fcd0d67-acb0-41ba-ab51-55e610f1f603",
      "first_seen_timestamp": "2025-10-19T13:05:00Z",
      "last_seen_timestamp": "2025-10-19T13:05:30Z",
      "confidence": 0.85
    }
  ],
  "total_person_objects": 12,
  "mvr_count": 3,
  "unique_videos": 2
}
```

---

## 5) MVR people analytics with routes (VMeta)

### MVRPeopleAnalyticsWithRoutes
```json
{
  "collection_name": "usb_camera_0",
  "start_time": "2026-02-12T13:00:00Z",
  "end_time": "2026-02-12T14:00:00Z",
  "tracking_sessions_count": 1,
  "total_individuals": 4,
  "total_mvr_people": 3,
  "total_videos_processed": 2,
  "mvr_with_quality": 3,
  "mvr_without_quality": 0,
  "total_quality_scores": 3,
  "average_quality": 0.86,
  "min_quality": 0.81,
  "max_quality": 0.92,
  "quality_std_dev": 0.045,
  "data_completeness": {
    "total_mvr_people": 3,
    "mvr_with_quality_scores": 3,
    "percentage": 100.0
  },
  "routes": {
    "total_routes": 2,
    "total_route_points": 5,
    "unique_persons": 2,
    "time_range_start": "2026-02-12T13:00:00Z",
    "time_range_end": "2026-02-12T14:00:00Z",
    "routes": [
      {
        "x": 120.5,
        "y": 240.8,
        "timestamp": "2026-02-12T13:05:05Z",
        "video_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
        "confidence": 0.93,
        "velocity": null
      },
      {
        "x": 130.2,
        "y": 238.1,
        "timestamp": "2026-02-12T13:05:06Z",
        "video_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
        "confidence": 0.91,
        "velocity": 0.012345
      }
    ],
    "spatial_analysis": {
      "heatmap_cells": [],
      "movement_statistics": {
        "total_distance": 0.0,
        "average_velocity": 0.0,
        "time_in_frame": 0.0
      }
    }
  }
}
```
