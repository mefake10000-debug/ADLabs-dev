import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DB_PATH = "data/storage/test_cloud_metrics.db"
CONFIG_PATH = "data/storage/test_cameras.yaml"
os.environ["SERVER_DB_PATH"] = DB_PATH
# The config endpoints write to disk -- never let tests touch the real configs/cameras.yaml
os.environ["CAMERAS_CONFIG"] = CONFIG_PATH

if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
    except OSError:
        pass

import yaml
from fastapi.testclient import TestClient
import server.app as server_app
from server.app import app, init_db

TEST_VIDEO = "data/sample_videos/mall_concourse_01.mp4"

class TestLiveMetricsAPI(unittest.TestCase):
    """Regression coverage for M0: /api/v1/live used to hardcode queue_length/
    avg_queue_wait_seconds/queue_alert_active to zero instead of reading them
    from the latest seeded telemetry rollup."""

    @classmethod
    def setUpClass(cls):
        init_db()   # tables must exist even if an earlier test module removed the file
        cls.client = TestClient(app)

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
        init_db()   # tables must exist even if an earlier test module removed the file
        cls.client = TestClient(app)

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
        init_db()   # tables must exist even if an earlier test module removed the file
        cls.client = TestClient(app)

    def _seed_rollup(self, store_id, camera_id, in_count, received_at, occupancy=0,
                     queue_length=0, avg_queue_wait_seconds=0.0, queue_alert_active=0):
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
                in_count, 0, occupancy, 0.0, queue_length, avg_queue_wait_seconds, queue_alert_active, received_at
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

    def test_live_metrics_aggregates_across_cameras_not_just_last_sync(self):
        # Regression: /api/v1/live used to read only the single most recent rollup row
        # store-wide, so with >1 camera it reported whichever camera happened to sync last,
        # not a true store-wide figure.
        store_id = "test_store_multicam"
        # cam_a syncs first with occupancy 5 and a queue alert; cam_b syncs LATER (higher id)
        # with occupancy 3 and no queue. A single-latest-row read would see only cam_b's numbers.
        self._seed_rollup(store_id, "cam_a", 1, "2026-09-01 09:00:00", occupancy=5,
                          queue_length=2, avg_queue_wait_seconds=40.0, queue_alert_active=1)
        self._seed_rollup(store_id, "cam_b", 1, "2026-09-01 09:00:05", occupancy=3,
                          queue_length=0, avg_queue_wait_seconds=0.0, queue_alert_active=0)

        data = self.client.get("/api/v1/live", params={"store_id": store_id}).json()
        self.assertEqual(data["net_occupancy"], 8)          # 5 + 3, not just cam_b's 3
        self.assertEqual(data["queue_length"], 2)            # summed, not dropped
        self.assertTrue(data["queue_alert_active"])          # true if ANY camera has an alert

        # A later rollup from cam_a alone must update cam_a's contribution without losing cam_b's
        self._seed_rollup(store_id, "cam_a", 1, "2026-09-01 09:00:10", occupancy=7,
                          queue_length=0, avg_queue_wait_seconds=0.0, queue_alert_active=0)
        data2 = self.client.get("/api/v1/live", params={"store_id": store_id}).json()
        self.assertEqual(data2["net_occupancy"], 10)         # 7 (cam_a's newer row) + 3 (cam_b's latest)
        self.assertFalse(data2["queue_alert_active"])        # cam_a's alert cleared, cam_b never had one

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

