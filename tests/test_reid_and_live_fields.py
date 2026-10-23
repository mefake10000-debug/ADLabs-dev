"""Soft ReID status + /api/v1/live per_camera / clock_sync honesty fields."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.reid import SoftReIdExtractor


class TestSoftReIdDefaultOff(unittest.TestCase):
    def test_explicit_off_reports_weights_without_loading(self):
        """models.reid.enabled: false keeps extractor inactive even when weights exist."""
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
        self.assertTrue(status.get("session_scoped", True))
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
            "video_loop": {
                "loop_count": 3,
                "is_simulated": True,
                "unique_this_pass": 7,
                "unique_total_all_passes": 18,
                "counting_mode": "per_pass (sample video replays)",
            },
        }
        with open(os.path.join(live_dir, "cam_entrance_01.json"), "w") as f:
            json.dump(cam, f)
        with open(os.path.join(live_dir, "store.json"), "w") as f:
            json.dump({**cam, "cameras": ["cam_entrance_01"], "source": "live_snapshot"}, f)

        live = self.client.get("/api/v1/live").json()
        self.assertEqual(live.get("source"), "live_snapshot")
        self.assertEqual(live.get("people_now"), 3)
        self.assertTrue(any(c.get("camera_id") == "cam_entrance_01" for c in live.get("per_camera", [])))
        self.assertEqual(live.get("video_loop", {}).get("loop_count"), 3)
        self.assertEqual(live.get("video_loop_by_camera", {}).get("cam_entrance_01", {}).get("is_simulated"), True)

    def test_simulated_footfall_uses_latest_pass_only(self):
        """Replay rollups from earlier loops must not inflate today's sample-video footfall."""
        now = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            for loop_count, in_count in ((1, 4), (1, 2), (2, 3)):
                conn.execute(
                    """INSERT INTO telemetry_rollups (
                        store_id, device_id, camera_id, timestamp_start, timestamp_end,
                        in_count, out_count, current_occupancy, avg_dwell_seconds,
                        queue_length, avg_queue_wait_seconds, queue_alert_active,
                        is_simulated, loop_count
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 1, ?)""",
                    ("store_mumbai_001", "test-edge", "sim_cam", now, now, in_count, loop_count),
                )
            conn.commit()

        live = self.client.get("/api/v1/live?camera_id=sim_cam").json()
        self.assertEqual(live.get("total_visitors"), 3)

    def test_live_zero_tripwire_not_replaced_by_db_rollup(self):
        """Fresh snap with IN=0 must win — never `0 or day_SUM` (~200 fake In)."""
        live_dir = os.path.join(os.path.dirname(self.db_path), "live")
        os.makedirs(live_dir, exist_ok=True)
        now = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO telemetry_rollups (
                    store_id, device_id, camera_id, timestamp_start, timestamp_end,
                    in_count, out_count, current_occupancy, avg_dwell_seconds,
                    queue_length, avg_queue_wait_seconds, queue_alert_active,
                    is_simulated, loop_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0)""",
                ("store_mumbai_001", "test-edge", "cam_entrance_01", now, now, 200, 111),
            )
            conn.commit()

        cam = {
            "camera_id": "cam_entrance_01",
            "people_now": 4,
            "net_occupancy": 4,
            "queue_length": 0,
            "avg_dwell_seconds": 8.0,
            "total_visitors": 0,
            "total_exits": 0,
            "timestamp": now,
            "infer_fps": 5.0,
            "tripwires": [{"id": "entrance", "name": "Entrance", "in_count": 0, "out_count": 0}],
        }
        with open(os.path.join(live_dir, "cam_entrance_01.json"), "w") as f:
            json.dump(cam, f)
        with open(os.path.join(live_dir, "store.json"), "w") as f:
            json.dump({**cam, "cameras": ["cam_entrance_01"], "source": "live_snapshot"}, f)

        live = self.client.get("/api/v1/live").json()
        self.assertEqual(live.get("source"), "live_snapshot")
        self.assertEqual(live.get("people_now"), 4)
        self.assertEqual(live.get("total_visitors"), 0)
        self.assertEqual(live.get("total_exits"), 0)

    def test_present_matches_tracks_and_day_rollup_stays_off_live(self):
        """Present is len(track_ids). In/Out are tripwire counts, not the day SUM.
        Lifetime product viewers and enrichment-off zeros are withheld."""
        live_dir = os.path.join(os.path.dirname(self.db_path), "live")
        os.makedirs(live_dir, exist_ok=True)
        now = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO telemetry_rollups (
                    store_id, device_id, camera_id, timestamp_start, timestamp_end,
                    in_count, out_count, current_occupancy, avg_dwell_seconds,
                    queue_length, avg_queue_wait_seconds, queue_alert_active,
                    is_simulated, loop_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 9, 0, 0, 0, 0, 0, 0)""",
                ("store_mumbai_001", "test-edge", "cam_entrance_01", now, now, 355, 173),
            )
            conn.commit()

        cam = {
            "camera_id": "cam_entrance_01",
            "people_now": 99,
            "net_occupancy": 99,
            "total_visitors": 355,
            "total_exits": 173,
            "timestamp": now,
            "track_ids": [4, 8, 15],
            "tripwires": [{"id": "entrance", "name": "Entrance", "in_count": 2, "out_count": 1}],
            "models": {"person_detector": "yolo26n", "enrichment": False},
            "engagement": {"engaged_ratio": 0.0, "facing_ratio": 0.0},
            "products_top": [
                {"category": "handbag", "viewers": 47305, "detections": 187487, "avg_dwell_seconds": 10.5}
            ],
        }
        with open(os.path.join(live_dir, "cam_entrance_01.json"), "w") as f:
            json.dump(cam, f)
        with open(os.path.join(live_dir, "store.json"), "w") as f:
            json.dump(
                {
                    "cameras": ["cam_entrance_01"],
                    "people_now": 99,
                    "total_visitors": 355,
                    "total_exits": 173,
                    "timestamp": now,
                    "source": "live_snapshot",
                    "models": {"person_detector": "yolo26n", "enrichment": False},
                    "engagement": {"engaged_ratio": 0.0, "facing_ratio": 0.0},
                    "products_top": [
                        {
                            "category": "handbag",
                            "viewers": 47305,
                            "detections": 187487,
                            "avg_dwell_seconds": 10.5,
                        }
                    ],
                },
                f,
            )

        live = self.client.get("/api/v1/live").json()
        self.assertEqual(live.get("source"), "live_snapshot")
        self.assertEqual(live.get("present_binding"), "active_tracks")
        self.assertEqual(live.get("track_ids"), [4, 8, 15])
        self.assertEqual(live.get("active_tracks"), 3)
        self.assertEqual(live.get("people_now"), 3)
        self.assertEqual(live.get("inout_binding"), "session_tripwire")
        self.assertEqual(live.get("total_visitors"), 2)
        self.assertEqual(live.get("total_exits"), 1)
        self.assertNotEqual(live.get("total_visitors"), 355)
        self.assertIsNone(live.get("products_top"))
        self.assertEqual(live.get("products_top_withheld"), "lifetime_rollup")
        self.assertIsNone(live.get("engagement"))


if __name__ == "__main__":
    unittest.main()
