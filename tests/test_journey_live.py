"""Service-journey / dead-zone block for /api/v1/live."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.journey import (
    build_journey_block,
    clear_journey_config_cache,
    load_journey_config,
)


class TestJourneyBuilder(unittest.TestCase):
    def setUp(self):
        clear_journey_config_cache()

    def tearDown(self):
        clear_journey_config_cache()

    def test_config_loads_six_buffet_stages(self):
        cfg = load_journey_config()
        self.assertEqual(cfg.get("metaphor"), "buffet")
        self.assertGreaterEqual(len(cfg.get("stages") or []), 6)

    def test_missing_when_no_zones(self):
        block = build_journey_block([])
        self.assertEqual(block["summary"]["missing"], len(block["stages"]))
        self.assertEqual(block["summary"]["calibrated"], 0)
        for s in block["stages"]:
            self.assertEqual(s["status"], "missing")
            self.assertFalse(s["calibrated"])
            self.assertEqual(s["visits"], 0)
            self.assertEqual(s["occupancy"], 0)

    def test_dead_zone_when_marked_but_cold(self):
        zones = [
            {"id": "z1", "name": "Entrance Welcome", "occupancy": 0, "visits": 0, "avg_dwell_seconds": 0},
            {"id": "z2", "name": "Hero Focal Wall", "occupancy": 0, "total_visits": 0, "avg_dwell_seconds": 0},
        ]
        block = build_journey_block(zones)
        by_id = {s["id"]: s for s in block["stages"]}
        self.assertTrue(by_id["welcome_drink"]["calibrated"])
        self.assertTrue(by_id["welcome_drink"]["dead_zone"])
        self.assertEqual(by_id["welcome_drink"]["status"], "dead_zone")
        self.assertTrue(by_id["main"]["calibrated"])
        self.assertTrue(by_id["main"]["dead_zone"])
        self.assertGreaterEqual(block["summary"]["dead_zone"], 2)

    def test_live_when_visits_or_occupancy(self):
        zones = [
            {"id": "z1", "name": "Front aisle starter", "occupancy": 2, "visits": 5, "avg_dwell_seconds": 12.0},
        ]
        block = build_journey_block(zones)
        starter = next(s for s in block["stages"] if s["id"] == "starter")
        self.assertEqual(starter["status"], "live")
        self.assertFalse(starter["dead_zone"])
        self.assertEqual(starter["occupancy"], 2)
        self.assertEqual(starter["visits"], 5)

    def test_explicit_journey_stage_tag(self):
        zones = [
            {"id": "custom", "name": "Zone A", "journey_stage": "dessert", "occupancy": 1, "visits": 1},
        ]
        block = build_journey_block(zones)
        dessert = next(s for s in block["stages"] if s["id"] == "dessert")
        self.assertTrue(dessert["calibrated"])
        self.assertEqual(dessert["status"], "live")
        self.assertIn("custom", dessert["zone_ids"])


class TestLiveApiJourney(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmpdir.name, "t.db")
        cls.config_path = os.path.join(cls._tmpdir.name, "cameras.yaml")
        Path(cls.config_path).write_text("cameras: []\n", encoding="utf-8")
        os.environ["SERVER_DB_PATH"] = cls.db_path
        os.environ["CAMERAS_CONFIG"] = cls.config_path
        import server.app as server_app
        from fastapi.testclient import TestClient
        from server.app import app, init_db

        cls.server_app = server_app
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_live_includes_journey_with_zero_defaults(self):
        # The local Docker worker may be publishing the default store's real
        # journey snapshot while the suite is running. This case verifies the
        # no-source empty state, so isolate it from the developer's live feed.
        with patch.object(self.server_app, "_read_live_snapshot", return_value=None):
            live = self.client.get("/api/v1/live").json()
        self.assertIn("journey", live)
        j = live["journey"]
        self.assertEqual(j.get("metaphor"), "buffet")
        self.assertIsInstance(j.get("stages"), list)
        self.assertGreaterEqual(len(j["stages"]), 6)
        self.assertIn("summary", j)

    def test_live_journey_from_snapshot_zones(self):
        # Write into the live dir the already-imported app module actually reads.
        live_dir = self.server_app._live_dir()
        os.makedirs(live_dir, exist_ok=True)
        journey = build_journey_block([
            {"id": "ent", "name": "Welcome drink bar", "occupancy": 0, "visits": 0},
            {"id": "hero", "name": "Main hero", "occupancy": 3, "visits": 8, "avg_dwell_seconds": 20},
        ])
        store = {
            "store_id": "store_mumbai_001",
            "people_now": 3,
            "net_occupancy": 3,
            "total_visitors": 10,
            "total_exits": 7,
            "queue_length": 0,
            "avg_dwell_seconds": 20.0,
            "timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "cameras": ["cam_entrance_01"],
            "source": "live_snapshot",
            "zones": [
                {"id": "ent", "name": "Welcome drink bar", "occupancy": 0, "visits": 0, "avg_dwell_seconds": 0},
                {"id": "hero", "name": "Main hero", "occupancy": 3, "visits": 8, "avg_dwell_seconds": 20},
            ],
            "journey": journey,
        }
        with open(os.path.join(live_dir, "store.json"), "w") as f:
            json.dump(store, f)
        with open(os.path.join(live_dir, "cam_entrance_01.json"), "w") as f:
            json.dump({**store, "camera_id": "cam_entrance_01"}, f)

        live = self.client.get("/api/v1/live").json()
        self.assertEqual(live.get("source"), "live_snapshot")
        self.assertIn("journey", live)
        by_id = {s["id"]: s for s in live["journey"]["stages"]}
        self.assertEqual(by_id["welcome_drink"]["status"], "dead_zone")
        self.assertEqual(by_id["main"]["status"], "live")
        self.assertEqual(by_id["main"]["occupancy"], 3)


if __name__ == "__main__":
    unittest.main()
