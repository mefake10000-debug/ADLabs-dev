"""Unit tests for RF-DETR / YOLO26 detector backend selection (no weight download)."""
import os
import unittest

from src.perception.detector_backend import (
    BACKEND_RFDETR,
    BACKEND_YOLO26,
    RFDETR_WEIGHT_IDS,
    resolve_detector_backend,
    resolve_rfdetr_variant,
    resolve_rfdetr_weights,
)
from src.perception.model_stack import build_model_stack
from src.perception.performance import resolve_performance


class DetectorBackendTests(unittest.TestCase):
    def tearDown(self):
        for key in (
            "EDGE_PERF_MODE",
            "DETECTOR_BACKEND",
            "RFDETR_VARIANT",
            "RFDETR_WEIGHTS",
            "RFDETR_RUNTIME_LOADED",
            "EDGESIGHT_DETECT_MODEL",
        ):
            os.environ.pop(key, None)

    def test_fast_defaults_to_yolo26(self):
        os.environ["EDGE_PERF_MODE"] = "fast"
        self.assertEqual(resolve_detector_backend({}), BACKEND_YOLO26)
        resolved = resolve_performance({})
        self.assertEqual(resolved["detector_backend"], BACKEND_YOLO26)

    def test_quality_defaults_to_ultralytics_yolo26(self):
        """Accuracy path stays Ultralytics; RF-DETR is opt-in only."""
        os.environ["EDGE_PERF_MODE"] = "quality"
        self.assertEqual(resolve_detector_backend({}), BACKEND_YOLO26)
        resolved = resolve_performance({})
        self.assertEqual(resolved["detector_backend"], BACKEND_YOLO26)
        self.assertEqual(resolved["model_name"], "models/yolo26s.pt")
        self.assertEqual(resolved["imgsz"], 640)

    def test_env_backend_wins(self):
        os.environ["EDGE_PERF_MODE"] = "quality"
        os.environ["DETECTOR_BACKEND"] = "yolo26"
        self.assertEqual(resolve_detector_backend({}), BACKEND_YOLO26)

        os.environ["EDGE_PERF_MODE"] = "fast"
        os.environ["DETECTOR_BACKEND"] = "rfdetr"
        self.assertEqual(resolve_detector_backend({}), BACKEND_RFDETR)

        os.environ["DETECTOR_BACKEND"] = "yolo11"
        self.assertEqual(resolve_detector_backend({}), BACKEND_YOLO26)

    def test_variant_and_weight_ids(self):
        self.assertEqual(RFDETR_WEIGHT_IDS["nano"], "rf-detr-nano.pth")
        self.assertEqual(RFDETR_WEIGHT_IDS["small"], "rf-detr-small.pth")
        os.environ["RFDETR_VARIANT"] = "small"
        self.assertEqual(resolve_rfdetr_variant(), "small")
        self.assertEqual(resolve_rfdetr_weights("small"), "rf-detr-small.pth")

    def test_stack_rfdetr_row_packed_or_off(self):
        stack = build_model_stack()
        keys = {m["key"] for m in stack["models"]}
        self.assertIn("rfdetr", keys)
        self.assertNotIn("apache_detector_swap", keys)
        row = next(m for m in stack["models"] if m["key"] == "rfdetr")
        self.assertIn(row["status"], ("LIVE", "PACKED", "OFF"))
        self.assertEqual(row["license"], "Apache-2.0")
        self.assertEqual(stack["env"]["DETECTOR_BACKEND"], BACKEND_YOLO26)

    def test_stack_live_when_selected_and_flagged(self):
        os.environ["DETECTOR_BACKEND"] = "rfdetr"
        os.environ["RFDETR_RUNTIME_LOADED"] = "1"
        stack = build_model_stack()
        row = next(m for m in stack["models"] if m["key"] == "rfdetr")
        # LIVE if import+disk OR runtime flag; without package may stay PACKED.
        self.assertIn(row["status"], ("LIVE", "PACKED"))
        self.assertEqual(stack["env"]["DETECTOR_BACKEND"], BACKEND_RFDETR)


if __name__ == "__main__":
    unittest.main()
