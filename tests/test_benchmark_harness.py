import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "benchmark"))

import benchmark_tracking as bt


class _Tensor:
    def __init__(self, v):
        self.v = v

    def tolist(self):
        return self.v


class _Box:
    def __init__(self, w, h):
        self.xyxy = [_Tensor([0, 0, w, h])]


class _FakeModel:
    """(w, h, conf): two good people, one tiny, one wide-and-short, one only visible at low confidence."""
    BOXES = [(60, 160, .9), (70, 200, .8), (20, 40, .7), (200, 80, .6), (50, 150, .3)]

    def predict(self, source, classes, conf, iou, device, verbose):
        class R:
            boxes = [_Box(w, h) for w, h, c in _FakeModel.BOXES if c >= conf]
        return [R()]


class _Detector:
    model = _FakeModel()
    iou_thresh, device = .45, "cpu"
    min_height, min_width, min_area = 95, 30, 3000
    min_aspect_ratio, max_aspect_ratio = 1.0, 4.2


class TestStageBreakdown(unittest.TestCase):

    def test_counts_each_stage(self):
        stages = bt.stage_breakdown(_Detector(), None, conf_thresh=0.5)
        self.assertEqual(stages["yolo_low_conf"], 5)
        self.assertEqual(stages["yolo_at_conf"], 4)
        self.assertEqual(stages["rejected_size"], 2)      # 20x40 and the 200x80 (height < 95)
        self.assertEqual(stages["rejected_aspect"], 0)

    def test_aspect_rejection_is_separate_from_size(self):
        _FakeModel.BOXES.append((250, 120, .9))            # big enough, but wider than tall
        try:
            stages = bt.stage_breakdown(_Detector(), None, conf_thresh=0.5)
        finally:
            _FakeModel.BOXES.pop()
        self.assertEqual(stages["rejected_aspect"], 1)

    def test_returns_none_when_yolo_not_loaded(self):
        detector = _Detector()
        detector.model = None
        self.assertIsNone(bt.stage_breakdown(detector, None, conf_thresh=0.5))

    def test_checkpoint_parsing_supports_both_ground_truth_formats(self):
        multi = {"method": "point-in-time headcount",
                 "checkpoints": [{"frame_index": 10, "expected_visible_people": 3}, {"frame_index": 20, "expected_visible_people": 5}]}
        single = {"method": "point-in-time headcount", "frame_index": 7, "expected_visible_people": 4}
        self.assertEqual(bt.checkpoints_from(multi), {10: 3, 20: 5})
        self.assertEqual(bt.checkpoints_from(single), {7: 4})
        self.assertEqual(bt.checkpoints_from({"method": "tripwire crossings"}), {})


if __name__ == "__main__":
    unittest.main()
