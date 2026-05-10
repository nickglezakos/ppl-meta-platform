"""Helpers for approximate instant-detection people analytics."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from json import JSONDecodeError
from typing import Any, Dict, List, Optional


@dataclass
class ApproximationParams:
    time_window_seconds: int = 12
    center_distance_px: int = 120
    size_ratio_tolerance: float = 0.35
    min_confidence: float = 0.50
    use_mvr_hint: bool = True


@dataclass
class Sighting:
    individual_uuid: str
    person_object_uuid: str
    timestamp: datetime
    confidence: float
    age_estimate: Optional[int]
    gender_estimate: Optional[str]
    mvr_people_uuid: Optional[str]
    bbox: List[float]
    center_x: float
    center_y: float
    area: float


@dataclass
class Cluster:
    members: List[Sighting] = field(default_factory=list)
    best_member: Optional[Sighting] = None

    def add(self, sighting: Sighting) -> None:
        self.members.append(sighting)
        if self.best_member is None or sighting.confidence > self.best_member.confidence:
            self.best_member = sighting

    @property
    def latest_member(self) -> Sighting:
        return self.members[-1]


def _parse_representative_faces(raw_faces: Any) -> Optional[List[float]]:
    if raw_faces is None:
        return None

    parsed = raw_faces
    if isinstance(raw_faces, str):
        try:
            parsed = json.loads(raw_faces)
        except JSONDecodeError:
            return None

    if isinstance(parsed, dict):
        parsed = parsed.get("faces") or [parsed]

    if not isinstance(parsed, list) or not parsed:
        return None

    face = parsed[0]
    if not isinstance(face, dict):
        return None

    bbox = face.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None

    try:
        return [float(value) for value in bbox]
    except (TypeError, ValueError):
        return None


def _normalize_gender(value: Optional[str]) -> str:
    normalized = (value or "unknown").strip().lower()
    if normalized in {"male", "man", "m"}:
        return "male"
    if normalized in {"female", "woman", "f"}:
        return "female"
    return "unknown"


def _build_sighting(row: Dict[str, Any]) -> Optional[Sighting]:
    bbox = _parse_representative_faces(row.get("representative_faces"))
    if not bbox:
        return None

    x1, y1, x2, y2 = bbox
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    area = width * height
    if area <= 0:
        return None

    return Sighting(
        individual_uuid=str(row["individual_uuid"]),
        person_object_uuid=str(row["person_object_uuid"]),
        timestamp=row["start_timestamp"],
        confidence=float(row.get("confidence") or 0.0),
        age_estimate=row.get("age_estimate"),
        gender_estimate=_normalize_gender(row.get("gender_estimate")),
        mvr_people_uuid=str(row["mvr_people_uuid"]) if row.get("mvr_people_uuid") else None,
        bbox=bbox,
        center_x=(x1 + x2) / 2.0,
        center_y=(y1 + y2) / 2.0,
        area=area,
    )


def normalize_sightings(rows: List[Dict[str, Any]], params: ApproximationParams) -> List[Sighting]:
    sightings: List[Sighting] = []
    for row in rows:
        sighting = _build_sighting(row)
        if sighting is None:
            continue
        if sighting.confidence < params.min_confidence:
            continue
        sightings.append(sighting)

    sightings.sort(key=lambda item: item.timestamp)
    return sightings


def _center_distance(left: Sighting, right: Sighting) -> float:
    return math.dist((left.center_x, left.center_y), (right.center_x, right.center_y))


def _size_delta(left: Sighting, right: Sighting) -> float:
    return abs(left.area - right.area) / max(left.area, right.area)


def _effective_time_window(cluster: Cluster, sighting: Sighting, params: ApproximationParams) -> int:
    if not params.use_mvr_hint or not sighting.mvr_people_uuid:
        return params.time_window_seconds
    if any(member.mvr_people_uuid == sighting.mvr_people_uuid for member in cluster.members):
        return params.time_window_seconds * 3
    return params.time_window_seconds


def is_compatible(cluster: Cluster, sighting: Sighting, params: ApproximationParams) -> bool:
    anchor = cluster.latest_member
    time_gap_seconds = abs((sighting.timestamp - anchor.timestamp).total_seconds())
    if time_gap_seconds > _effective_time_window(cluster, sighting, params):
        return False

    best_member = cluster.best_member or anchor
    if _center_distance(best_member, sighting) > params.center_distance_px:
        return False
    if _size_delta(best_member, sighting) > params.size_ratio_tolerance:
        return False
    return True


def score_candidate_cluster(cluster: Cluster, sighting: Sighting, params: ApproximationParams) -> float:
    anchor = cluster.latest_member
    best_member = cluster.best_member or anchor
    time_window = max(1, _effective_time_window(cluster, sighting, params))
    time_gap_seconds = abs((sighting.timestamp - anchor.timestamp).total_seconds())
    center_distance = _center_distance(best_member, sighting)
    size_delta = _size_delta(best_member, sighting)
    return (
        time_gap_seconds / time_window
        + center_distance / max(1, params.center_distance_px)
        + size_delta / max(0.0001, params.size_ratio_tolerance)
    )


def cluster_sightings(sightings: List[Sighting], params: ApproximationParams) -> List[Cluster]:
    clusters: List[Cluster] = []
    for sighting in sightings:
        best_cluster: Optional[Cluster] = None
        best_score: Optional[float] = None

        for cluster in reversed(clusters):
            if not is_compatible(cluster, sighting, params):
                continue
            score = score_candidate_cluster(cluster, sighting, params)
            if best_score is None or score < best_score:
                best_cluster = cluster
                best_score = score

        if best_cluster is None:
            best_cluster = Cluster()
            clusters.append(best_cluster)

        best_cluster.add(sighting)

    return clusters


def summarize_cluster(cluster: Cluster, index: int, include_members: bool) -> Dict[str, Any]:
    members = cluster.members
    best_member = cluster.best_member or members[0]

    ages = [member.age_estimate for member in members if member.age_estimate is not None]
    age = round(sum(ages) / len(ages)) if ages else None

    gender_counts: Counter[str] = Counter()
    gender_confidence: Dict[str, float] = defaultdict(float)
    for member in members:
        normalized = _normalize_gender(member.gender_estimate)
        gender_counts[normalized] += 1
        gender_confidence[normalized] += member.confidence

    if gender_counts:
        gender = sorted(
            gender_counts.keys(),
            key=lambda item: (gender_counts[item], gender_confidence[item], item != "unknown"),
            reverse=True,
        )[0]
    else:
        gender = "unknown"

    mvr_values = {member.mvr_people_uuid for member in members if member.mvr_people_uuid}
    group_mvr = next(iter(mvr_values)) if len(mvr_values) == 1 and len(members) == len([m for m in members if m.mvr_people_uuid]) else None

    result: Dict[str, Any] = {
        "approx_person_id": f"approx_{index:03d}",
        "first_seen": min(member.timestamp for member in members).isoformat(),
        "last_seen": max(member.timestamp for member in members).isoformat(),
        "detection_count": len(members),
        "age": age,
        "gender": gender,
        "representative_bbox": [round(value, 2) for value in best_member.bbox],
        "avg_face_area": round(sum(member.area for member in members) / len(members), 2),
        "mvr_people_uuid": group_mvr,
    }

    if include_members:
        result["members"] = [
            {
                "person_object_uuid": member.person_object_uuid,
                "individual_uuid": member.individual_uuid,
                "timestamp": member.timestamp.isoformat(),
                "confidence": member.confidence,
                "age_estimate": member.age_estimate,
                "gender_estimate": member.gender_estimate,
                "mvr_people_uuid": member.mvr_people_uuid,
                "bbox": [round(value, 2) for value in member.bbox],
            }
            for member in members
        ]
    else:
        result["member_person_object_uuids"] = [member.person_object_uuid for member in members]

    return result


def summarize_clusters(clusters: List[Cluster], include_members: bool) -> List[Dict[str, Any]]:
    return [
        summarize_cluster(cluster, index, include_members)
        for index, cluster in enumerate(clusters, start=1)
    ]