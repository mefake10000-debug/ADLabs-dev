"""Cross-camera association is gated by explicit calibration and uses union counts."""
from __future__ import annotations

import unittest

from src.analytics.cross_camera_fusion import CrossCameraFusion, project_homography


IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def fusion(**overrides):
    args = {
        "requested_enabled": True,
        "reid_active": True,
        "shared_zone_cameras": {"checkout": {"cam_a", "cam_b"}},
        "camera_homographies": {"cam_a": IDENTITY, "cam_b": IDENTITY},
        "association_window_seconds": 1.5,
        "cosine_threshold": 0.86,
        "max_floor_distance_m": 2.5,
    }
    args.update(overrides)
    return CrossCameraFusion(**args)


class TestCrossCameraFusion(unittest.TestCase):
    def test_matches_same_person_across_cameras_and_counts_union(self):
        engine = fusion()
        a = engine.observe("cam_a", 11, [1.0, 0.0], 10.0, ["checkout"], [2.0, 4.0])
        waiting = engine.snapshot({"cam_a": [11]})
        self.assertEqual(waiting["status"], "READY_NO_MATCHES_YET")
        self.assertEqual(waiting["matched_active_tracks"], 0)
        b = engine.observe("cam_b", 39, [0.98, 0.02], 10.5, ["checkout"], [2.2, 4.1])
        self.assertEqual(a, b)
        snap = engine.snapshot({"cam_a": [11], "cam_b": [39]})
        self.assertEqual(snap["deduplicated_active_count"], 1)
        self.assertEqual(snap["matched_active_tracks"], 2)
        # Public telemetry is aggregate-only; ephemeral person keys are not returned.
        self.assertNotIn(a, repr(snap))

    def test_does_not_match_when_zone_time_or_floor_gate_fails(self):
        for second_observation in (
            ("cam_b", 2, [0.99, 0.01], 10.5, ["aisle"], [2.0, 4.0]),
            ("cam_b", 2, [0.99, 0.01], 12.0, ["checkout"], [2.0, 4.0]),
            ("cam_b", 2, [0.99, 0.01], 10.5, ["checkout"], [9.0, 4.0]),
        ):
            engine = fusion(shared_zone_cameras={"checkout": {"cam_a", "cam_b"}, "aisle": {"cam_a", "cam_b"}})
            first = engine.observe("cam_a", 1, [1.0, 0.0], 10.0, ["checkout"], [2.0, 4.0])
            second = engine.observe(*second_observation)
            self.assertNotEqual(first, second)

    def test_fusion_is_fail_closed_without_shared_zone_or_homography(self):
        no_zone = fusion(shared_zone_cameras={})
        no_h = fusion(camera_homographies={"cam_a": IDENTITY})
        self.assertFalse(no_zone.enabled)
        self.assertEqual(no_zone.gate_reason, "shared_store_zone_not_mapped_in_two_cameras")
        self.assertFalse(no_h.enabled)
        self.assertTrue(no_h.gate_reason.startswith("floor_homography_missing:"))
        self.assertIsNone(no_zone.observe("cam_a", 1, [1, 0], 1, ["checkout"], [0, 0]))

    def test_homography_projection(self):
        self.assertEqual(project_homography([25, 70], IDENTITY), (25.0, 70.0))
        self.assertIsNone(project_homography([25, 70], [[1, 0], [0, 1]]))


if __name__ == "__main__":
    unittest.main()
