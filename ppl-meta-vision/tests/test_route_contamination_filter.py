"""
Unit tests for route-based face contamination filter (frame-primary).
"""

import os
import sys
import unittest

src_path = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(src_path))

from person_objects.route_contamination_filter import (
    build_route_points_for_person,
    filter_contaminated_person_tracks,
    should_keep_route,
)


def _pt(frame: int, x: float = 100.0, y: float = 100.0, size: float = 40.0):
    return {
        "frame_number": frame,
        "center_x": x,
        "center_y": y,
        "bbox": [x - size / 2, y - size / 2, x + size / 2, y + size / 2],
    }


class TestRouteContaminationFilter(unittest.TestCase):
    def test_continuous_walk_kept(self):
        # ~2.7s walk @ step 10 / 30 FPS with small center drift
        points = [
            _pt(f, x=100.0 + i * 2.0, y=100.0 + i)
            for i, f in enumerate(range(0, 90, 10))
        ]
        decision = should_keep_route(points, sample_frame_step=10, video_fps=30.0)
        self.assertTrue(decision["keep"], decision)
        self.assertEqual(decision["reason"], "ok")
        self.assertGreaterEqual(decision["metrics"]["longest_run_seconds"], 1.2)

    def test_one_or_two_isolated_frames_dropped(self):
        decision = should_keep_route([_pt(0)], sample_frame_step=10, video_fps=30.0)
        self.assertFalse(decision["keep"])
        self.assertEqual(decision["reason"], "longest_run")

        decision = should_keep_route(
            [_pt(0), _pt(10)], sample_frame_step=10, video_fps=30.0
        )
        self.assertFalse(decision["keep"])
        self.assertEqual(decision["reason"], "longest_run")

    def test_scattered_hits_dropped_by_occupancy(self):
        # Two short real-looking bursts (~1.3s each) far apart → longest_run ok,
        # but occupancy across the long span is low.
        points = [_pt(f) for f in list(range(0, 50, 10)) + list(range(800, 850, 10))]
        decision = should_keep_route(points, sample_frame_step=10, video_fps=30.0)
        self.assertFalse(decision["keep"], decision)
        self.assertEqual(decision["reason"], "occupancy")
        self.assertGreaterEqual(decision["metrics"]["longest_run_seconds"], 1.2)
        self.assertLess(decision["metrics"]["occupancy"], 0.5)
        self.assertGreaterEqual(decision["metrics"]["span_seconds"], 2.0)

    def test_standing_person_continuous_kept(self):
        # ~5s continuous, near-zero motion
        points = [_pt(f, x=200.0, y=150.0) for f in range(0, 160, 10)]
        decision = should_keep_route(points, sample_frame_step=10, video_fps=30.0)
        self.assertTrue(decision["keep"], decision)
        self.assertLess(decision["metrics"]["normalized_center_std"], 0.05)

    def test_filter_grouping_results_strips_mappings(self):
        faces = [
            {
                "id": "a1",
                "frame_number": 0,
                "position_x": 100,
                "position_y": 100,
                "bbox_x1": 80,
                "bbox_y1": 80,
                "bbox_x2": 120,
                "bbox_y2": 120,
            },
            {
                "id": "a2",
                "frame_number": 500,
                "position_x": 100,
                "position_y": 100,
                "bbox_x1": 80,
                "bbox_y1": 80,
                "bbox_x2": 120,
                "bbox_y2": 120,
            },
        ]
        grouping = {
            "person_objects": [
                {"person_id": "person_1", "face_count": 2},
            ],
            "face_mappings": [
                {
                    "person_id": "person_1",
                    "face_detection_id": "a1",
                    "frame_number": 0,
                    "position_x": 100,
                    "position_y": 100,
                },
                {
                    "person_id": "person_1",
                    "face_detection_id": "a2",
                    "frame_number": 500,
                    "position_x": 100,
                    "position_y": 100,
                },
            ],
            "statistics": {},
        }
        filter_contaminated_person_tracks(
            grouping, faces, sample_frame_step=10, video_fps=30.0
        )
        self.assertEqual(grouping["person_objects"], [])
        self.assertEqual(grouping["face_mappings"], [])
        self.assertEqual(grouping["statistics"]["route_contaminants_dropped"], 1)

    def test_build_route_points_joins_detections(self):
        faces = [
            {
                "id": "f1",
                "frame_number": 10,
                "bbox_x1": 0,
                "bbox_y1": 0,
                "bbox_x2": 40,
                "bbox_y2": 40,
                "timestamp": 0.33,
            }
        ]
        mappings = [
            {
                "person_id": "p1",
                "face_detection_id": "f1",
                "frame_number": 10,
            }
        ]
        points = build_route_points_for_person("p1", mappings, faces)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["center_x"], 20.0)
        self.assertEqual(points[0]["timestamp"], 0.33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
