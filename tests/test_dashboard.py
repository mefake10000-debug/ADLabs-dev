import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DB_PATH = "data/storage/test_cloud_metrics.db"
CONFIG_PATH = "data/storage/test_cameras.yaml"
os.environ.setdefault("SERVER_DB_PATH", DB_PATH)
os.environ.setdefault("CAMERAS_CONFIG", CONFIG_PATH)
os.environ["DASHBOARD_AUTO_REFRESH"] = "0"   # the app's sleep+rerun loop would never let AppTest return

import yaml
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import server.app as server_app

TEST_VIDEO = "data/sample_videos/mall_concourse_01.mp4"
DASHBOARD = os.path.join(os.path.dirname(__file__), "..", "server", "dashboard.py")


def _path(url):
    return "/" + url.split("/", 3)[3]


class TestDashboard(unittest.TestCase):
    """Runs the real Streamlit script against the real FastAPI app (requests routed
    in-process), so this exercises the actual UI -> API -> cameras.yaml path."""

    @classmethod
    def setUpClass(cls):
        server_app.init_db()
        cls.client = TestClient(server_app.app)

    @classmethod
    def tearDownClass(cls):
        for path in (server_app.CONFIG_PATH, server_app.CONFIG_PATH + ".tmp"):
            if os.path.exists(path):
                os.remove(path)

    def setUp(self):
        self.config_path = server_app.CONFIG_PATH
        with open(self.config_path, "w") as f:
            yaml.safe_dump({"cameras": [
                {"id": "cam_a", "name": "Cam A", "source": "data/sample_videos/entrance_sample.mp4", "fps_target": 15},
                {"id": "cam_b", "name": "Cam B", "source": "rtsp://10.0.0.5/stream", "fps_target": 10},
            ]}, f, sort_keys=False)
        self.store = f"dash_store_{time.time_ns()}"
        self.patches = [
            patch("requests.get", lambda url, params=None, timeout=None, **kw: self.client.get(_path(url), params=params)),
            patch("requests.post", lambda url, json=None, timeout=None, **kw: self.client.post(_path(url), json=json)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def config(self):
        with open(self.config_path) as f:
            return {c["id"]: c for c in yaml.safe_load(f)["cameras"]}

    def seed(self, camera_id, in_count, out_count=0):
        resp = self.client.post("/api/v1/telemetry", json={
            "batch_size": 1, "exported_at": time.time(),
            "rollups": [{
                "store_id": self.store, "device_id": "d", "camera_id": camera_id,
                "timestamp_start": "2026-09-19 10:00:00", "timestamp_end": "2026-09-19 10:00:10",
                "in_count": in_count, "out_count": out_count, "current_occupancy": 3,
                "avg_dwell_seconds": 20.0, "queue_length": 2, "avg_queue_wait_seconds": 30.0,
                "queue_alert_active": 0,
            }],
        })
        self.assertEqual(resp.status_code, 200)

    def run_app(self):
        at = AppTest.from_file(DASHBOARD, default_timeout=120)
        at.run()
        at.sidebar.text_input[0].set_value(self.store).run()
        return at

    @staticmethod
    def metric(at, label_fragment):
        matches = [m for m in at.metric if label_fragment in m.label]
        assert matches, f"no metric containing {label_fragment!r}; have {[m.label for m in at.metric]}"
        return matches[0].value

    @staticmethod
    def button(at, label):
        return next(b for b in at.button if b.label == label)

    def test_renders_with_camera_filter_and_historical_kpis(self):
        self.seed("cam_a", 5)
        self.seed("cam_b", 7)
        at = self.run_app()
        self.assertFalse(at.exception, at.exception)

        self.assertEqual(at.sidebar.selectbox(key="camera_filter").options, ["All cameras", "cam_a", "cam_b"])
        self.assertEqual(self.metric(at, "Visitors in Range"), "12")
        self.assertNotEqual(self.metric(at, "Peak Traffic Hour"), "—")

        at.sidebar.selectbox(key="camera_filter").select("cam_b").run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.metric(at, "Visitors in Range"), "7")

    def test_empty_store_shows_placeholders_not_errors(self):
        at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.metric(at, "Peak Traffic Hour"), "—")
        self.assertEqual(self.metric(at, "Visitors in Range"), "0")

    def test_switching_source_from_the_ui_updates_only_that_camera(self):
        at = self.run_app()
        at.selectbox(key="setup_cam").select("cam_a").run()
        at.radio(key="src_mode_cam_a").set_value("Video file")
        at.selectbox(key="src_file_cam_a").select(TEST_VIDEO)
        self.button(at, "Apply source").click().run()

        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.config()["cam_a"]["source"], TEST_VIDEO)
        self.assertEqual(self.config()["cam_b"]["source"], "rtsp://10.0.0.5/stream")

    def test_switching_to_rtsp_and_rejecting_a_bad_url(self):
        at = self.run_app()
        at.radio(key="src_mode_cam_a").set_value("RTSP / stream URL")
        at.text_input(key="src_url_cam_a").set_value("rtsp://admin:pw@192.168.1.9:554/ch1")
        self.button(at, "Apply source").click().run()
        self.assertEqual(self.config()["cam_a"]["source"], "rtsp://admin:pw@192.168.1.9:554/ch1")

        at.text_input(key="src_url_cam_a").set_value("not-a-url")
        self.button(at, "Apply source").click().run()
        self.assertTrue(any("Could not update source" in e.value for e in at.error))
        self.assertEqual(self.config()["cam_a"]["source"], "rtsp://admin:pw@192.168.1.9:554/ch1")

    def test_adding_a_queue_zone_from_the_ui(self):
        at = self.run_app()
        at.selectbox(key="setup_cam").select("cam_a").run()
        at.text_input(key="zone_id_cam_a").set_value("checkout_queue")
        at.selectbox(key="zone_type_cam_a").select("queue")
        at.text_input(key="zone_poly_cam_a").set_value("100,200 400,200 400,500 100,500")
        self.button(at, "Add zone").click().run()

        self.assertFalse(at.exception, at.exception)
        zone = self.config()["cam_a"]["zones"][0]
        self.assertEqual((zone["id"], zone["type"]), ("checkout_queue", "queue"))
        self.assertEqual(len(zone["polygon"]), 4)
        self.assertEqual(self.config()["cam_a"]["source"], "data/sample_videos/entrance_sample.mp4")

    def test_bad_polygon_is_rejected_client_side(self):
        at = self.run_app()
        at.text_input(key="zone_poly_cam_a").set_value("100,200 400,200")
        self.button(at, "Add zone").click().run()
        self.assertTrue(any("Invalid polygon" in e.value for e in at.error))
        self.assertNotIn("zones", self.config()["cam_a"])

    def test_adding_then_removing_a_tripwire(self):
        at = self.run_app()
        at.text_input(key="tw_id_cam_a").set_value("door")
        at.number_input(key="tw_x1_cam_a").set_value(600.0)
        at.number_input(key="tw_y1_cam_a").set_value(580.0)
        at.number_input(key="tw_x2_cam_a").set_value(1050.0)
        at.number_input(key="tw_y2_cam_a").set_value(580.0)
        at.selectbox(key="tw_dir_cam_a").select("bottom_to_top")
        self.button(at, "Add tripwire").click().run()
        tw = self.config()["cam_a"]["tripwires"][0]
        self.assertEqual((tw["id"], tw["in_direction"]), ("door", "bottom_to_top"))

        at.multiselect(key="remove_cam_a").set_value(["door"])
        self.button(at, "Remove selected").click().run()
        self.assertEqual(self.config()["cam_a"]["tripwires"], [])


if __name__ == "__main__":
    unittest.main()
