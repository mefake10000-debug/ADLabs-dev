import time
import unittest

from src.perception.async_pose import AsyncPoseRefiner


class _Track:
    def __init__(self, track_id=7):
        self.track_id = track_id
        self.bbox = [10, 10, 60, 100]
        self.pose = None

    def set_pose(self, **pose):
        self.pose = pose


class _SlowPoseEstimator:
    def __init__(self, delay=0.2):
        self.delay = delay
        self.calls = 0

    def estimate_on_bboxes(self, frame, boxes):
        self.calls += 1
        time.sleep(self.delay)
        return [{"foot_point": (34.0, 98.0), "keypoints": ["measured"]} for _ in boxes]


class AsyncPoseRefinerTests(unittest.TestCase):
    def test_pose_inference_does_not_block_live_detector_and_updates_matching_track(self):
        estimator = _SlowPoseEstimator()
        refiner = AsyncPoseRefiner(estimator)
        track = _Track()
        try:
            started = time.monotonic()
            refiner.update([track], object(), every_n=1)
            self.assertLess(time.monotonic() - started, 0.1)
            self.assertIsNone(track.pose)

            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline and track.pose is None:
                time.sleep(0.01)
                refiner.update([track], object(), every_n=1)

            self.assertGreaterEqual(estimator.calls, 1)
            self.assertEqual(track.pose["foot"], (34.0, 98.0))
            self.assertEqual(track.pose["keypoints"], ["measured"])
        finally:
            refiner.close()


if __name__ == "__main__":
    unittest.main()
