import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.heatmap import Heatmap
from src.perception.tracker import Track


def standing_at(x, y, tid=1):
    """A track whose feet are at (x, y)."""
    return Track(tid, [x - 20, y - 100, x + 20, y], 0.9, 0.0)


class TestHeatmap(unittest.TestCase):
    def test_accumulates_person_seconds_at_the_foot_cell(self):
        hm = Heatmap(640, 480, cell=16)
        for t in range(0, 11):  # one person standing still for 10 seconds
            hm.add([standing_at(100, 200)], float(t))
        self.assertAlmostEqual(hm.total_person_seconds, 10.0)
        self.assertAlmostEqual(hm.grid[200 // 16, 100 // 16], 10.0)

    def test_same_answer_at_any_frame_rate(self):
        slow, fast = Heatmap(640, 480), Heatmap(640, 480)
        for i in range(0, 31):  # 3 fps for 10s
            slow.add([standing_at(300, 300)], i / 3)
        for i in range(0, 131):  # 13 fps for 10s
            fast.add([standing_at(300, 300)], i / 13)
        self.assertAlmostEqual(slow.total_person_seconds, fast.total_person_seconds, places=4)

    def test_processing_stall_is_capped(self):
        hm = Heatmap(640, 480)
        hm.add([standing_at(100, 100)], 0.0)
        hm.add([standing_at(100, 100)], 30.0)  # 30s with no processed frames
        self.assertAlmostEqual(hm.total_person_seconds, Heatmap.MAX_STEP_SECONDS)

    def test_feet_outside_the_frame_land_in_the_edge_cell(self):
        hm = Heatmap(640, 480, cell=16)
        hm.add([], 0.0)
        hm.add([standing_at(700, 500)], 1.0)
        self.assertAlmostEqual(hm.grid[-1, -1], 1.0)

    def test_render_keeps_frame_size_and_only_tints_where_people_were(self):
        hm = Heatmap(640, 480)
        frame = np.full((480, 640, 3), 128, np.uint8)
        self.assertEqual(hm.render(frame).shape, frame.shape)  # empty heatmap renders fine
        for t in range(0, 11):
            hm.add([standing_at(100, 300)], float(t))
        out = hm.render(frame)
        self.assertEqual(out.shape, frame.shape)
        self.assertFalse(np.array_equal(out[300, 100], frame[300, 100]))  # tinted where they stood
        self.assertTrue(np.array_equal(out[400, 600], frame[400, 600]))   # untouched far away


if __name__ == "__main__":
    unittest.main()
