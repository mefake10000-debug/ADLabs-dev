"""Soft ReID status + /api/v1/live per_camera / clock_sync honesty fields."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.reid import SoftReIdExtractor


class TestSoftReIdDefaultOff(unittest.TestCase):
    def test_default_off_reports_weights_without_loading(self):
        root = Path(__file__).resolve().parents[1]
        verified = (
            root / "models" / "pack" / "03-reid"
            / "osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"
        )
        legacy = root / "models" / "pack" / "03-reid" / "osnet-x0_25" / "osnet_x0_25_msmt17.pt"
        if verified.is_file():
            weights = str(verified)
        elif legacy.is_file():
            weights = str(legacy)
        else:
            weights = str(verified)
        extractor = SoftReIdExtractor(
            weights=weights,
            enabled=False,
            base_dir=str(root),
        )
        status = extractor.status()
        self.assertFalse(status["enabled"])
        self.assertFalse(status["active"])
        self.assertFalse(status["cross_cam_fusion"])
        self.assertIn("no face id", status["note"].lower())


class TestLivePerCameraAndClockSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmpdir.name, "t.db")
        cls.config_path = os.path.join(cls._tmpdir.name, "cameras.yaml")
        os.environ["SERVER_DB_PATH"] = cls.db_path
        os.environ["CAMERAS_CONFIG"] = cls.config_path
        # Import after env so app picks up paths
        import server.app as server_app
        from fastapi.testclient import TestClient
        from server.app import app, init_db

        cls.server_app = server_app
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_live_includes_per_camera_and_occupancy_mode(self):
        live = self.client.get("/api/v1/live").json()
        self.assertIn("per_camera", live)
        self.assertIn("occupancy_mode", live)
        self.assertIsInstance(live["per_camera"], list)

    def test_device_health_clock_sync_stub(self):
        health = self.client.get("/api/v1/device/health").json()
        self.assertIn("clock_sync", health)
        self.assertIsNone(health["clock_sync"]["ntp_ok"])
        self.assertIn("reid", health)
        self.assertFalse(health["reid"]["cross_cam_fusion"])

    def test_live_prefers_fresh_snapshot_per_camera(self):
        live_dir = os.path.join(os.path.dirname(self.db_path), "live")
        os.makedirs(live_dir, exist_ok=True)
        cam = {
            "camera_id": "cam_entrance_01",
            "people_now": 3,
            "net_occupancy": 3,
            "queue_length": 1,
            "avg_dwell_seconds": 12.0,
            "total_visitors": 9,
            "total_exits": 6,
            "timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "infer_fps": 11.5,
        }
        with open(os.path.join(live_dir, "cam_entrance_01.json"), "w") as f:
            json.dump(cam, f)
        with open(os.path.join(live_dir, "store.json"), "w") as f:
            json.dump({**cam, "cameras": ["cam_entrance_01"], "source": "live_snapshot"}, f)

        live = self.client.get("/api/v1/live").json()
        self.assertEqual(live.get("source"), "live_snapshot")
        self.assertEqual(live.get("people_now"), 3)
        self.assertTrue(any(c.get("camera_id") == "cam_entrance_01" for c in live.get("per_camera", [])))


if __name__ == "__main__":
    unittest.main()
