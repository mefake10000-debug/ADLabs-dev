"""Unit tests for parallel-box overlay geometry and OVERLAY_BOX_STYLE."""
import os
import unittest

from src.perception.tracker import Track
from src.visualizer.debug_overlay import (
    heading_shear_px,
    parallel_body_quad,
    parallel_footprint_quad,
    resolve_overlay_box_style,
)


class OverlayBoxStyleTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("OVERLAY_BOX_STYLE", None)

    def test_default_is_parallel(self):
        self.assertEqual(resolve_overlay_box_style({}), "parallel")

    def test_env_aabb(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "aabb"}), "aabb")

    def test_unknown_falls_back(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "obb"}), "parallel")


class ParallelGeometryTests(unittest.TestCase):
    def test_body_quad_is_parallelogram(self):
        bbox = [100.0, 50.0, 160.0, 220.0]
        shear = 18.0
        pts = parallel_body_quad(bbox, shear)
        self.assertEqual(pts.shape, (4, 2))
        # Top edge length == bottom edge length
        top = ((pts[1][0] - pts[0][0]) ** 2 + (pts[1][1] - pts[0][1]) ** 2) ** 0.5
        bot = ((pts[2][0] - pts[3][0]) ** 2 + (pts[2][1] - pts[3][1]) ** 2) ** 0.5
        self.assertAlmostEqual(float(top), float(bot), places=3)
        # Left and right sides share the same delta (parallel)
        left = (pts[3][0] - pts[0][0], pts[3][1] - pts[0][1])
        right = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
        self.assertAlmostEqual(float(left[0]), float(right[0]), places=3)
        self.assertAlmostEqual(float(left[1]), float(right[1]), places=3)

    def test_velocity_shear_leans_with_heading(self):
        t = Track(1, [100, 100, 160, 260], 0.9, 1.0)
        t.velocity = (40.0, 5.0)  # moving right
        s_right = heading_shear_px(t, 60.0)
        t.velocity = (-40.0, 5.0)
        s_left = heading_shear_px(t, 60.0)
        self.assertGreater(s_right, 0)
        self.assertLess(s_left, 0)

    def test_stationary_uses_isometric_lean(self):
        t = Track(2, [100, 100, 160, 260], 0.9, 1.0)
        t.velocity = (0.0, 0.0)
        s = heading_shear_px(t, 60.0)
        self.assertGreater(s, 0)
        self.assertLessEqual(s, 0.45 * 60.0)

    def test_footprint_quad_four_points(self):
        pts = parallel_footprint_quad([100, 50, 160, 220], 12.0)
        self.assertEqual(pts.shape, (4, 2))


if __name__ == "__main__":
    unittest.main()
