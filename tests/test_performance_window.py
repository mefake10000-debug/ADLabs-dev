import unittest

from src.optimization.performance import PerformanceWindow


class TestPerformanceWindow(unittest.TestCase):
    def test_reports_measured_feed_detector_effective_fps_and_skip_rate(self):
        metrics = PerformanceWindow(window_seconds=2.0)
        metrics.record_frame()
        metrics.record_inference(duration_ms=100, motion_score=0.02, reason="startup")
        metrics.record_frame()
        metrics.record_skip(motion_score=0.0, reason="stable_scene")
        metrics.record_render()

        metrics.snapshot(now=0.0, feed_fps=15.0)
        result = metrics.snapshot(now=2.0, feed_fps=15.0)

        self.assertEqual(result["feed_fps"], 15.0)
        self.assertEqual(result["model_inference_fps"], 0.5)
        self.assertEqual(result["effective_fps"], 0.5)
        self.assertEqual(result["skip_rate"], 50.0)
        self.assertEqual(result["detector_ms_avg"], 100.0)
        self.assertEqual(result["last_schedule_reason"], "stable_scene")

    def test_missing_feed_rate_stays_null(self):
        metrics = PerformanceWindow()

        snapshot = metrics.snapshot(now=1.0, feed_fps=None)
        self.assertIsNone(snapshot["feed_fps"])
        self.assertIsNone(snapshot["model_inference_fps"])
        self.assertIsNone(snapshot["effective_fps"])


if __name__ == "__main__":
    unittest.main()
