"""NFC tap stub + retail_roles (floor) maturity on /api/v1/live — no synthetic taps."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DB_PATH = "data/storage/test_nfc_cloud_metrics.db"
CONFIG_PATH = "data/storage/test_nfc_cameras.yaml"
os.environ["SERVER_DB_PATH"] = DB_PATH
os.environ["CAMERAS_CONFIG"] = CONFIG_PATH

if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
    except OSError:
        pass

from fastapi.testclient import TestClient
from server.app import app, init_db
from server import nfc_store


class TestNfcIndustryApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        nfc_store.clear_session()

    def test_live_nfc_empty_needs_hardware(self):
        live = self.client.get("/api/v1/live")
        self.assertEqual(live.status_code, 200)
        data = live.json()
        self.assertIn("nfc", data)
        self.assertEqual(data["nfc"]["status"], "NEEDS-HARDWARE")
        self.assertEqual(data["nfc"]["recent_taps"], [])
        self.assertEqual(data["nfc"]["tap_count_session"], 0)
        self.assertIn("connect_hint", data["nfc"])
        self.assertIn("retail_roles", data)
        self.assertEqual(data["retail_roles"]["schema"], "floor_roles_v1")
        self.assertEqual(data["retail_roles"]["entrance"]["stop_rate"], "FUTURE")
        self.assertEqual(data["retail_roles"]["shelf"]["shelf_qa_moondream"], "FUTURE")
        # Deprecated industry alias still present for older clients.
        self.assertIn("industry", data)
        self.assertTrue(data["industry"].get("_deprecated"))
        self.assertEqual(data["industry"]["fashion"]["nfc_taps"], "NEEDS-HARDWARE")

    def test_post_tap_then_live_lists_it(self):
        resp = self.client.post(
            "/api/v1/nfc/tap",
            json={
                "product_id": "SKU-RED-TEE-42",
                "zone": "fitting_wall_a",
                "zone_id": "z_fit_a",
                "camera_id": "cam_entrance_01",
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["tap"]["product_id"], "SKU-RED-TEE-42")
        self.assertEqual(body["nfc"]["status"], "LIVE")
        self.assertEqual(body["nfc"]["tap_count_session"], 1)

        live = self.client.get("/api/v1/live").json()
        self.assertEqual(live["nfc"]["status"], "LIVE")
        self.assertEqual(live["nfc"]["tap_count_session"], 1)
        self.assertEqual(len(live["nfc"]["recent_taps"]), 1)
        self.assertEqual(live["nfc"]["recent_taps"][0]["product_id"], "SKU-RED-TEE-42")
        self.assertEqual(live["nfc"]["recent_taps"][0]["zone"], "fitting_wall_a")
        self.assertEqual(live["retail_roles"]["shelf"]["nfc_optional"], "LIVE")
        self.assertEqual(live["industry"]["fashion"]["nfc_taps"], "LIVE")

    def test_empty_product_id_rejected(self):
        resp = self.client.post("/api/v1/nfc/tap", json={"product_id": "  "})
        self.assertIn(resp.status_code, (422, 400))

    def test_get_nfc_taps_endpoint(self):
        empty = self.client.get("/api/v1/nfc/taps").json()
        self.assertEqual(empty["recent_taps"], [])
        self.client.post("/api/v1/nfc/tap", json={"product_id": "P1"})
        filled = self.client.get("/api/v1/nfc/taps").json()
        self.assertEqual(filled["tap_count_session"], 1)


if __name__ == "__main__":
    unittest.main()
