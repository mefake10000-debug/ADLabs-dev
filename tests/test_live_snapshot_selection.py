import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

import server.app as server_app


class LiveSnapshotSelectionTests(unittest.TestCase):
    def test_live_snapshot_is_not_applied_to_another_store(self):
        snapshot = {"store_id": "store_mumbai_001", "people_now": 6}
        scope = getattr(server_app, "_snapshot_for_store", None)

        self.assertTrue(callable(scope), "live snapshot store scoping helper is missing")
        self.assertIsNone(scope(snapshot, "test_store"))
        self.assertIs(scope(snapshot, "store_mumbai_001"), snapshot)
        legacy_default_snapshot = {"people_now": 3}
        self.assertIs(scope(legacy_default_snapshot, "store_mumbai_001"), legacy_default_snapshot)
        self.assertIsNone(scope(legacy_default_snapshot, "test_store"))

    def test_store_snapshot_selects_the_freshest_camera_file(self):
        with tempfile.TemporaryDirectory() as live_dir:
            now = time.time()
            for camera_id, written_at in (
                ("cam_checkout_01", now - 45),
                ("cam_entrance_01", now),
            ):
                payload = {
                    "camera_id": camera_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(written_at)),
                }
                path = os.path.join(live_dir, f"{camera_id}.json")
                with open(path, "w") as stream:
                    json.dump(payload, stream)
                os.utime(path, (written_at, written_at))

            with patch("server.app._live_dir", return_value=live_dir):
                snapshot = server_app._read_live_snapshot()

        self.assertEqual(snapshot["camera_id"], "cam_entrance_01")
        self.assertFalse(snapshot.get("_stale", False))

    def test_fresh_worker_utc_timestamp_is_not_marked_stale(self):
        with tempfile.TemporaryDirectory() as live_dir:
            written_at = time.time()
            path = os.path.join(live_dir, "cam_entrance_01.json")
            with open(path, "w") as stream:
                json.dump({
                    "camera_id": "cam_entrance_01",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(written_at)),
                }, stream)
            os.utime(path, (written_at, written_at))

            with patch("server.app._live_dir", return_value=live_dir):
                snapshot = server_app._read_live_snapshot("cam_entrance_01")

        self.assertFalse(snapshot.get("_stale", False))


if __name__ == "__main__":
    unittest.main()
