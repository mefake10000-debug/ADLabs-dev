"""Unit tests for foot/skeleton overlay default and track foot API."""
import os
import unittest

from src.perception.tracker import Track
from src.perception.rtmpose_estimator import bbox_foot, foot_from_ankles, resolve_rtmpose_onnx
from src.visualizer.debug_overlay import DebugOverlay, person_annotator, resolve_overlay_box_style


class OverlayFootStyleTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("OVERLAY_BOX_STYLE", None)

    def test_default_is_foot(self):
        self.assertEqual(resolve_overlay_box_style({}), "foot")

    def test_env_styles(self):
        for style in ("foot", "skeleton", "nvidia", "parallel", "aabb"):
            self.assertEqual(
                resolve_overlay_box_style({"OVERLAY_BOX_STYLE": style}), style
            )

    def test_pallet_alias_to_nvidia(self):
        self.assertEqual(
            resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "pallet"}), "nvidia"
        )

    def test_unknown_falls_back_to_foot(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "obb"}), "foot")

    def test_box_styles_do_not_stack_the_foot(self):
        self.assertEqual(person_annotator("foot"), "foot")
        self.assertEqual(person_annotator("skeleton"), "foot+skeleton")
        self.assertEqual(person_annotator("nvidia"), "nvidia")
        self.assertEqual(person_annotator("pallet"), "nvidia")
        self.assertNotIn("foot", person_annotator("aabb"))

    def test_foot_does_not_also_stroke_the_person_box(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy missing")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        person = Track(1, [200, 100, 280, 320], 0.9, 1.0)
        objects = [{"bbox": [400, 80, 470, 160], "label": "bottle"}]
        foot = DebugOverlay.draw_pipeline(
            frame, [person], [], [], [], box_style="foot", objects=objects,
        )
        if foot is frame:
            self.skipTest("cv2 missing")
        self.assertGreater(int(foot[320, 240, 2]), 200)  # red foot
        self.assertEqual(int(foot[200, 200].sum()), 0)  # no person rectangle
        self.assertGreater(int(foot[120, 400].sum()), 0)  # separate object layer
        boxed = DebugOverlay.draw_pipeline(
            frame, [person], [], [], [], box_style="aabb", objects=objects,
        )
        self.assertGreater(int(boxed[200, 200].sum()), 0)
        b, g, r = [int(v) for v in boxed[320, 240]]
        self.assertFalse(r > 200 and g < 40 and b < 40)


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
