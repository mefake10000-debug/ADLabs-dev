import unittest

import numpy as np

from src.perception.illumination import normalize_illumination


class TestAdaptiveIllumination(unittest.TestCase):
    def test_normal_light_frame_is_not_modified(self):
        frame = np.full((48, 64, 3), 128, dtype=np.uint8)

        result, mode = normalize_illumination(frame)

        self.assertIs(result, frame)
        self.assertEqual(mode, "normal")

    def test_low_light_is_lifted_without_changing_frame_shape(self):
        frame = np.full((48, 64, 3), 35, dtype=np.uint8)

        result, mode = normalize_illumination(frame)

        self.assertEqual(mode, "low_light")
        self.assertEqual(result.shape, frame.shape)
        self.assertGreater(float(result.mean()), float(frame.mean()))

    def test_overexposed_frame_is_compressed_without_changing_frame_shape(self):
        frame = np.full((48, 64, 3), 238, dtype=np.uint8)

        result, mode = normalize_illumination(frame)

        self.assertEqual(mode, "high_light")
        self.assertEqual(result.shape, frame.shape)
        self.assertLess(float(result.mean()), float(frame.mean()))


if __name__ == "__main__":
    unittest.main()
