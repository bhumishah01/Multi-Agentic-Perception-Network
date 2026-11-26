import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from apn.perception.detector import CentroidAssociator
from apn.perception.models import Observation, Quality
from apn.perception.pipeline import PerceptionPipeline
from apn.perception.reid import HSVEmbedding
from apn.perception.zones import ZoneResolver


class PerceptionTests(unittest.TestCase):
    def test_observation_contract(self):
        observation = Observation(
            camera_id="CAM-01", local_track_id="T-0001", ts_source=1, store_ts=1,
            frame_idx=24, bbox_px=(1, 2, 11, 22), foot_px=(6, 22), zone="Entrance",
            detector_score=.8, embedding_ref="e.npy", crop_ref="c.jpg",
            quality=Quality(blur=10, occlusion_est=0, size_px=200),
        )
        self.assertIsNone(observation.foot_floor)
        self.assertEqual(observation.position_basis, "uncalibrated_image")

    def test_centroid_association_is_stable(self):
        tracker = CentroidAssociator(max_distance=30)
        first = tracker.assign([(0, 0, 10, 20), (100, 0, 110, 20)])
        second = tracker.assign([(3, 0, 13, 20), (97, 0, 107, 20)])
        self.assertEqual(first, second)

    def test_hsv_embedding_is_saved_and_normalised(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "embedding.npy"
            crop = np.full((30, 20, 3), (0, 0, 255), dtype=np.uint8)
            HSVEmbedding().save(crop, path)
            vector = np.load(path)
            self.assertEqual(vector.shape, (384,))
            self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_zone_polygon_assignment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zones.json"
            path.write_text('{"zones":[{"name":"Checkout","points":[[0,0],[10,0],[10,10],[0,10]]}]}')
            resolver = ZoneResolver("Unknown", path)
            self.assertEqual(resolver.resolve((5, 5)), "Checkout")
            self.assertEqual(resolver.resolve((20, 20)), "Unknown")

    def test_overlay_renderer_does_not_burn_into_source(self):
        frame = np.zeros((40, 40, 3), dtype=np.uint8)
        observation = Observation(
            camera_id="CAM-01", local_track_id="T-1", ts_source=0, store_ts=0,
            frame_idx=0, bbox_px=(5, 5, 20, 30), foot_px=(12.5, 30), zone="Entrance",
            detector_score=.8, embedding_ref="e.npy", crop_ref="c.jpg",
            quality=Quality(blur=1, occlusion_est=0, size_px=375),
        )
        rendered = PerceptionPipeline.render_overlay(frame, [observation])
        self.assertEqual(int(frame.sum()), 0)
        self.assertGreater(int(rendered.sum()), 0)


if __name__ == "__main__":
    unittest.main()
