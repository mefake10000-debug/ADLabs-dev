"""Unit tests for foot/skeleton overlay default and track foot API."""
import os
import unittest

from src.perception.tracker import Track
from src.perception.rtmpose_estimator import bbox_foot, foot_from_ankles, resolve_rtmpose_onnx
from src.visualizer import debug_overlay
from src.visualizer.debug_overlay import resolve_overlay_box_style


class OverlayFootStyleTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("OVERLAY_BOX_STYLE", None)

    def test_default_is_clean_aabb(self):
        self.assertEqual(resolve_overlay_box_style({}), "aabb")

    def test_env_styles(self):
        for style in ("foot", "skeleton", "nvidia", "parallel", "aabb"):
            self.assertEqual(
                resolve_overlay_box_style({"OVERLAY_BOX_STYLE": style}), style
            )

    def test_pallet_alias_to_nvidia(self):
        self.assertEqual(
            resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "pallet"}), "nvidia"
        )

    def test_unknown_falls_back_to_clean_aabb(self):
        self.assertEqual(resolve_overlay_box_style({"OVERLAY_BOX_STYLE": "obb"}), "aabb")

    def test_person_boxes_are_clipped_to_the_frame(self):
        clip = getattr(debug_overlay, "clip_bbox_to_frame", None)
        self.assertTrue(callable(clip), "clean live boxes must share a clipping helper")
        self.assertEqual(clip([-10, 8, 120, 100], 100, 80), (0, 8, 99, 79))
        self.assertIsNone(clip([40, 50, 20, 60], 100, 80))

    def test_clean_aabb_label_is_short_and_does_not_repeat_person_or_dwell_text(self):
        label = getattr(debug_overlay, "clean_person_label", None)
        self.assertTrue(callable(label), "AABB labels should use a dedicated compact formatter")
        track = Track(22, [10, 10, 50, 80], 0.9, 1.0)
        track.dwell_s = 28
        self.assertEqual(label(track), "ID:22")

    def test_aabb_live_style_has_person_boxes_but_no_default_foot_or_object_clutter(self):
        if debug_overlay.cv2 is None or debug_overlay.np is None:
            self.skipTest("OpenCV/numpy unavailable")
        track = Track(7, [10, 10, 50, 80], 0.9, 1.0)
        track.history = [(20, 60, 1.0), (20, 70, 1.1), (20, 80, 1.2)]
        frame = debug_overlay.np.zeros((100, 100, 3), dtype=debug_overlay.np.uint8)
        rendered = debug_overlay.DebugOverlay.draw_pipeline(
            frame=frame,
            tracks=[track],
            tripwires=[],
            zones=[],
            queues=[],
            fps=12,
            infer_fps=3,
            box_style="aabb",
            objects=[{"bbox": [60, 55, 90, 90], "label": "crate"}],
        )
        self.assertGreater(int(rendered[50, 10, 1]), 200)
        self.assertGreater(int(rendered[50, 10, 2]), 200)
        self.assertEqual(int(rendered[50, 10, 0]), 0)
        self.assertNotEqual(tuple(int(v) for v in rendered[80, 30]), debug_overlay.FOOT_COLOR)
        self.assertEqual(tuple(int(v) for v in rendered[60, 60]), (0, 0, 0))

    def test_foot_style_keeps_visible_person_box_with_foot_mark(self):
        if debug_overlay.cv2 is None or debug_overlay.np is None:
            self.skipTest("OpenCV/numpy unavailable")
        track = Track(7, [10, 10, 50, 80], 0.9, 1.0)
        frame = debug_overlay.np.zeros((100, 100, 3), dtype=debug_overlay.np.uint8)
        rendered = debug_overlay.DebugOverlay.draw_pipeline(
            frame=frame,
            tracks=[track],
            tripwires=[],
            zones=[],
            queues=[],
            box_style="foot",
        )
        self.assertGreater(int(rendered[45, 10, 1]), 200)
        self.assertGreater(int(rendered[45, 10, 2]), 200)
        self.assertEqual(tuple(int(v) for v in rendered[80, 30]), debug_overlay.FOOT_COLOR)


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

class MovingPoseFootTests(unittest.TestCase):
    def test_cached_ankles_move_with_detection_between_pose_passes(self):
        t = Track(1, [100, 50, 160, 220], 0.9, 1.0)
        t.set_pose(foot=(128, 218), keypoints_xy=[[128, 218]])
        t.update([120, 60, 180, 230], 0.9, 2.0)
        self.assertEqual(t.foot_point, (148, 228))
        self.assertEqual(t.keypoints_xy, [[148, 228]])
        self.assertEqual(t.history[-1], (148, 228, 2.0))

class PoseAnalyticsParityTests(unittest.TestCase):
    def test_pose_refinement_updates_tripwire_history_same_frame(self):
        t=Track(1,[100,50,160,220],.9,1)
        t.set_pose(foot=(128,218))
        self.assertEqual(t.history[-1],(128,218,1))
