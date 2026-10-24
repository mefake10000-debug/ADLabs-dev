import unittest

from src.optimization.frame_scheduler import FrameScheduler


class TestFastInferenceWorker(unittest.TestCase):
    def test_scheduler_never_skips_startup_when_no_tracks_exist(self):
        scheduler = FrameScheduler({"enabled": True, "min_inference_fps": 5})

        decision = scheduler.decide(None, [], now=1.0, feed_fps=15.0)

        self.assertTrue(decision.run_inference)
        self.assertEqual(decision.reason, "startup")


if __name__ == "__main__":
    unittest.main()
