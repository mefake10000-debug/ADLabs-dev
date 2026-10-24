import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DB_PATH = "data/storage/test_cloud_metrics.db"
CONFIG_PATH = "data/storage/test_cameras.yaml"
# Always override, never setdefault: the dashboard container sets CAMERAS_CONFIG to the real
# configs/cameras.yaml, which these tests would otherwise overwrite and then delete.
os.environ["SERVER_DB_PATH"] = DB_PATH
os.environ["CAMERAS_CONFIG"] = CONFIG_PATH
os.environ["DASHBOARD_AUTO_REFRESH"] = "0"   # the app's sleep+rerun loop would never let AppTest return

import yaml
from PIL import Image
from fastapi.testclient import TestClient
try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("streamlit"):
        raise unittest.SkipTest("Streamlit AppTest requires the optional dashboard dependency")
    raise

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
        from tempfile import TemporaryDirectory

        server_app.init_db()
        cls.client = TestClient(server_app.app)
        cls.fixture_dir = TemporaryDirectory(prefix="edgesight-dashboard-plumbing-")
        cls.video_patch = patch.object(server_app, "VIDEO_DIR", cls.fixture_dir.name)
        cls.video_patch.start()
        global TEST_VIDEO, ENTRANCE_VIDEO
        TEST_VIDEO = os.path.join(cls.fixture_dir.name, "mall_concourse_01.mp4")
        ENTRANCE_VIDEO = os.path.join(cls.fixture_dir.name, "entrance_sample.mp4")
        for fixture_path in (TEST_VIDEO, ENTRANCE_VIDEO):
            with open(fixture_path, "wb") as fixture:
                fixture.write(b"")

    @classmethod
    def tearDownClass(cls):
        cls.video_patch.stop()
        cls.fixture_dir.cleanup()
        for path in (server_app.CONFIG_PATH, server_app.CONFIG_PATH + ".tmp"):
            if os.path.exists(path):
                os.remove(path)

    def setUp(self):
        self.config_path = server_app.CONFIG_PATH
        with open(self.config_path, "w") as f:
            yaml.safe_dump({"cameras": [
                {"id": "cam_a", "name": "Cam A", "source": ENTRANCE_VIDEO, "fps_target": 15},
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

    def test_heatmap_tab_shows_each_cameras_heatmap_or_says_why_not(self):
        path = os.path.join(os.path.dirname(DB_PATH), "heatmaps", "cam_a.jpg")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.new("RGB", (64, 36), (200, 40, 40)).save(path, "JPEG")  # cam_a has a heatmap, cam_b doesn't
        self.addCleanup(os.remove, path)
        at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        messages = [i.value for i in at.info]
        self.assertTrue(any("No heatmap yet for cam_b" in m for m in messages), messages)
        self.assertFalse(any("No heatmap yet for cam_a" in m for m in messages), messages)

    def test_switching_source_from_the_ui_updates_only_that_camera(self):
        at = self.run_app()
        at.selectbox(key="setup_cam").select("cam_a").run()
        at.radio(key="src_mode_cam_a").set_value("Video file")
        at.selectbox(key="src_file_cam_a").select(TEST_VIDEO)
        self.button(at, "Apply source").click().run()

        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.config()["cam_a"]["source"], TEST_VIDEO)
        self.assertEqual(self.config()["cam_b"]["source"], "rtsp://10.0.0.5/stream")
        # Live Vision's "Current source" must show the new video at once, not after a hard refresh
        self.assertIn(TEST_VIDEO, [c.value for c in at.code])
        self.assertTrue(any("Source updated" in m.value for m in at.success))

    def test_camera_whose_video_was_deleted_can_be_switched_to_another_file(self):
        # Regression: a deleted/renamed local file used to flip the form into URL mode with the
        # missing path pre-filled, so choosing a file and pressing Apply re-submitted the missing path.
        with open(self.config_path) as f:
            cfg = yaml.safe_load(f)
        cfg["cameras"][0]["source"] = "data/sample_videos/clip_that_was_deleted.mp4"
        with open(self.config_path, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)

        at = self.run_app()
        at.selectbox(key="setup_cam").select("cam_a").run()
        self.assertEqual(at.radio(key="src_mode_cam_a").value, "Video file")
        self.assertTrue(any("no longer exists" in w.value for w in at.warning))

        at.selectbox(key="src_file_cam_a").select(TEST_VIDEO)
        self.button(at, "Apply source").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.config()["cam_a"]["source"], TEST_VIDEO)

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

    def test_camera_setup_has_no_calibration_write_widgets(self):
        """Regression test: tripwires/zones must only ever be created or removed through the
        Calibration Studio now, never through this dashboard. Two clients independently able to
        write the same calibration file is exactly what caused the stale-snapshot bugs this
        replaced (dashboard vs. Studio each silently reverting the other's concurrent write)."""
        at = self.run_app()
        at.selectbox(key="setup_cam").select("cam_a").run()
        self.assertFalse(at.exception, at.exception)

        button_labels = {b.label for b in at.button}
        self.assertNotIn("Add zone", button_labels)
        self.assertNotIn("Add tripwire", button_labels)
        self.assertNotIn("Remove selected", button_labels)
        # The "Apply source" button is the one remaining camera-setup mutation, and it's fine to
        # keep here: it doesn't touch tripwires/zones, so there's no second writer to race with.
        self.assertIn("Apply source", button_labels)

    def test_camera_setup_shows_existing_calibration_read_only_and_links_to_studio(self):
        with open(self.config_path) as f:
            cfg = yaml.safe_load(f)
        cfg["cameras"][0]["tripwires"] = [{"id": "door", "name": "door", "line": [[0, 0], [10, 10]], "in_direction": "bottom_to_top"}]
        cfg["cameras"][0]["zones"] = [{"id": "checkout_queue", "name": "checkout_queue",
                                        "polygon": [[100, 200], [400, 200], [400, 500], [100, 500]], "type": "queue"}]
        with open(self.config_path, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)

        at = self.run_app()
        at.selectbox(key="setup_cam").select("cam_a").run()
        self.assertFalse(at.exception, at.exception)

        # Read-only tables render the calibration that's actually on disk, with no way to edit it here.
        dataframe_values = [df.value.to_dict("records") for df in at.dataframe]
        self.assertTrue(any(row.get("id") == "door" for rows in dataframe_values for row in rows))
        self.assertTrue(any(row.get("id") == "checkout_queue" for rows in dataframe_values for row in rows))

        # Config on disk is untouched by merely viewing it.
        self.assertEqual(self.config()["cam_a"]["tripwires"][0]["id"], "door")
        self.assertEqual(self.config()["cam_a"]["zones"][0]["id"], "checkout_queue")


if __name__ == "__main__":
    unittest.main()
