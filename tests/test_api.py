import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DB_PATH = "data/storage/test_cloud_metrics.db"
os.environ["SERVER_DB_PATH"] = DB_PATH

if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
    except OSError:
        pass

from fastapi.testclient import TestClient
from server.app import app

class TestLiveMetricsAPI(unittest.TestCase):
    """Regression coverage for M0: /api/v1/live used to hardcode queue_length/
    avg_queue_wait_seconds/queue_alert_active to zero instead of reading them
    from the latest seeded telemetry rollup."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except OSError:
                pass

    def test_live_metrics_echoes_seeded_queue_fields(self):
        store_id = "test_store_api"
        payload = {
            "batch_size": 1,
            "exported_at": time.time(),
            "rollups": [{
                "store_id": store_id,
                "device_id": "test_mac_01",
                "camera_id": "cam_checkout",
                "timestamp_start": "2026-09-18 10:00:00",
                "timestamp_end": "2026-09-18 10:00:30",
                "in_count": 5,
                "out_count": 2,
                "current_occupancy": 3,
                "avg_dwell_seconds": 42.0,
                "queue_length": 4,
                "avg_queue_wait_seconds": 65.5,
                "queue_alert_active": 1
            }]
        }
        resp = self.client.post("/api/v1/telemetry", json=payload)
        self.assertEqual(resp.status_code, 200)

        live = self.client.get("/api/v1/live", params={"store_id": store_id})
        self.assertEqual(live.status_code, 200)
        data = live.json()

        self.assertEqual(data["queue_length"], 4)
        self.assertEqual(data["avg_queue_wait_seconds"], 65.5)
        self.assertTrue(data["queue_alert_active"])

if __name__ == "__main__":
    unittest.main()
