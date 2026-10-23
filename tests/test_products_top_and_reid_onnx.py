"""products_top live field + SoftReID ONNX session-scoped behaviour."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.product_interest import ProductInterestAnalyzer
from src.perception.reid import SoftReIdExtractor, SoftReIdGallery
from src.perception.world_detector import OpenVocabProductDetector


class _FakeTrack:
    def __init__(self, tid: int, foot):
        self.track_id = tid
        self.foot_point = foot
        self.bbox = [foot[0] - 20, foot[1] - 80, foot[0] + 20, foot[1]]


class TestProductsTopShape(unittest.TestCase):
    def test_snapshot_maps_to_products_top(self):
        analyzer = ProductInterestAnalyzer(engagement_radius_px=200.0, min_dwell_seconds=0.5)
        tracks = [_FakeTrack(1, (100.0, 100.0))]
        dets = [{"label": "handbag", "bbox": [90.0, 80.0, 110.0, 120.0]}]
        analyzer.observe(dets, tracks, 1.0)
        analyzer.observe(dets, tracks, 2.0)
        snap = analyzer.snapshot()
        products = snap.get("products") or []
        self.assertTrue(products)
        products_top = [
            {
                "category": p["category"],
                "viewers": int(p.get("viewers", 0) or 0),
                "avg_dwell_seconds": float(p.get("avg_dwell_seconds", 0.0) or 0.0),
            }
            for p in products[:8]
        ]
        self.assertEqual(products_top[0]["category"], "handbag")
        self.assertGreaterEqual(products_top[0]["viewers"], 1)


class TestPromptFreeLabelMap(unittest.TestCase):
    def test_maps_yoloe_names(self):
        self.assertEqual(
            OpenVocabProductDetector._map_prompt_free_label("beer bottle", ["bottle", "shoe"]),
            "bottle",
        )
        self.assertEqual(
            OpenVocabProductDetector._map_prompt_free_label("backpack", ["handbag", "backpack"]),
            "backpack",
        )
        self.assertIsNone(
            OpenVocabProductDetector._map_prompt_free_label("abacus", ["shoe", "handbag"])
        )


class TestSoftReIdOnnxSession(unittest.TestCase):
    def test_onnx_loads_when_enabled(self):
        root = Path(__file__).resolve().parents[1]
        onnx = root / "models" / "pack" / "03-reid" / "osnet_x0_25_msmt17.onnx"
        if not onnx.is_file():
            self.skipTest("OSNet ONNX not on disk — run scripts/download/download_pack_models.py")
        extractor = SoftReIdExtractor(
            weights=str(onnx),  # resolve will also find pth; force onnx via onnx_weights
            onnx_weights=str(onnx),
            enabled=True,
            base_dir=str(root),
        )
        # Prefer ONNX when torchreid missing — either backend is fine if active
        status = extractor.status()
        self.assertTrue(status["enabled"])
        self.assertTrue(status["session_scoped"])
        self.assertFalse(status["cross_cam_fusion"])
        if not status["active"]:
            self.skipTest(f"ReID inactive: {status.get('load_error')}")
        self.assertIn(status["backend"], ("onnx_osnet", "onnx_youtu", "torchreid"))

        crop = np.zeros((120, 60, 3), dtype=np.uint8)
        crop[:] = (40, 80, 120)
        feats = extractor.extract_crops([crop, crop])
        self.assertIsNotNone(feats)
        self.assertEqual(feats.shape[0], 2)
        # L2-normalized
        norms = np.linalg.norm(feats, axis=1)
        np.testing.assert_allclose(norms, np.ones_like(norms), atol=1e-3)

        gallery = SoftReIdGallery(max_age_seconds=60.0)
        gallery.add(
            __import__("src.perception.reid", fromlist=["ReIdEmbedding"]).ReIdEmbedding(
                camera_id="cam_a",
                track_id=1,
                embedding=feats[0],
                capture_ts_utc=100.0,
            )
        )
        self.assertEqual(gallery.size(), 1)
        gallery.prune(200.0)  # beyond ttl
        self.assertEqual(gallery.size(), 0)


if __name__ == "__main__":
    unittest.main()
