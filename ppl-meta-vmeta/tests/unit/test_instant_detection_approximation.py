from datetime import datetime, timedelta

from src.services.instant_detection_approximation import (
    ApproximationParams,
    cluster_sightings,
    normalize_sightings,
    summarize_clusters,
)


def _row(
    *,
    person_object_uuid: str,
    start_timestamp: datetime,
    bbox: list[float],
    confidence: float = 0.9,
    age_estimate: int | None = None,
    gender_estimate: str | None = None,
    mvr_people_uuid: str | None = None,
) -> dict:
    return {
        "individual_uuid": f"ind-{person_object_uuid}",
        "person_object_uuid": person_object_uuid,
        "start_timestamp": start_timestamp,
        "confidence": confidence,
        "representative_faces": [{"bbox": bbox, "confidence": confidence}],
        "age_estimate": age_estimate,
        "gender_estimate": gender_estimate,
        "mvr_people_uuid": mvr_people_uuid,
    }


def test_clusters_nearby_sightings_into_one_person():
    params = ApproximationParams()
    start = datetime(2026, 5, 10, 9, 0, 0)
    rows = [
        _row(
            person_object_uuid="a1",
            start_timestamp=start,
            bbox=[100, 100, 160, 180],
            age_estimate=30,
            gender_estimate="Male",
        ),
        _row(
            person_object_uuid="a2",
            start_timestamp=start + timedelta(seconds=5),
            bbox=[108, 104, 168, 184],
            age_estimate=32,
            gender_estimate="Male",
        ),
    ]

    sightings = normalize_sightings(rows, params)
    clusters = cluster_sightings(sightings, params)
    summary = summarize_clusters(clusters, include_members=False)

    assert len(clusters) == 1
    assert summary[0]["detection_count"] == 2
    assert summary[0]["age"] == 31
    assert summary[0]["gender"] == "male"


def test_separates_sightings_when_geometry_is_far_apart():
    params = ApproximationParams()
    start = datetime(2026, 5, 10, 9, 0, 0)
    rows = [
        _row(
            person_object_uuid="a1",
            start_timestamp=start,
            bbox=[100, 100, 160, 180],
        ),
        _row(
            person_object_uuid="b1",
            start_timestamp=start + timedelta(seconds=3),
            bbox=[500, 500, 560, 580],
        ),
    ]

    sightings = normalize_sightings(rows, params)
    clusters = cluster_sightings(sightings, params)

    assert len(clusters) == 2


def test_mvr_hint_extends_time_window_but_keeps_demographic_summary():
    params = ApproximationParams(time_window_seconds=12, use_mvr_hint=True)
    start = datetime(2026, 5, 10, 9, 0, 0)
    rows = [
        _row(
            person_object_uuid="a1",
            start_timestamp=start,
            bbox=[200, 200, 260, 280],
            age_estimate=24,
            gender_estimate="Female",
            mvr_people_uuid="mvr-1",
        ),
        _row(
            person_object_uuid="a2",
            start_timestamp=start + timedelta(seconds=25),
            bbox=[205, 202, 265, 282],
            age_estimate=28,
            gender_estimate="Female",
            mvr_people_uuid="mvr-1",
        ),
        _row(
            person_object_uuid="a3",
            start_timestamp=start + timedelta(seconds=27),
            bbox=[208, 204, 268, 284],
            age_estimate=26,
            gender_estimate="Male",
            mvr_people_uuid="mvr-1",
        ),
    ]

    sightings = normalize_sightings(rows, params)
    clusters = cluster_sightings(sightings, params)
    summary = summarize_clusters(clusters, include_members=True)

    assert len(clusters) == 1
    assert summary[0]["age"] == 26
    assert summary[0]["gender"] == "female"
    assert summary[0]["mvr_people_uuid"] == "mvr-1"
    assert len(summary[0]["members"]) == 3