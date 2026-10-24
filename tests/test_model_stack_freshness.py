import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.perception.model_stack import build_model_stack


class ModelStackFreshnessTests(unittest.TestCase):
    def test_model_rows_wait_until_a_fresh_worker_snapshot_names_them(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for rel in (
                "models/yolo26n.pt",
                "models/yolo26s.pt",
                "models/pack/06-shelf/yoloe-v8s-seg-pf.pt",
                "models/pack/03-reid/osnet.onnx",
                "weights/clip/ViT-B-32.pt",
            ):
                path = base / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x" * 256)

            with patch.dict(os.environ, {
                "DETECTOR_BACKEND": "yolo26",
                "EDGE_PERF_MODE": "quality",
                "ENABLE_DEMOGRAPHICS": "0",
                "DEMOGRAPHICS_DPIA_OK": "0",
            }, clear=False):
                result = build_model_stack(str(base))

        rows = {row["key"]: row for row in result["models"]}
        for key in ("yolo26n", "yolo26s", "yoloe", "osnet_reid", "clip_vit_b32"):
            with self.subTest(model=key):
                self.assertNotEqual("LIVE", rows[key]["status"])
                self.assertNotEqual("ON", rows[key]["run_state"])

    def test_osnet_is_live_when_fresh_snapshot_confirms_it_in_fast_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            weights = base / "models/pack/03-reid/osnet_x0_25_msmt17.onnx"
            weights.parent.mkdir(parents=True)
            weights.write_bytes(b"x" * 256)
            live = base / "data/storage/live/cam_entrance_01.json"
            live.parent.mkdir(parents=True)
            live.write_text(
                '{"timestamp":"2099-10-23T00:00:00Z",'
                '"models":{"osnet_reid_enabled":true},'
                '"reid":{"active":true,"backend":"onnx_osnet"}}',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {
                "DETECTOR_BACKEND": "yolo26",
                "EDGE_PERF_MODE": "fast",
                "ENABLE_DEMOGRAPHICS": "0",
                "DEMOGRAPHICS_DPIA_OK": "0",
            }, clear=False):
                result = build_model_stack(str(base))

        rows = {row["key"]: row for row in result["models"]}
        self.assertEqual("LIVE", rows["osnet_reid"]["status"])
        self.assertEqual("ON", rows["osnet_reid"]["run_state"])


if __name__ == "__main__":
    unittest.main()
