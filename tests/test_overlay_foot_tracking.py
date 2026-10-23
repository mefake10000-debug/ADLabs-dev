"""Unit tests for foot/skeleton overlay default and track foot API."""
import os
import unittest

from src.perception.tracker import Track
from src.perception.rtmpose_estimator import bbox_foot, foot_from_ankles, resolve_rtmpose_onnx
from src.visualizer.debug_overlay import resolve_overlay_box_style


class OverlayFootStyleTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("OVERLAY_BOX_STYLE", None)

    def test_default_is_foot(self):
        self.assertEqual(resolve_overlay_box_style({}), "foot")

    def test_env_styles(self):
        for style in ("foot", "skeleton", "parallel", "aabb"):
            self.assertEqual(
                resolve_overlay_box_style({"OVERLAY_BOX_STYLE": style}), style
            )

    def test_nvidia_alias_to_parallel(self):
        self.assertEqual(
            resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "nvidia"}), "parallel"
        )

    def test_unknown_falls_back_to_foot(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "obb"}), "foot")


class TrackFootTests(unittest.TestCase):
    def test_bbox_bottom_center_default(self):
        t = Track(1, [100.0, 50.0, 160.0, 220.0], 0.9, 1.0)
        self.assertAlmostEqual(t.foot_point[0], 130.0)
        self.assertAlmostEqual(t.foot_point[1], 220.0)
        self.assertEqual(t.ground_point, t.foot_point)

    def test_pose_foot_overrides(self):
        t = Track(2, [100.0, 50.0, 160.0, 220.0], 0.9, 1.0)
        t.set_pose(foot=(128.5, 218.0))
        self.assertAlmostEqual(t.foot_point[0], 128.5)
        self.assertAlmostEqual(t.foot_point[1], 218.0)

    def test_live_dict_fields(self):
        t = Track(7, [10.0, 20.0, 40.0, 80.0], 0.8, 10.0)
        t.dwell_s = 5.5
        row = t.to_live_dict()
        self.assertEqual(row["id"], 7)
        self.assertEqual(row["foot"], [25.0, 80.0])
        self.assertEqual(row["dwell_s"], 5.5)
        self.assertEqual(row["ground_point"], [25.0, 80.0])

    def test_ankle_foot_helper(self):
        kps = [[0, 0]] * 17
        kps[15] = [100.0, 200.0]
        kps[16] = [120.0, 210.0]
        foot = foot_from_ankles(kps, scores=[1.0] * 17)
        self.assertIsNotNone(foot)
        self.assertAlmostEqual(foot[0], 110.0)
        self.assertAlmostEqual(foot[1], 210.0)

    def test_bbox_foot_helper(self):
        self.assertEqual(bbox_foot([0, 0, 100, 50]), (50.0, 50.0))


class RTMPosePackTests(unittest.TestCase):
    def test_resolve_finds_pack_when_present(self):
        # May be None in CI without pack; presence is enough when downloaded.
        path = resolve_rtmpose_onnx()
        if path is not None:
            self.assertTrue(path.name.startswith("rtmpose-"))
            self.assertTrue(path.suffix == ".onnx")


if __name__ == "__main__":
    unittest.main()
