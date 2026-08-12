"""
PPL Meta Vision Service - Three-Tier Discrimination Cascade Tests
Validates the new grouping enhancements in VisionFaceGroupingEngine:

1. Tier 1 - size-proportional tolerance (bbox-based, percentage fallback)
2. Tier 2 - velocity vector discrimination (opt-in)
3. Tier 3 - embedding similarity gate (opt-in)

Also verifies backward compatibility of the default configuration so the
legacy percentage-based behavior (and the existing test suite) is preserved.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime
from typing import Any, Dict, List

# Add the src directory to Python path for imports
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

from person_objects import VisionFaceGroupingEngine


def make_face(
    face_id: str,
    frame: int,
    x: float,
    y: float,
    bbox_w: float = 20.0,
    bbox_h: float = 20.0,
    embedding: List[float] = None,
) -> Dict[str, Any]:
    """Build a face detection record centered at (x, y) with a bbox."""
    face = {
        "id": face_id,
        "frame_number": frame,
        "position_x": x,
        "position_y": y,
        "bbox_x1": x - bbox_w / 2.0,
        "bbox_y1": y - bbox_h / 2.0,
        "bbox_x2": x + bbox_w / 2.0,
        "bbox_y2": y + bbox_h / 2.0,
        "confidence": 0.9,
        "method": "two_stage",
        "created_at": datetime.now(),
    }
    if embedding is not None:
        face["embedding"] = embedding
    return face


class TestTier1SizeProportionalTolerance(unittest.TestCase):
    """Validate the size-proportional tolerance (fixed positional dependency)."""

    def setUp(self):
        self.engine = VisionFaceGroupingEngine()
        self.engine.use_size_based_tolerance = True
        self.engine.size_tolerance_factor = 0.5

    def test_size_based_tolerance_grows_with_bbox(self):
        """Tolerance should scale with bbox size, not absolute position."""
        # Two faces with identical bbox size grouped regardless of where they are.
        faces = [
            make_face("f1", 1, 100.0, 100.0, bbox_w=20.0),  # near origin
            make_face("f2", 2, 105.0, 105.0, bbox_w=20.0),  # 5px away
            make_face("f3", 3, 1000.0, 1000.0, bbox_w=20.0),  # far from origin
            make_face("f4", 4, 1005.0, 1005.0, bbox_w=20.0),  # 5px away, far zone
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        # f1+f2 group, f3+f4 group -> 2 persons, tolerance is position-independent.
        self.assertEqual(len(result["person_objects"]), 2)

    def test_percentage_fallback_when_no_bbox(self):
        """Without bbox size, legacy percentage-of-position tolerance is used."""
        pos1 = {"x": 100.0, "y": 150.0}
        pos2 = {"x": 105.0, "y": 155.0}
        dist = self.engine.calculate_position_distance(pos1, pos2)
        # Legacy percentage: x_tolerance = 100 * 0.2 = 20, y = 150 * 0.2 = 30.
        self.assertAlmostEqual(dist["x_tolerance_used"], 20.0)
        self.assertAlmostEqual(dist["y_tolerance_used"], 30.0)
        self.assertEqual(dist["tolerance_mode"], "percentage")
        self.assertTrue(dist["within_tolerance"])

    def test_size_based_tolerance_mode_reported(self):
        """Size-proportional mode is reported when bbox is present."""
        pos1 = {"x": 100.0, "y": 100.0, "size": 20.0}
        pos2 = {"x": 103.0, "y": 103.0, "size": 20.0}
        dist = self.engine.calculate_position_distance(pos1, pos2)
        self.assertEqual(dist["tolerance_mode"], "size_proportional")
        self.assertAlmostEqual(dist["x_tolerance_used"], 10.0)  # 20 * 0.5
        self.assertTrue(dist["within_tolerance"])

class TestTier2VelocityDiscrimination(unittest.TestCase):
    """Validate the opt-in velocity filter that disambiguates crossing paths."""

    def setUp(self):
        self.engine = VisionFaceGroupingEngine()
        self.engine.use_size_based_tolerance = True
        self.engine.size_tolerance_factor = 0.5
        self.engine.velocity_activation_threshold = 0.0  # always on
        self.engine.min_frames_for_velocity = 2
        self.engine.velocity_inconsistency_factor = 0.5

    def test_velocity_filter_rejects_crossing_person(self):
        """
        Two people cross paths. Position-only would merge them; the velocity
        filter should keep them separate once velocity history is established.
        """
        faces = [
            # Person A moving right, 10px per frame (within 10px tolerance).
            make_face("a1", 1, 100.0, 200.0, bbox_w=20.0),
            make_face("a2", 2, 110.0, 200.0, bbox_w=20.0),
            make_face("a3", 3, 120.0, 200.0, bbox_w=20.0),
            # Person B appears near A's position (would merge by position) but
            # moving left, opposite to A's trajectory.
            make_face("b1", 4, 115.0, 200.0, bbox_w=20.0),
            make_face("b2", 5, 110.0, 200.0, bbox_w=20.0),
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        # A continues right; B moves left from A's last position. Velocity filter
        # should keep them separate -> 2 persons with velocity enabled.
        self.assertEqual(len(result["person_objects"]), 2)
        self.assertGreater(result["statistics"]["tier2_velocity_rejected"], 0)

    def test_velocity_disabled_preserves_legacy_merge(self):
        """With velocity effectively disabled, the same faces merge by position alone."""
        # A very high activation threshold disables velocity discrimination.
        self.engine.velocity_activation_threshold = 1e9
        faces = [
            make_face("a1", 1, 100.0, 200.0, bbox_w=20.0),
            make_face("a2", 2, 110.0, 200.0, bbox_w=20.0),
            make_face("a3", 3, 120.0, 200.0, bbox_w=20.0),
            make_face("b1", 4, 115.0, 200.0, bbox_w=20.0),
            make_face("b2", 5, 110.0, 200.0, bbox_w=20.0),
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        self.assertEqual(len(result["person_objects"]), 1)


class TestTier3EmbeddingGate(unittest.TestCase):
    """Validate the opt-in embedding similarity gate."""

    def setUp(self):
        self.engine = VisionFaceGroupingEngine()
        self.engine.use_size_based_tolerance = True
        self.engine.size_tolerance_factor = 0.5
        self.engine.embedding_gate_enabled = True
        self.engine.embedding_similarity_threshold = 0.6

    def test_embedding_gate_rejects_dissimilar_faces(self):
        """
        Two people standing together (same position, similar velocity) but with
        dissimilar embeddings should be kept separate by the embedding gate.
        """
        faces = [
            # Person A.
            make_face("a1", 1, 100.0, 100.0, embedding=[1.0, 0.0, 0.0]),
            make_face("a2", 2, 101.0, 100.0, embedding=[1.0, 0.0, 0.0]),
            # Person B in the same zone but visually distinct.
            make_face("b1", 2, 102.0, 100.0, embedding=[0.0, 1.0, 0.0]),
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        self.assertEqual(len(result["person_objects"]), 2)
        self.assertGreater(result["statistics"]["tier3_embedding_rejected"], 0)

    def test_embedding_gate_merges_similar_faces(self):
        """Similar embeddings in the same zone group together."""
        faces = [
            make_face("a1", 1, 100.0, 100.0, embedding=[1.0, 0.0, 0.0]),
            make_face("a2", 2, 101.0, 100.0, embedding=[0.98, 0.0, 0.0]),
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        self.assertEqual(len(result["person_objects"]), 1)

    def test_embedding_similarity_math(self):
        """Cosine similarity calculation is correct."""
        self.assertAlmostEqual(
            self.engine._cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0
        )
        self.assertAlmostEqual(
            self.engine._cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0
        )
        self.assertAlmostEqual(self.engine._cosine_similarity([], []), 0.0)

class TestTier3LazyExtractor(unittest.TestCase):
    """Validate lazy, in-memory embedding extraction via the injected extractor."""

    def setUp(self):
        self.engine = VisionFaceGroupingEngine()
        self.engine.use_size_based_tolerance = True
        self.engine.size_tolerance_factor = 0.5
        self.engine.embedding_gate_enabled = True
        self.engine.embedding_similarity_threshold = 0.6

    def test_lazy_extractor_provides_embeddings(self):
        """Faces without an embedding field get one from the injected extractor."""
        calls = []

        def extractor(face_record):
            calls.append(face_record["id"])
            # Person A -> [1,0,0], Person B -> [0,1,0]
            if face_record["id"].startswith("a"):
                return [1.0, 0.0, 0.0]
            return [0.0, 1.0, 0.0]

        self.engine = VisionFaceGroupingEngine(embedding_extractor=extractor)
        self.engine.use_size_based_tolerance = True
        self.engine.size_tolerance_factor = 0.5
        self.engine.embedding_gate_enabled = True
        self.engine.embedding_similarity_threshold = 0.6

        faces = [
            make_face("a1", 1, 100.0, 100.0),  # no embedding field
            make_face("a2", 2, 101.0, 100.0),  # no embedding field
            make_face("b1", 2, 102.0, 100.0),  # no embedding field
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        # A and B are distinguished by the extracted embeddings.
        self.assertEqual(len(result["person_objects"]), 2)
        self.assertGreater(result["statistics"]["tier3_embedding_rejected"], 0)
        # Extractor was called, and embeddings were cached in-memory (no DB).
        self.assertGreater(len(calls), 0)
        self.assertGreater(len(self.engine._extracted_embeddings), 0)

    def test_lazy_extractor_noop_when_absent(self):
        """Without an extractor, Tier 3 remains a no-op (backward compatible)."""
        engine = VisionFaceGroupingEngine()  # no extractor
        engine.use_size_based_tolerance = True
        engine.size_tolerance_factor = 0.5
        engine.embedding_gate_enabled = True

        faces = [
            make_face("a1", 1, 100.0, 100.0),  # no embedding
            make_face("b1", 2, 102.0, 100.0),  # no embedding
        ]
        result = asyncio.run(engine.apply_percentage_based_tracking(faces, 20.0))
        # No embeddings -> no discrimination -> any nearby face merges.
        self.assertEqual(len(result["person_objects"]), 1)
        self.assertEqual(result["statistics"]["tier3_embedding_rejected"], 0)

    def test_extractor_failure_is_non_blocking(self):
        """A failing extractor must not break grouping (Tier 3 degrades to no-op)."""
        def extractor(face_record):
            raise RuntimeError("model unavailable")

        engine = VisionFaceGroupingEngine(embedding_extractor=extractor)
        engine.use_size_based_tolerance = True
        engine.size_tolerance_factor = 0.5
        engine.embedding_gate_enabled = True

        faces = [
            make_face("a1", 1, 100.0, 100.0),
            make_face("a2", 2, 101.0, 100.0),
        ]
        result = asyncio.run(engine.apply_percentage_based_tracking(faces, 20.0))
        # Grouping still works; Tier 3 simply did not reject anything.
        self.assertEqual(len(result["person_objects"]), 1)
        self.assertEqual(result["statistics"]["tier3_embedding_rejected"], 0)

class TestBackwardCompatibility(unittest.TestCase):
    """Default config must preserve the original percentage-based behavior."""

    def setUp(self):
        self.engine = VisionFaceGroupingEngine()

    def test_default_tolerance_is_percentage_when_no_bbox(self):
        pos1 = {"x": 100.0, "y": 150.0}
        pos2 = {"x": 105.0, "y": 155.0}
        dist = self.engine.calculate_position_distance(pos1, pos2)
        self.assertAlmostEqual(dist["x_tolerance_used"], 20.0)
        self.assertAlmostEqual(dist["y_tolerance_used"], 30.0)
        self.assertEqual(dist["tolerance_mode"], "percentage")

    def test_default_velocity_and_embedding_enabled(self):
        # Tier 2 (velocity) and Tier 3 (embedding) are on by default but
        # self-regulating: velocity gates on motion, embedding gates on data.
        self.assertEqual(self.engine.velocity_activation_threshold, 0.0)
        self.assertTrue(self.engine.embedding_gate_enabled)
        self.assertTrue(self.engine.use_size_based_tolerance)

    def test_default_grouping_still_groups_nearby_faces(self):
        faces = [
            make_face("f1", 1, 100.0, 150.0),
            make_face("f2", 2, 105.0, 155.0),
            make_face("f3", 3, 300.0, 200.0),
        ]
        result = asyncio.run(self.engine.apply_percentage_based_tracking(faces, 20.0))
        self.assertEqual(len(result["person_objects"]), 2)
        self.assertEqual(result["statistics"]["algorithm"], "percentage_based_tracking")


if __name__ == "__main__":
    unittest.main(verbosity=2)