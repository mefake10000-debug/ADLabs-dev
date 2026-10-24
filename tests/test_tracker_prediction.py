import unittest
from types import SimpleNamespace

from src.main import EdgePipeline


class TestTrackerPredictionViews(unittest.TestCase):
    def setUp(self):
        self.track = SimpleNamespace(
            bbox=[15.0, 10.0, 35.0, 50.0],
            velocity=(50.0, 0.0),
            last_seen=1.1,
        )

    def test_display_projection_translates_copy_without_mutating_observed_track(self):
        original_bbox = list(self.track.bbox)

        views = EdgePipeline._display_tracks_at_time([self.track], 1.2, (100, 100, 3))

        self.assertEqual(len(views), 1)
        self.assertAlmostEqual(views[0].bbox[0], 20.0, places=1)
        self.assertEqual(self.track.bbox, original_bbox)

    def test_display_projection_caps_drift_for_old_tracks(self):
        projected = EdgePipeline._display_tracks_at_time([self.track], 2.0, (100, 100, 3))
        self.assertLessEqual(projected[0].bbox[0] - self.track.bbox[0], 12.0)


if __name__ == "__main__":
    unittest.main()
