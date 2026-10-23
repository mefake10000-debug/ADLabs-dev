"""Unit tests for live FPS performance presets."""
import os
import unittest

from src.perception.performance import (
    FAST_PRESET,
    QUALITY_PRESET,
    limit_cameras,
    resolve_perf_mode,
    resolve_performance,
)


class PerformanceModeTests(unittest.TestCase):
    def tearDown(self):
        for key in ("EDGE_PERF_MODE", "EDGE_MAX_CAMERAS", "EDGESIGHT_DETECT_MODEL"):
            os.environ.pop(key, None)

    def test_default_is_fast(self):
        self.assertEqual(resolve_perf_mode({}), "fast")
        resolved = resolve_performance({})
        self.assertEqual(resolved["mode"], "fast")
        self.assertEqual(resolved["model_name"], FAST_PRESET["model_name"])
        self.assertEqual(resolved["imgsz"], 320)
        self.assertFalse(resolved["enrichment"])

    def test_env_quality_wins(self):
        os.environ["EDGE_PERF_MODE"] = "quality"
        resolved = resolve_performance({"performance": {"mode": "fast"}})
        self.assertEqual(resolved["mode"], "quality")
        self.assertEqual(resolved["model_name"], QUALITY_PRESET["model_name"])
        self.assertEqual(resolved["imgsz"], 640)
        self.assertTrue(resolved["enrichment"])

    def test_detect_model_env_override(self):
        os.environ["EDGESIGHT_DETECT_MODEL"] = "models/pack/01-detection/yolo11n.pt"
        resolved = resolve_performance({"performance": {"mode": "fast"}})
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
