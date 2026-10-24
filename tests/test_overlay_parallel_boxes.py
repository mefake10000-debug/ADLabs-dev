"""Unit tests for parallel/nvidia overlay geometry and OVERLAY_BOX_STYLE."""
import os
import unittest

from src.perception.tracker import Track
from src.visualizer.debug_overlay import (
    heading_shear_px,
    inset_parallel_quad,
    object_label,
    parallel_body_quad,
    parallel_footprint_quad,
    person_label,
    resolve_overlay_box_style,
)


class OverlayBoxStyleTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("OVERLAY_BOX_STYLE", None)

    def test_default_is_aabb(self):
        self.assertEqual(resolve_overlay_box_style({}), "aabb")

    def test_env_aabb(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "aabb"}), "aabb")

    def test_nvidia_optional(self):
        self.assertEqual(
            resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "nvidia"}), "nvidia"
        )
        self.assertEqual(
            resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "pallet"}), "nvidia"
        )

    def test_parallel_still_valid(self):
        self.assertEqual(
            resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "parallel"}), "parallel"
        )

    def test_unknown_falls_back(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "obb"}), "aabb")


class ParallelGeometryTests(unittest.TestCase):
    def test_body_quad_is_parallelogram(self):
        bbox = [100.0, 50.0, 160.0, 220.0]
        shear = 18.0
        pts = parallel_body_quad(bbox, shear)
        self.assertEqual(pts.shape, (4, 2))
        top = ((pts[1][0] - pts[0][0]) ** 2 + (pts[1][1] - pts[0][1]) ** 2) ** 0.5
        bot = ((pts[2][0] - pts[3][0]) ** 2 + (pts[2][1] - pts[3][1]) ** 2) ** 0.5
        self.assertAlmostEqual(float(top), float(bot), places=3)
        left = (pts[3][0] - pts[0][0], pts[3][1] - pts[0][1])
        right = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
        self.assertAlmostEqual(float(left[0]), float(right[0]), places=3)
        self.assertAlmostEqual(float(left[1]), float(right[1]), places=3)

    def test_velocity_shear_leans_with_heading(self):
        t = Track(1, [100, 100, 160, 260], 0.9, 1.0)
        t.velocity = (40.0, 5.0)
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

    def test_inset_stays_parallelogram(self):
        body = parallel_body_quad([100.0, 50.0, 160.0, 220.0], 18.0)
        inner = inset_parallel_quad(body, inset=4.0)
        self.assertEqual(inner.shape, (4, 2))


class LabelRulesTests(unittest.TestCase):
    def test_person_label_priority(self):
        t = Track(7, [10, 10, 40, 80], 0.9, 1.0)
        self.assertEqual(person_label(t), "person ID:7")
        t.dwell_s = 3.2
        self.assertIn("person ID:7", person_label(t))
        self.assertIn("3s", person_label(t))

    def test_object_label_from_class_name(self):
        self.assertEqual(object_label({"label": "handbag"}), "handbag")
        self.assertEqual(object_label({"class_name": "bottle"}), "bottle")
        self.assertEqual(object_label({"class_id": 39}), "class_39")


if __name__ == "__main__":
    unittest.main()
