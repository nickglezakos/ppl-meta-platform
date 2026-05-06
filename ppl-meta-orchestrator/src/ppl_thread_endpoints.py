"""
PPL Meta Orchestrator - PPL Thread (Person Objects) Endpoints
Provides centralized PPL Thread workflow management and data retrieval.
Enhanced with detailed person groups, quality scoring, and route tracking.
"""

import logging
import math
import uuid
import json
from datetime import datetime
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from workflow_orchestrator import (
    CameraFaceDetectionWorkflowOrchestrator,
    ServiceClientManager,
    TraceabilityContext,
)

logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer()


def get_auth_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract and validate authentication token."""
    return credentials.credentials


# Create router for PPL Thread endpoints
ppl_thread_router = APIRouter(prefix="/person-objects", tags=["person-objects"])


class PPLThreadWorkflowRequest(BaseModel):
    """Request model for PPL Thread workflow."""

    media_id: str


class PPLThreadPersonGroup(BaseModel):
    """Individual person group with detailed face data and analytics."""

    person_uuid: str
    person_id: str
    face_count: int
    representative_faces: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # Top 3 faces with quality scores
    all_face_ids: List[str] = Field(default_factory=list)
    average_confidence: float = 0.0
    spatial_bounds: Dict[str, float] = Field(
        default_factory=dict
    )  # min/max coordinates across all faces
    temporal_span: Dict[str, Any] = Field(
        default_factory=dict
    )  # start_frame, end_frame, duration
    movement_tracking: Dict[str, Any] = Field(
        default_factory=dict
    )  # route points and velocity data
    quality_metrics: Dict[str, Any] = Field(
        default_factory=dict
    )  # selection criteria and scoring
    demographics: Dict[str, Any] = Field(
        default_factory=dict
    )  # normalized age/gender evidence for the single-video group


class PPLThreadWorkflowResponse(BaseModel):
    """Enhanced response model for PPL Thread workflow with detailed person groups."""

    success: bool
    media_id: str
    total_persons: int
    total_faces: int
    status: str
    message: str
    person_groups: List[PPLThreadPersonGroup] = Field(default_factory=list)
    grouping_algorithm: str = "rectangle_overlap_detection"
    iou_threshold: float = 0.3
    processing_time_ms: float = 0.0
    session_uuid: str = ""
    routes_data: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # Movement tracking data


class PPLThreadEndpoints:
    """PPL Thread workflow management endpoints."""

    def __init__(
        self,
        orchestrator: CameraFaceDetectionWorkflowOrchestrator,
        service_manager: ServiceClientManager,
    ):
        self.orchestrator = orchestrator
        self.service_manager = service_manager
        self._setup_routes()

    def _calculate_iou(self, bbox1, bbox2):
        """
        Calculate Intersection over Union (IoU) for two bounding boxes.

        Args:
            bbox1, bbox2: [x1, y1, x2, y2] format bounding boxes

        Returns:
            float: IoU value between 0 and 1
        """
        # Calculate intersection coordinates
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        # No intersection if coordinates are invalid
        if x1 >= x2 or y1 >= y2:
            return 0.0

        # Calculate intersection area
        intersection_area = (x2 - x1) * (y2 - y1)

        # Calculate union area
        bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        bbox2_area = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union_area = bbox1_area + bbox2_area - intersection_area

        # Avoid division by zero
        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    def _group_faces_by_rectangle_overlap(self, face_bboxes, iou_threshold=0.3):
        """
        Group face bounding boxes using rectangle overlap detection with Union-Find.

        Args:
            face_bboxes: List of [x1, y1, x2, y2] bounding boxes
            iou_threshold: IoU threshold for considering faces as overlapping

        Returns:
            int: Number of distinct person groups
        """
        if not face_bboxes:
            return 0

        n = len(face_bboxes)
        if n == 1:
            return 1

        # Union-Find data structure
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Check all pairs for overlap
        for i in range(n):
            for j in range(i + 1, n):
                iou = self._calculate_iou(face_bboxes[i], face_bboxes[j])
                if iou >= iou_threshold:
                    union(i, j)

        # Count distinct groups
        groups = set(find(i) for i in range(n))
        return len(groups)

    def _extract_face_groups(self, face_bboxes, faces_data):
        """Extract face groups using Union-Find results."""
        if not face_bboxes or not faces_data:
            return {}

        n = len(face_bboxes)
        if n != len(faces_data):
            logger.warning(
                f"Mismatch between bboxes ({n}) and face data ({len(faces_data)})"
            )
            return {}

        # Union-Find to group faces
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Group faces by overlap
        for i in range(n):
            for j in range(i + 1, n):
                iou = self._calculate_iou(face_bboxes[i], face_bboxes[j])
                if iou >= 0.3:  # Default threshold
                    union(i, j)

        # Extract groups
        groups = {}
        for i in range(n):
            group_id = find(i)
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(faces_data[i])

        return groups

    def _build_person_group_from_stored_object(
        self,
        stored_person: Dict[str, Any],
    ) -> PPLThreadPersonGroup:
        """Map a persisted Vision person object into the Orchestrator response shape."""
        representative_faces = stored_person.get("representative_faces") or []
        if isinstance(representative_faces, str):
            try:
                representative_faces = json.loads(representative_faces)
            except (TypeError, ValueError):
                representative_faces = []

        movement_tracking = stored_person.get("movement_tracking") or {}
        route_points = movement_tracking.get("route_points") or []
        movement_statistics = movement_tracking.get("movement_statistics") or {}

        demographics = stored_person.get("demographics") or {}
        tracking_metadata = stored_person.get("tracking_metadata") or {}
        if tracking_metadata:
            demographics = {**demographics, "tracking_metadata": tracking_metadata}

        quality_score = float(stored_person.get("quality_score") or 0.0)

        return PPLThreadPersonGroup(
            person_uuid=stored_person.get("person_id", ""),
            person_id=stored_person.get("person_id", ""),
            face_count=int(stored_person.get("face_count") or 0),
            representative_faces=representative_faces,
            all_face_ids=stored_person.get("face_ids") or [],
            average_confidence=quality_score,
            spatial_bounds=stored_person.get("spatial_bounds") or {},
            temporal_span=stored_person.get("temporal_span") or {},
            movement_tracking={
                "route_points": route_points,
                "movement_statistics": movement_statistics,
            },
            quality_metrics={"quality_score": quality_score},
            demographics=demographics,
        )

    async def _build_person_objects_from_live_faces(
        self,
        media_id: str,
        auth_token: str,
        session_uuid: str,
    ) -> PPLThreadWorkflowResponse:
        """Fallback for media that do not yet have persisted person-object sessions."""
        from face_detection_endpoints import FaceDetectionSessionManager

        start_time = datetime.now()
        session_manager = FaceDetectionSessionManager()

        logger.info(
            "🔄 Falling back to live person-object grouping for media %s",
            media_id,
        )

        face_result = await session_manager.enhanced_logic_v2_session_based(
            media_id=media_id,
            auth_token=auth_token,
            frame_interval=10,
            session_uuid=session_uuid or None,
        )

        if not face_result.get("success", False):
            error_msg = face_result.get("error", "Enhanced Logic V2 failed")
            logger.error("❌ Enhanced Logic V2 failed: %s", error_msg)
            return PPLThreadWorkflowResponse(
                success=False,
                media_id=media_id,
                total_persons=0,
                total_faces=0,
                status="error",
                message=f"Enhanced Logic V2 failed: {error_msg}",
                session_uuid=session_uuid,
            )

        persisted_session_uuid = face_result.get("session_uuid") or session_uuid
        persisted_response = await self._load_persisted_person_objects_response(
            media_id=media_id,
            auth_token=auth_token,
            session_uuid=persisted_session_uuid,
            start_time=start_time,
            attempts=3,
        )
        if persisted_response:
            logger.info(
                "✅ Fallback materialized readable persisted person objects for session %s",
                persisted_session_uuid,
            )
            return persisted_response

        total_faces = face_result.get("total_faces", 0)
        faces_data = face_result.get("faces", [])

        if total_faces == 0:
            person_groups = []
            total_persons = 0
        else:
            face_bboxes = []
            valid_faces = []

            for face in faces_data:
                bbox = face.get("bbox", [])
                if len(bbox) == 4:
                    face_bboxes.append(bbox)
                    valid_faces.append(face)

            if face_bboxes:
                person_groups = self._group_faces_by_rectangle_overlap_detailed(
                    face_bboxes, valid_faces
                )
                total_persons = len(person_groups)
            else:
                person_groups = []
                total_persons = 1 if total_faces > 0 else 0

        routes_data = []
        for person_group in person_groups:
            routes_data.append(
                {
                    "person_uuid": person_group.person_uuid,
                    "person_id": person_group.person_id,
                    "route_points": person_group.movement_tracking.get("route_points", []),
                    "movement_statistics": person_group.movement_tracking.get(
                        "movement_statistics", {}
                    ),
                }
            )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        return PPLThreadWorkflowResponse(
            success=True,
            media_id=media_id,
            total_persons=total_persons,
            total_faces=total_faces,
            status="completed",
            message=f"Rectangle overlap detection with detailed person objects: {total_faces} faces → {total_persons} persons",
            person_groups=person_groups,
            session_uuid=session_uuid,
            routes_data=routes_data,
            processing_time_ms=round(processing_time, 2),
        )

    async def _load_persisted_person_objects_response(
        self,
        media_id: str,
        auth_token: str,
        session_uuid: str,
        start_time: datetime,
        attempts: int = 1,
    ) -> Optional[PPLThreadWorkflowResponse]:
        """Load persisted person objects for a session and format the response."""
        if not session_uuid:
            return None

        trace_ctx = TraceabilityContext(
            workflow_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            source_service="orchestrator",
            operation="get_person_objects_for_media_persisted_session",
            metadata={"media_id": media_id, "session_uuid": session_uuid},
        )

        last_error = None
        for attempt in range(attempts):
            session_details = (
                await self.service_manager.vision.get_person_objects_for_session_details(
                    trace_ctx=trace_ctx,
                    session_uuid=session_uuid,
                    auth_token=auth_token,
                )
            )

            if session_details.success and session_details.data:
                stored_person_objects = session_details.data.get("person_objects") or []
                person_groups = [
                    self._build_person_group_from_stored_object(person)
                    for person in stored_person_objects
                ]
                total_persons = len(person_groups)
                total_faces = sum(person.face_count for person in person_groups)

                routes_data = []
                for person_group in person_groups:
                    routes_data.append(
                        {
                            "person_uuid": person_group.person_uuid,
                            "person_id": person_group.person_id,
                            "route_points": person_group.movement_tracking.get(
                                "route_points", []
                            ),
                            "movement_statistics": person_group.movement_tracking.get(
                                "movement_statistics", {}
                            ),
                        }
                    )

                processing_time = (
                    datetime.now() - start_time
                ).total_seconds() * 1000
                return PPLThreadWorkflowResponse(
                    success=True,
                    media_id=media_id,
                    total_persons=total_persons,
                    total_faces=total_faces,
                    status="completed",
                    message=f"Retrieved {total_persons} persisted person groups",
                    person_groups=person_groups,
                    session_uuid=session_uuid,
                    routes_data=routes_data,
                    processing_time_ms=round(processing_time, 2),
                )

            last_error = session_details.error_message or "Persisted person objects unavailable"
            if attempt < attempts - 1:
                await asyncio.sleep(0.1)

        logger.warning(
            "⚠️ Persisted person objects still unavailable for session %s after fallback write: %s",
            session_uuid,
            last_error,
        )
        return None

    def _select_best_faces(self, group_faces, count=3):
        """Select best faces using PPL Meta quality criteria."""
        if not group_faces:
            return []

        scored_faces = []
        for face in group_faces:
            quality_score = self._calculate_face_quality_score(face)
            scored_faces.append((face, quality_score))

        # Sort by quality score (highest first)
        scored_faces.sort(key=lambda x: x[1], reverse=True)

        # Return top N faces with selection metadata
        representative_faces = []
        for i, (face, score) in enumerate(scored_faces[:count]):
            representative_faces.append(
                {
                    "face_data": face,
                    "quality_score": score,
                    "selection_rank": i + 1,
                    "selection_criteria": {
                        "distance_weight": 0.3,
                        "confidence_weight": 0.3,
                        "area_weight": 0.2,
                        "position_weight": 0.2,
                        "method": "composite_quality_scoring",
                    },
                }
            )

        return representative_faces

    def _calculate_face_quality_score(self, face):
        """Calculate composite quality score for face selection."""
        # Distance score (closer = better, inverse relationship)
        distance = face.get("distance_from_camera", 100)
        distance_score = 100 / max(distance, 1)  # Normalize

        # Confidence score
        confidence_score = face.get("confidence", 0) * 100

        # Size score (larger face area = better quality)
        area_score = face.get("face_area", 1000) / 1000  # Normalize

        # Position score (center of frame = better)
        center_x = face.get("center_x", 0)
        center_y = face.get("center_y", 0)
        # Assume 640x480 frame size for normalization
        frame_center_x, frame_center_y = 320, 240
        position_distance = math.sqrt(
            (center_x - frame_center_x) ** 2 + (center_y - frame_center_y) ** 2
        )
        position_score = 100 / max(position_distance, 1)

        # Weighted composite score
        composite_score = (
            distance_score * 0.3
            + confidence_score * 0.3
            + area_score * 0.2
            + position_score * 0.2
        )

        return round(composite_score, 3)

    def _parse_estimated_age(self, face: Dict[str, Any]) -> Optional[int]:
        """Extract a normalized estimated age from a face payload."""
        age_detection = face.get("age_detection")
        if isinstance(age_detection, dict):
            estimated_age = age_detection.get("estimated_age")
            if isinstance(estimated_age, int) and estimated_age > 0:
                return estimated_age
            if isinstance(estimated_age, str):
                parsed_age = int(estimated_age) if estimated_age.isdigit() else None
                if parsed_age and parsed_age > 0:
                    return parsed_age

        age_estimate = face.get("age_estimate")
        if isinstance(age_estimate, dict):
            estimated_age = age_estimate.get("estimated_age")
            if isinstance(estimated_age, int) and estimated_age > 0:
                return estimated_age
            if isinstance(estimated_age, str):
                parsed_age = int(estimated_age) if estimated_age.isdigit() else None
                if parsed_age and parsed_age > 0:
                    return parsed_age

            min_age = age_estimate.get("min_age")
            max_age = age_estimate.get("max_age")
            if isinstance(min_age, int) and isinstance(max_age, int) and min_age > 0 and max_age > 0:
                return round((min_age + max_age) / 2)

        estimated_age = face.get("estimated_age")
        if isinstance(estimated_age, int) and estimated_age > 0:
            return estimated_age

        return None

    def _parse_age_confidence(self, face: Dict[str, Any]) -> Optional[float]:
        """Extract age confidence when present."""
        age_detection = face.get("age_detection")
        if isinstance(age_detection, dict):
            confidence = age_detection.get("confidence")
            if isinstance(confidence, (int, float)):
                return float(confidence)

        age_estimate = face.get("age_estimate")
        if isinstance(age_estimate, dict):
            confidence = age_estimate.get("confidence")
            if isinstance(confidence, (int, float)):
                return float(confidence)

        return None

    def _parse_gender_evidence(self, face: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract normalized gender evidence from a face payload when available."""
        candidates = [
            face.get("gender_detection"),
            face.get("gender_estimate"),
        ]

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            gender = candidate.get("gender") or candidate.get("estimated_gender")
            if isinstance(gender, str):
                normalized_gender = gender.strip().lower()
                if normalized_gender in {"male", "female", "unknown"}:
                    confidence = candidate.get("confidence")
                    return {
                        "gender": normalized_gender,
                        "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
                    }

        gender = face.get("gender") or face.get("estimated_gender")
        if isinstance(gender, str):
            normalized_gender = gender.strip().lower()
            if normalized_gender in {"male", "female", "unknown"}:
                confidence = face.get("gender_confidence")
                return {
                    "gender": normalized_gender,
                    "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
                }

        return None

    def _build_group_demographics(self, group_faces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate age and gender evidence for a single-video person group."""
        ages: List[int] = []
        age_confidences: List[float] = []
        gender_weights = {"male": 0.0, "female": 0.0, "unknown": 0.0}
        gender_best_confidence: Dict[str, float] = {}

        for face in group_faces:
            estimated_age = self._parse_estimated_age(face)
            if estimated_age is not None:
                ages.append(estimated_age)
                age_confidence = self._parse_age_confidence(face)
                if age_confidence is not None:
                    age_confidences.append(age_confidence)

            gender_evidence = self._parse_gender_evidence(face)
            if gender_evidence is not None:
                gender = gender_evidence["gender"]
                confidence = gender_evidence.get("confidence")
                weight = confidence if confidence is not None else 1.0
                gender_weights[gender] += weight
                previous_best = gender_best_confidence.get(gender)
                if previous_best is None or (confidence is not None and confidence > previous_best):
                    gender_best_confidence[gender] = confidence if confidence is not None else 1.0

        demographics: Dict[str, Any] = {}

        if ages:
            demographics.update(
                {
                    "age_min": min(ages),
                    "age_max": max(ages),
                    "age_mean": round(sum(ages) / len(ages), 2),
                    "age_confidence": round(sum(age_confidences) / len(age_confidences), 3)
                    if age_confidences
                    else None,
                }
            )

        winning_gender = max(gender_weights, key=gender_weights.get)
        if gender_weights[winning_gender] > 0:
            demographics.update(
                {
                    "gender": winning_gender,
                    "gender_confidence": gender_best_confidence.get(winning_gender),
                }
            )

        if demographics:
            demographics.update(
                {
                    "demographics_source": "single_video_person_group",
                    "face_sample_count": len(group_faces),
                }
            )

        return demographics

    def _generate_movement_tracking(self, group_faces):
        """Generate route tracking data for person group."""
        if not group_faces:
            return {
                "route_points": [],
                "movement_statistics": {
                    "total_route_points": 0,
                    "total_distance_pixels": 0,
                    "average_velocity": 0,
                    "max_velocity": 0,
                    "time_in_frame_seconds": 0,
                },
            }

        # Sort faces by frame number/timestamp
        sorted_faces = sorted(group_faces, key=lambda f: f.get("frame_number", 0))

        route_points = []
        velocities = []

        # IMPORTANT: Include ALL face detections in route tracking
        # NO additional sampling needed - Enhanced Logic V2 already handles
        # frame_interval sampling (default every 10 frames)
        for i, face in enumerate(sorted_faces):
            center_x = face.get("center_x", 0)
            center_y = face.get("center_y", 0)
            timestamp = face.get("timestamp", 0)

            # Calculate velocity if not first point
            velocity_x = velocity_y = velocity_magnitude = 0
            if i > 0:
                prev_face = sorted_faces[i - 1]
                prev_center_x = prev_face.get("center_x", 0)
                prev_center_y = prev_face.get("center_y", 0)
                prev_timestamp = prev_face.get("timestamp", 0)

                time_diff = timestamp - prev_timestamp
                if time_diff > 0:
                    velocity_x = (center_x - prev_center_x) / time_diff
                    velocity_y = (center_y - prev_center_y) / time_diff
                    velocity_magnitude = math.sqrt(velocity_x**2 + velocity_y**2)

            route_point = {
                "sequence_number": i + 1,
                "frame_number": face.get("frame_number"),
                "timestamp": timestamp,
                "center_x": center_x,
                "center_y": center_y,
                "distance_from_camera": face.get("distance_from_camera"),
                "velocity_x": round(velocity_x, 2),
                "velocity_y": round(velocity_y, 2),
                "velocity_magnitude": round(velocity_magnitude, 2),
            }

            route_points.append(route_point)
            if velocity_magnitude > 0:
                velocities.append(velocity_magnitude)

        # Calculate movement statistics
        total_distance = sum(velocities) if velocities else 0
        average_velocity = sum(velocities) / len(velocities) if velocities else 0
        max_velocity = max(velocities) if velocities else 0

        return {
            "route_points": route_points,  # ALL detection points, no sampling
            "movement_statistics": {
                "total_route_points": len(route_points),
                "total_distance_pixels": round(total_distance, 2),
                "average_velocity": round(average_velocity, 2),
                "max_velocity": round(max_velocity, 2),
                "time_in_frame_seconds": round(
                    (
                        route_points[-1]["timestamp"] - route_points[0]["timestamp"]
                        if len(route_points) > 1
                        else 0
                    ),
                    2,
                ),
            },
        }

    def _calculate_spatial_bounds(self, group_faces):
        """Calculate spatial boundaries for person group."""
        if not group_faces:
            return {}

        center_xs = [face.get("center_x", 0) for face in group_faces]
        center_ys = [face.get("center_y", 0) for face in group_faces]

        return {
            "min_x": min(center_xs),
            "max_x": max(center_xs),
            "min_y": min(center_ys),
            "max_y": max(center_ys),
            "width": max(center_xs) - min(center_xs),
            "height": max(center_ys) - min(center_ys),
        }

    def _calculate_temporal_span(self, group_faces):
        """Calculate temporal span for person group."""
        if not group_faces:
            return {}

        frame_numbers = [face.get("frame_number", 0) for face in group_faces]
        timestamps = [face.get("timestamp", 0) for face in group_faces]

        return {
            "start_frame": min(frame_numbers),
            "end_frame": max(frame_numbers),
            "frame_span": max(frame_numbers) - min(frame_numbers),
            "start_timestamp": min(timestamps),
            "end_timestamp": max(timestamps),
            "duration_seconds": max(timestamps) - min(timestamps),
        }

    def _group_faces_by_rectangle_overlap_detailed(self, face_bboxes, faces_data):
        """Enhanced grouping with detailed person object creation."""
        if not face_bboxes or not faces_data:
            return []

        # Extract face groups using Union-Find
        groups = self._extract_face_groups(face_bboxes, faces_data)

        person_groups = []

        for group_faces in groups.values():
            # Generate person UUID and ID
            person_uuid = str(uuid.uuid4())
            person_id = f"person_{len(person_groups) + 1}"

            # Select representative faces (top 3)
            representative_faces = self._select_best_faces(group_faces, count=3)

            # Calculate analytics
            average_confidence = sum(
                face.get("confidence", 0) for face in group_faces
            ) / len(group_faces)

            spatial_bounds = self._calculate_spatial_bounds(group_faces)
            temporal_span = self._calculate_temporal_span(group_faces)
            movement_tracking = self._generate_movement_tracking(group_faces)

            # Quality metrics
            quality_scores = [
                self._calculate_face_quality_score(face) for face in group_faces
            ]
            quality_metrics = {
                "average_quality": round(sum(quality_scores) / len(quality_scores), 2),
                "max_quality": round(max(quality_scores), 2),
                "min_quality": round(min(quality_scores), 2),
                "quality_variance": round(
                    sum(
                        (q - sum(quality_scores) / len(quality_scores)) ** 2
                        for q in quality_scores
                    )
                    / len(quality_scores),
                    2,
                ),
            }

            # Extract all face IDs (using frame numbers as IDs)
            all_face_ids = [
                f"face_{face.get('frame_number', i)}"
                for i, face in enumerate(group_faces)
            ]
            demographics = self._build_group_demographics(group_faces)

            person_group = PPLThreadPersonGroup(
                person_uuid=person_uuid,
                person_id=person_id,
                face_count=len(group_faces),
                representative_faces=representative_faces,
                all_face_ids=all_face_ids,
                average_confidence=round(average_confidence, 3),
                spatial_bounds=spatial_bounds,
                temporal_span=temporal_span,
                movement_tracking=movement_tracking,
                quality_metrics=quality_metrics,
                demographics=demographics,
            )

            person_groups.append(person_group)

        return person_groups

    def _setup_routes(self):
        """Setup PPL Thread API routes."""

        @ppl_thread_router.post("/trigger", response_model=PPLThreadWorkflowResponse)
        async def trigger_ppl_thread_workflow(
            request: PPLThreadWorkflowRequest,
            auth_token: str = Depends(get_auth_token),
        ):
            """
            🎯 Trigger PPL Thread workflow for media with face data.

            This is called automatically by the Orchestrator after face detection
            completes, but can also be called manually via API.
            """
            media_id = request.media_id

            logger.info(
                f"🎯 ORCHESTRATOR API: Triggering PPL Thread workflow for media {media_id}"
            )

            try:
                # Create traceability context
                trace_ctx = self.service_manager.create_trace_context(
                    workflow_id=f"ppl-thread-{media_id}",
                    operation="manual_ppl_thread_trigger",
                    metadata={"media_id": media_id, "source": "api"},
                )

                # Trigger PPL Thread workflow via Vision Service
                ppl_response = (
                    await self.service_manager.vision.trigger_person_objects_workflow(
                        trace_ctx=trace_ctx,
                        media_id=media_id,
                        auth_token=auth_token,
                    )
                )

                if ppl_response.success:
                    response_data = ppl_response.data
                    total_persons = response_data.get("total_persons", 0)
                    total_faces = response_data.get("total_faces", 0)
                    status = response_data.get("status", "completed")

                    logger.info(
                        f"🎯 ORCHESTRATOR API: ✅ PPL Thread workflow completed for media {media_id}: {total_persons} persons"
                    )

                    return PPLThreadWorkflowResponse(
                        success=True,
                        media_id=media_id,
                        total_persons=total_persons,
                        total_faces=total_faces,
                        status=status,
                        message=f"PPL Thread workflow completed successfully",
                    )
                else:
                    error_msg = ppl_response.error_message or "Unknown error"
                    logger.error(
                        f"🎯 ORCHESTRATOR API: ❌ PPL Thread workflow failed for media {media_id}: {error_msg}"
                    )

                    return PPLThreadWorkflowResponse(
                        success=False,
                        media_id=media_id,
                        total_persons=0,
                        total_faces=0,
                        status="failed",
                        message=f"PPL Thread workflow failed: {error_msg}",
                    )

            except Exception as e:
                logger.error(
                    f"🎯 ORCHESTRATOR API: Exception triggering PPL Thread for media {media_id}: {e}"
                )

                return PPLThreadWorkflowResponse(
                    success=False,
                    media_id=media_id,
                    total_persons=0,
                    total_faces=0,
                    status="error",
                    message=f"Exception: {str(e)}",
                )

        @ppl_thread_router.get("/{media_id}", response_model=PPLThreadWorkflowResponse)
        async def get_person_objects_for_media(
            media_id: str,
            auth_token: str = Depends(get_auth_token),
        ):
            """
            🎯 Get detailed persisted person objects data for media UUID.

            This endpoint retrieves previously materialized person groups from Vision storage
            so person UUIDs remain stable across reads.
            """
            logger.info(
                f"🎯 PPL THREAD: Getting detailed person objects for media {media_id}"
            )

            start_time = datetime.now()
            session_uuid = ""

            try:
                trace_ctx = TraceabilityContext(
                    workflow_id=str(uuid.uuid4()),
                    request_id=str(uuid.uuid4()),
                    source_service="orchestrator",
                    operation="get_person_objects_for_media_persisted",
                    metadata={"media_id": media_id},
                )

                media_summary = await self.service_manager.vision.get_person_objects_for_media(
                    trace_ctx=trace_ctx,
                    media_id=media_id,
                    auth_token=auth_token,
                )

                summary_data = media_summary.data or {}
                session_uuid = summary_data.get("session_uuid", "")

                if not media_summary.success or not session_uuid:
                    return await self._build_person_objects_from_live_faces(
                        media_id=media_id,
                        auth_token=auth_token,
                        session_uuid=session_uuid,
                    )

                session_details = await self.service_manager.vision.get_person_objects_for_session_details(
                    trace_ctx=trace_ctx,
                    session_uuid=session_uuid,
                    auth_token=auth_token,
                )

                if not session_details.success or not session_details.data:
                    error_msg = (
                        session_details.error_message
                        or "Failed to retrieve persisted person objects"
                    )
                    logger.error("❌ Persisted person object retrieval failed: %s", error_msg)

                    return PPLThreadWorkflowResponse(
                        success=False,
                        media_id=media_id,
                        total_persons=0,
                        total_faces=0,
                        status="error",
                        message=error_msg,
                        session_uuid=session_uuid,
                    )

                stored_person_objects = session_details.data.get("person_objects") or []
                person_groups = [
                    self._build_person_group_from_stored_object(person)
                    for person in stored_person_objects
                ]
                total_persons = len(person_groups)
                total_faces = sum(person.face_count for person in person_groups)

                routes_data = []
                for person_group in person_groups:
                    route_data = {
                        "person_uuid": person_group.person_uuid,
                        "person_id": person_group.person_id,
                        "route_points": person_group.movement_tracking.get(
                            "route_points", []
                        ),
                        "movement_statistics": person_group.movement_tracking.get(
                            "movement_statistics", {}
                        ),
                    }
                    routes_data.append(route_data)

                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds() * 1000

                logger.info(
                    f"🎯 PPL THREAD: ✅ Retrieved {total_persons} persisted person groups from session {session_uuid}"
                )

                return PPLThreadWorkflowResponse(
                    success=True,
                    media_id=media_id,
                    total_persons=total_persons,
                    total_faces=total_faces,
                    status="completed",
                    message=f"Retrieved {total_persons} persisted person groups",
                    person_groups=person_groups,
                    session_uuid=session_uuid,
                    routes_data=routes_data,
                    processing_time_ms=round(processing_time, 2),
                )

            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(f"❌ PPL Thread detailed error for media {media_id}: {e}")

                return PPLThreadWorkflowResponse(
                    success=False,
                    media_id=media_id,
                    total_persons=0,
                    total_faces=0,
                    status="error",
                    message=f"PPL Thread detailed error: {str(e)}",
                    session_uuid=session_uuid,
                    processing_time_ms=round(processing_time, 2),
                )


def create_ppl_thread_endpoints(
    orchestrator: CameraFaceDetectionWorkflowOrchestrator,
    service_manager: ServiceClientManager,
) -> APIRouter:
    """Create and return PPL Thread API router."""
    endpoints = PPLThreadEndpoints(orchestrator, service_manager)
    return ppl_thread_router
