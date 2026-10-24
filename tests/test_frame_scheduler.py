import unittest

import numpy as np

from src.optimization.frame_scheduler import FrameScheduler


class FakeTrack:
    def __init__(self, stationary=True, time_since_update=0, hits=10, state="active", velocity=(0.0, 0.0)):
        self.is_stationary = stationary
        self.time_since_update = time_since_update
        self.hits = hits
        self.state = state
        self.velocity = velocity


class TestFrameScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = FrameScheduler({
            "enabled": True,
            "mode": "balanced",
            "min_inference_fps": 5,
            "motion_threshold": 0.01,
            "use_prediction": True,
        })
        self.still = np.zeros((90, 160, 3), dtype=np.uint8)

    def test_first_frame_requires_real_inference(self):
        decision = self.scheduler.decide(self.still, [], now=0.0, feed_fps=15)

        self.assertTrue(decision.run_inference)
        self.assertEqual(decision.reason, "startup")

    def test_empty_scene_always_runs_detector_for_new_arrivals(self):
        self.scheduler.decide(self.still, [], now=0.0, feed_fps=15)

        decision = self.scheduler.decide(self.still, [], now=0.05, feed_fps=15)

        self.assertTrue(decision.run_inference)
        self.assertEqual(decision.reason, "no_tracks")

    def test_still_confirmed_scene_uses_prediction_between_minimum_rate_inferences(self):
        track = FakeTrack(stationary=True)
        self.scheduler.decide(self.still, [track], now=0.0, feed_fps=15)

        skipped = self.scheduler.decide(self.still, [track], now=0.05, feed_fps=15)
        between = self.scheduler.decide(self.still, [track], now=0.10, feed_fps=15)
        due = self.scheduler.decide(self.still, [track], now=0.15, feed_fps=15)
        forced = self.scheduler.decide(self.still, [track], now=0.36, feed_fps=15)

        self.assertFalse(skipped.run_inference)
        self.assertEqual(skipped.reason, "stable_scene")
        self.assertFalse(between.run_inference)
        self.assertTrue(due.run_inference)
        self.assertEqual(due.reason, "cadence_due")
        self.assertTrue(forced.run_inference)
        self.assertEqual(forced.reason, "minimum_rate")

    def test_fast_velocity_track_forces_fresh_detection(self):
        fast = FakeTrack(stationary=False, velocity=(240.0, 0.0))
        self.scheduler.decide(self.still, [FakeTrack(stationary=False)], now=0.0, feed_fps=15)

        decision = self.scheduler.decide(self.still, [fast], now=0.05, feed_fps=15)

        self.assertTrue(decision.run_inference)
        self.assertEqual(decision.reason, "fast_track_motion")

    def test_scene_change_forces_inference(self):
        self.scheduler.decide(self.still, [FakeTrack()], now=0.0, feed_fps=15)

        decision = self.scheduler.decide(np.full_like(self.still, 255), [FakeTrack()], now=0.05, feed_fps=15)

        self.assertTrue(decision.run_inference)
        self.assertEqual(decision.reason, "scene_change")

    def test_unconfirmed_or_missed_track_forces_inference(self):
        self.scheduler.decide(self.still, [FakeTrack()], now=0.0, feed_fps=15)

        decision = self.scheduler.decide(
            self.still, [FakeTrack(time_since_update=1)], now=0.05, feed_fps=15
        )

        self.assertTrue(decision.run_inference)
        self.assertEqual(decision.reason, "track_recovery")


if __name__ == "__main__":
    unittest.main()