class TestCameraConfigAPI(unittest.TestCase):
    """Front-end camera source switching and calibration must edit one camera
    in place, never clobber the rest of cameras.yaml, and reject bad input."""

    @classmethod
    def setUpClass(cls):
        init_db()   # tables must exist even if an earlier test module removed the file
        cls.client = TestClient(app)

    def setUp(self):
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump({"cameras": [
                {"id": "cam_a", "name": "Cam A", "source": "data/sample_videos/entrance_sample.mp4", "fps_target": 15,
                 "tripwires": [{"id": "tw1", "line": [[0, 10], [100, 10]], "in_direction": "top_to_bottom"}]},
                {"id": "cam_b", "name": "Cam B", "source": "rtsp://10.0.0.5/stream", "fps_target": 10},
            ]}, f, sort_keys=False)

    @classmethod
    def tearDownClass(cls):
        for path in (CONFIG_PATH, CONFIG_PATH + ".tmp"):
            if os.path.exists(path):
                os.remove(path)

    def _config(self):
        with open(CONFIG_PATH) as f:
            return {c["id"]: c for c in yaml.safe_load(f)["cameras"]}

    def test_lists_selectable_videos(self):
        videos = self.client.get("/api/v1/config/sources").json()["videos"]
        self.assertIn(TEST_VIDEO, videos)
        self.assertTrue(all(v.startswith("data/sample_videos/") for v in videos))

    def test_switch_source_changes_only_that_camera_and_keeps_calibration(self):
        resp = self.client.post("/api/v1/config/cameras/cam_a/source", json={"source": TEST_VIDEO, "fps_target": 12})
        self.assertEqual(resp.status_code, 200)
        cfg = self._config()
        self.assertEqual(cfg["cam_a"]["source"], TEST_VIDEO)
        self.assertEqual(cfg["cam_a"]["fps_target"], 12)
        self.assertEqual(cfg["cam_a"]["tripwires"][0]["id"], "tw1")   # calibration preserved
        self.assertEqual(cfg["cam_b"]["source"], "rtsp://10.0.0.5/stream")  # other camera untouched

    def test_rtsp_source_accepted(self):
        resp = self.client.post("/api/v1/config/cameras/cam_a/source", json={"source": "rtsp://admin:pw@192.168.1.10:554/ch1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._config()["cam_a"]["source"], "rtsp://admin:pw@192.168.1.10:554/ch1")

    def test_bad_sources_rejected_and_config_unchanged(self):
        before = self._config()
        bad_sources = [
            "",                                            # empty
            "data/sample_videos/does_not_exist.mp4",       # missing file
            "data/sample_videos/../../etc/passwd",         # path traversal
            "/etc/passwd",                                 # absolute path
            "data/sample_videos/SOURCES.md",               # not a video
            "configs/pipeline.yaml",                       # outside the video dir
        ]
        for source in bad_sources:
            resp = self.client.post("/api/v1/config/cameras/cam_a/source", json={"source": source})
            self.assertEqual(resp.status_code, 400, f"{source!r} should be rejected")
        self.assertEqual(self._config(), before)

    def test_unknown_camera_is_404(self):
        resp = self.client.post("/api/v1/config/cameras/nope/source", json={"source": TEST_VIDEO})
        self.assertEqual(resp.status_code, 404)

    def test_calibration_saves_queue_zone_and_preserves_source(self):
        body = {
            "tripwires": [{"id": "door", "line": [[600, 580], [1050, 580]], "in_direction": "bottom_to_top"}],
            "zones": [{"id": "q1", "polygon": [[100, 200], [400, 200], [400, 500]], "type": "queue",
                       "max_comfortable_queue": 3, "congestion_threshold_seconds": 90}],
        }
        resp = self.client.post("/api/v1/config/cameras/cam_a/calibration", json=body)
        self.assertEqual(resp.status_code, 200)
        cam = self._config()["cam_a"]
        self.assertEqual(cam["source"], "data/sample_videos/entrance_sample.mp4")
        self.assertEqual(cam["tripwires"][0]["id"], "door")
        self.assertEqual(cam["zones"][0]["type"], "queue")
        self.assertEqual(cam["zones"][0]["max_comfortable_queue"], 3)
        self.assertEqual(self._config()["cam_b"]["fps_target"], 10)

    def test_calibration_accepts_a_staff_zone(self):
        resp = self.client.post("/api/v1/config/cameras/cam_a/calibration", json={
            "zones": [{"id": "counter", "polygon": [[0, 0], [200, 0], [200, 400]], "type": "staff"}]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._config()["cam_a"]["zones"][0]["type"], "staff")

    def test_calibration_omitting_a_key_leaves_it_alone(self):
        self.client.post("/api/v1/config/cameras/cam_a/calibration",
                         json={"zones": [{"id": "z", "polygon": [[0, 0], [10, 0], [10, 10]]}]})
        cam = self._config()["cam_a"]
        self.assertEqual(cam["tripwires"][0]["id"], "tw1")
        self.assertEqual(cam["zones"][0]["id"], "z")

    def test_invalid_calibration_rejected(self):
        for body in (
            {"zones": [{"id": "z", "polygon": [[0, 0], [10, 0]]}]},                       # 2 points
            {"zones": [{"id": "z", "polygon": [[0, 0], [10, 0], [5, 5]], "type": "x"}]},  # bad type
            {"tripwires": [{"id": "t", "line": [[0, 0]]}]},                                # 1 point
            {"tripwires": [{"id": "t", "line": [[0, 0], [1, 1]], "in_direction": "left"}]},
        ):
            resp = self.client.post("/api/v1/config/cameras/cam_a/calibration", json=body)
            self.assertEqual(resp.status_code, 422, body)
        self.assertEqual(self._config()["cam_a"]["tripwires"][0]["id"], "tw1")

    def test_heatmap_endpoint_serves_the_edge_written_image(self):
        path = os.path.join(os.path.dirname(DB_PATH), "heatmaps", "test_heatmap_cam.jpg")
        self.assertEqual(self.client.get("/api/v1/heatmap/test_heatmap_cam").status_code, 404)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"\xff\xd8fake-jpeg")
        try:
            resp = self.client.get("/api/v1/heatmap/test_heatmap_cam")
            self.assertEqual((resp.status_code, resp.headers["content-type"], resp.content),
                             (200, "image/jpeg", b"\xff\xd8fake-jpeg"))
        finally:
            os.remove(path)

    def test_rtsp_credentials_are_redacted_in_every_response(self):
        creds_source = "rtsp://admin:sup3rSecret@192.168.1.50:554/Streaming/Channels/102"
        self.client.post("/api/v1/config/cameras/cam_a/source", json={"source": creds_source})

        get_resp = self.client.get("/api/v1/config/cameras").json()
        cam_a = next(c for c in get_resp["cameras"] if c["id"] == "cam_a")
        self.assertNotIn("sup3rSecret", cam_a["source"])
        self.assertIn("****:****@192.168.1.50", cam_a["source"])

        # Never touch the actual file on disk -- only API responses are redacted
        self.assertIn("sup3rSecret", self._config()["cam_a"]["source"])

        # The POST response itself must also be redacted, not just the later GET
        post_resp = self.client.post("/api/v1/config/cameras/cam_a/source", json={"source": creds_source}).json()
        self.assertNotIn("sup3rSecret", post_resp["camera"]["source"])

    def test_calibration_studio_closes_zones_without_relying_on_a_native_dblclick(self):
        """Regression guard for a bug where a queue/dwell zone could only be finished by a native
        browser dblclick event. That event depends on the OS/browser/input-device double-click
        threshold, which trackpads, remote-desktop/VM input forwarding, and some mice don't hit
        reliably -- when it silently doesn't fire, the clicked points never become a real polygon:
        never in the shapes list, never saved, never reaches the edge. A tripwire needs only two
        ordinary clicks (no double-click gesture at all), which is why it always worked while a
        zone sometimes didn't for the exact same "click on the frame" interaction. There's an
        explicit, reliable "Close Shape" button now; this only checks it's actually wired into
        the page (a real click-driven repro of the bug lives outside this suite, via Playwright,
        since this project intentionally keeps a browser automation dependency out of CI)."""
        html = self.client.get("/").text
        self.assertIn('onclick="finishPolygon()"', html)
        self.assertIn("Close Shape", html)
        self.assertIn("function finishPolygon()", html)
        # The old close path (double-click) must still work for anyone whose pointer supports it.
        self.assertIn("canvas.ondblclick = () => finishPolygon();", html)


class TestApiKeyAuth(unittest.TestCase):
    """State-changing endpoints only: GET reads stay open even when a key is configured."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_no_key_configured_means_no_auth_required(self):
        # server_app.API_KEY is None in every other test in this file (env var never set) --
        # this is just an explicit assertion that today's zero-config behaviour is unchanged.
        resp = self.client.post("/api/v1/metrics/reset")
        self.assertEqual(resp.status_code, 200)

    def test_post_rejected_without_or_with_wrong_key_when_configured(self):
        with patch.object(server_app, "API_KEY", "correct-key"):
            no_key = self.client.post("/api/v1/metrics/reset")
            self.assertEqual(no_key.status_code, 401)

            wrong_key = self.client.post("/api/v1/metrics/reset", headers={"X-API-Key": "wrong"})
            self.assertEqual(wrong_key.status_code, 401)

            right_key = self.client.post("/api/v1/metrics/reset", headers={"X-API-Key": "correct-key"})
            self.assertEqual(right_key.status_code, 200)

    def test_get_endpoints_stay_open_even_when_a_key_is_configured(self):
        with patch.object(server_app, "API_KEY", "correct-key"):
            resp = self.client.get("/api/v1/live", params={"store_id": "any"})
            self.assertEqual(resp.status_code, 200)


def tearDownModule():
    # Removing the DB per test class broke every later class on Linux (Windows just failed to delete an open file).
    for path in (DB_PATH, CONFIG_PATH, CONFIG_PATH + ".tmp"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

if __name__ == "__main__":
    unittest.main()
