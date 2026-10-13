"""
Orchestrator: time-aware IoU grouping + route contamination hard-drop.
"""

import os
import sys
import unittest

src_path = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(src_path))

from route_contamination_filter import should_keep_route
from ppl_thread_endpoints import PPLThreadEndpoints


def _face(frame: int, bbox, confidence: float = 0.9):
    x1, y1, x2, y2 = bbox
    return {
        "id": f"face_{frame}",
        "frame_number": frame,
        "timestamp": frame / 30.0,
        "bbox": [x1, y1, x2, y2],
        "center_x": (x1 + x2) / 2.0,
        "center_y": (y1 + y2) / 2.0,
        "confidence": confidence,
    }


class TestTimeAwareIoUGrouping(unittest.TestCase):
    def setUp(self):
        self.endpoints = PPLThreadEndpoints(
            orchestrator=None,
            service_manager=None,
        )

    def test_iou_without_time_would_glue_but_gap_splits(self):
        # Same bbox location at frame 10 and 500 — IoU high, but temporal gap splits.
        bbox = [100, 100, 140, 140]
        faces = [_face(10, bbox), _face(500, bbox)]
        bboxes = [f["bbox"] for f in faces]
        groups = self.endpoints._extract_face_groups(
            bboxes, faces, max_link_frame_gap=20
        )
        self.assertEqual(len(groups), 2)

    def test_nearby_frames_with_iou_merge(self):
        bbox_a = [100, 100, 140, 140]
        bbox_b = [105, 105, 145, 145]
        faces = [_face(0, bbox_a), _face(10, bbox_b), _face(20, bbox_b)]
        bboxes = [f["bbox"] for f in faces]
        groups = self.endpoints._extract_face_groups(
            bboxes, faces, max_link_frame_gap=20
        )
        self.assertEqual(len(groups), 1)

    def test_detailed_grouping_drops_short_blinks(self):
        bbox = [100, 100, 140, 140]
        faces = [_face(0, bbox), _face(500, bbox)]
        bboxes = [f["bbox"] for f in faces]
        groups = self.endpoints._group_faces_by_rectangle_overlap_detailed(
            bboxes, faces
        )
        # Each becomes its own group then both fail longest_run → empty
        self.assertEqual(len(groups), 0)

    def test_detailed_grouping_keeps_continuous_walk(self):
        faces = []
        for i, frame in enumerate(range(0, 90, 10)):
            x = 100 + i * 2
            faces.append(_face(frame, [x, 100, x + 40, 140]))
        bboxes = [f["bbox"] for f in faces]
        groups = self.endpoints._group_faces_by_rectangle_overlap_detailed(
            bboxes, faces
        )
        self.assertEqual(len(groups), 1)

    def test_should_keep_route_vectors_match_vision(self):
        # Identical vectors to Vision filter tests
        walk = [
            {
                "frame_number": f,
                "center_x": 100.0 + i * 2,
                "center_y": 100.0 + i,
                "bbox": [80, 80, 120, 120],
            }
            for i, f in enumerate(range(0, 90, 10))
        ]
        self.assertTrue(
            should_keep_route(walk, sample_frame_step=10, video_fps=30.0)["keep"]
        )

        scattered = [
            {"frame_number": f, "center_x": 100.0, "center_y": 100.0}
            for f in list(range(0, 50, 10)) + list(range(800, 850, 10))
        ]
        decision = should_keep_route(
            scattered, sample_frame_step=10, video_fps=30.0
        )
        self.assertFalse(decision["keep"])
        self.assertEqual(decision["reason"], "occupancy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
