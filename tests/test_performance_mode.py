"""Unit tests for live FPS performance presets."""
import os
import unittest

from src.perception.performance import (
    BALANCED_PRESET,
    FAST_PRESET,
    QUALITY_PRESET,
    limit_cameras,
    resolve_perf_mode,
    resolve_performance,
)


class PerformanceModeTests(unittest.TestCase):
    def tearDown(self):
        for key in (
            "EDGE_PERF_MODE",
            "EDGE_MAX_CAMERAS",
            "EDGESIGHT_DETECT_MODEL",
            "DETECTOR_BACKEND",
            "RFDETR_VARIANT",
            "RFDETR_WEIGHTS",
        ):
            os.environ.pop(key, None)

    def test_default_is_detect(self):
        self.assertEqual(resolve_perf_mode({}), "detect")
        resolved = resolve_performance({})
        self.assertEqual(resolved["mode"], "detect")
        self.assertTrue(str(resolved["model_name"]).endswith("yolo26s.pt") or str(resolved["model_name"]).endswith("yolo26n.pt"))
        self.assertEqual(resolved["imgsz"], 640)
        self.assertEqual(resolved["infer_every_n"], 2)
        self.assertFalse(resolved["enrichment"])
        self.assertEqual(resolved["detector_backend"], "yolo26")
        self.assertGreaterEqual(resolved["person_conf"], 0.20)
        self.assertLessEqual(resolved["person_conf"], 0.25)
        self.assertGreater(resolved["object_conf"], resolved["person_conf"])
        self.assertGreaterEqual(resolved["track_thresh"], resolved["person_conf"])
        self.assertLessEqual(resolved["track_thresh"], 0.30)

    def test_balanced_still_available(self):
        os.environ["EDGE_PERF_MODE"] = "balanced"
        resolved = resolve_performance({"performance": {"mode": "detect", "imgsz": 640}})
        self.assertEqual(resolved["mode"], "balanced")
        self.assertEqual(resolved["model_name"], BALANCED_PRESET["model_name"])
        self.assertEqual(resolved["imgsz"], 416)
        self.assertEqual(resolved["infer_every_n"], 2)

    def test_fast_preset_more_aggressive(self):
        os.environ["EDGE_PERF_MODE"] = "fast"
        resolved = resolve_performance({})
        self.assertEqual(resolved["mode"], "fast")
        self.assertEqual(resolved["model_name"], FAST_PRESET["model_name"])
        self.assertEqual(resolved["imgsz"], 320)
        self.assertEqual(resolved["infer_every_n"], 3)
        self.assertFalse(resolved["enrichment"])

    def test_env_quality_wins(self):
        os.environ["EDGE_PERF_MODE"] = "quality"
        resolved = resolve_performance({"performance": {"mode": "balanced"}})
        self.assertEqual(resolved["mode"], "quality")
        self.assertEqual(resolved["model_name"], QUALITY_PRESET["model_name"])
        self.assertEqual(resolved["imgsz"], 640)
        self.assertTrue(resolved["enrichment"])
        self.assertEqual(resolved["detector_backend"], "yolo26")

    def test_fast_ignores_detect_yaml_letterbox(self):
        os.environ["EDGE_PERF_MODE"] = "fast"
        resolved = resolve_performance({
            "performance": {"mode": "detect", "imgsz": 640, "infer_every_n": 2},
            "perception": {"model_name": "models/yolo26s.pt", "imgsz": 640},
        })
        self.assertEqual(resolved["mode"], "fast")
        self.assertEqual(resolved["imgsz"], FAST_PRESET["imgsz"])
        self.assertEqual(resolved["infer_every_n"], FAST_PRESET["infer_every_n"])
        self.assertEqual(resolved["model_name"], FAST_PRESET["model_name"])

    def test_rfdetr_opt_in_only(self):
        os.environ["EDGE_PERF_MODE"] = "quality"
        os.environ["DETECTOR_BACKEND"] = "rfdetr"
        resolved = resolve_performance({})
        self.assertEqual(resolved["detector_backend"], "rfdetr")

    def test_detect_model_env_override(self):
        os.environ["EDGESIGHT_DETECT_MODEL"] = "models/pack/01-detection/yolo11n.pt"
        resolved = resolve_performance({"performance": {"mode": "balanced"}})
        self.assertEqual(resolved["model_name"], "models/pack/01-detection/yolo11n.pt")

    def test_max_cameras_limit(self):
        cams = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        self.assertEqual(len(limit_cameras(cams, None)), 3)
        self.assertEqual([c["id"] for c in limit_cameras(cams, 1)], ["a"])
        os.environ["EDGE_MAX_CAMERAS"] = "2"
        resolved = resolve_performance({})
        self.assertEqual(resolved["max_cameras"], 2)


if __name__ == "__main__":
    unittest.main()
