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

class TestCrossingEventsAPI(unittest.TestCase):
    """Coverage for M1: per-crossing events must be individually ingestible
    and queryable, independent of rollup aggregation."""

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

    def test_events_ingested_and_individually_queryable(self):
        store_id = "test_store_events"
        payload = {
            "batch_size": 2,
            "exported_at": time.time(),
            "events": [
                {
                    "store_id": store_id,
                    "device_id": "test_mac_01",
                    "camera_id": "cam_entrance",
                    "wire_id": "tw_01",
                    "track_id": 42,
                    "direction": "in",
                    "event_timestamp": "2026-09-18 10:00:00"
                },
                {
                    "store_id": store_id,
                    "device_id": "test_mac_01",
                    "camera_id": "cam_entrance",
                    "wire_id": "tw_01",
                    "track_id": 43,
                    "direction": "out",
                    "event_timestamp": "2026-09-18 10:00:05"
                }
            ]
        }
        resp = self.client.post("/api/v1/telemetry/events", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["processed_records"], 2)

        events = self.client.get("/api/v1/events", params={"store_id": store_id})
        self.assertEqual(events.status_code, 200)
        rows = events.json()["events"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["track_id"] for r in rows}, {42, 43})
        self.assertEqual({r["direction"] for r in rows}, {"in", "out"})

        filtered = self.client.get("/api/v1/events", params={"store_id": store_id, "camera_id": "cam_entrance"})
        self.assertEqual(len(filtered.json()["events"]), 2)

        no_match = self.client.get("/api/v1/events", params={"store_id": store_id, "camera_id": "cam_checkout"})
        self.assertEqual(len(no_match.json()["events"]), 0)

class TestAnalyticsAndFilteringAPI(unittest.TestCase):
    """Coverage for M3: camera-level filtering on /api/v1/history, date-range
    filtering, and the new /api/v1/analytics/summary peak/average endpoint."""

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

    def _seed_rollup(self, store_id, camera_id, in_count, received_at):
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
            INSERT INTO telemetry_rollups (
                store_id, device_id, camera_id, timestamp_start, timestamp_end,
                in_count, out_count, current_occupancy, avg_dwell_seconds,
                queue_length, avg_queue_wait_seconds, queue_alert_active, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                store_id, "test_mac_01", camera_id, received_at, received_at,
                in_count, 0, 0, 0.0, 0, 0.0, 0, received_at
            ))
            conn.commit()

    def test_history_filters_by_camera_and_date_range(self):
        store_id = "test_store_m3_history"
        self._seed_rollup(store_id, "cam_a", 10, "2026-09-01 09:00:00")
        self._seed_rollup(store_id, "cam_b", 20, "2026-09-01 10:00:00")
        self._seed_rollup(store_id, "cam_a", 30, "2026-09-05 09:00:00")

        all_rows = self.client.get("/api/v1/history", params={"store_id": store_id}).json()
        self.assertEqual(len(all_rows), 3)

        cam_a_only = self.client.get("/api/v1/history", params={"store_id": store_id, "camera_id": "cam_a"}).json()
        self.assertEqual(len(cam_a_only), 2)
        self.assertTrue(all(r["camera_id"] == "cam_a" for r in cam_a_only))

        ranged = self.client.get("/api/v1/history", params={
            "store_id": store_id, "start_date": "2026-09-01", "end_date": "2026-09-01"
        }).json()
        self.assertEqual(len(ranged), 2)

    def test_live_metrics_filters_by_camera(self):
        store_id = "test_store_m3_live"
        self._seed_rollup(store_id, "cam_a", 10, "2026-09-01 09:00:00")
        self._seed_rollup(store_id, "cam_b", 999, "2026-09-01 09:05:00")

        cam_a_live = self.client.get("/api/v1/live", params={"store_id": store_id, "camera_id": "cam_a"}).json()
        self.assertEqual(cam_a_live["camera_id"], "cam_a")
        self.assertEqual(cam_a_live["total_visitors"], 10)

    def test_analytics_summary_peak_and_average(self):
        store_id = "test_store_m3_summary"
        self._seed_rollup(store_id, "cam_a", 5, "2026-09-01 09:00:00")
        self._seed_rollup(store_id, "cam_a", 15, "2026-09-01 09:30:00")  # same hour bucket -> 20 total
        self._seed_rollup(store_id, "cam_a", 50, "2026-09-01 17:00:00")  # peak hour

        summary = self.client.get("/api/v1/analytics/summary", params={"store_id": store_id}).json()
        self.assertEqual(summary["peak_period"]["hour"], "2026-09-01 17:00:00")
        self.assertEqual(summary["peak_period"]["visitors"], 50)
        # two hour buckets: 20 and 50 -> average 35.0
        self.assertEqual(summary["avg_visitors_per_hour"], 35.0)

    def test_analytics_summary_empty_range_returns_no_peak(self):
        summary = self.client.get("/api/v1/analytics/summary", params={"store_id": "test_store_never_seen"}).json()
        self.assertIsNone(summary["peak_period"])
        self.assertEqual(summary["avg_visitors_per_hour"], 0.0)

if __name__ == "__main__":
    unittest.main()
