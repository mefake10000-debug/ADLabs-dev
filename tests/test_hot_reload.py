import os
import sys
import gc
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import EdgePipeline
from src.storage.local_buffer import LocalBuffer
from src.ingestion.stream_reader import StreamReader
from src.perception.tracker import Track

DB_PATH = "data/storage/test_hot_reload.db"


def camera(cam_id="cam_a", source="data/sample_videos/a.mp4", **extra):
    return {"id": cam_id, "name": cam_id, "source": source, "fps_target": 15, **extra}


TRIPWIRE = {"id": "door", "line": [[0, 100], [200, 100]], "in_direction": "top_to_bottom"}
QUEUE = {"id": "q", "polygon": [[0, 0], [300, 0], [300, 300], [0, 300]], "type": "queue"}


class TestCameraHotReload(unittest.TestCase):

    def setUp(self):
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(DB_PATH + suffix):
                try:
                    os.remove(DB_PATH + suffix)
                except OSError:
                    pass
        self.pipeline = EdgePipeline.__new__(EdgePipeline)
        self.pipeline.store_id = "s"
        self.pipeline.device_id = "d"
        self.pipeline.pipeline_cfg = {}
        self.pipeline.running = False
        self.pipeline.camera_contexts = {}
        self.pipeline.local_buffer = LocalBuffer(db_path=DB_PATH)

    def tearDown(self):
        del self.pipeline
        gc.collect()
        try:
            os.remove(DB_PATH)
        except OSError:
            pass

    def load(self, *cams):
        self.pipeline.cameras_cfg = {"cameras": list(cams)}
        self.pipeline._init_cameras()

    def reload(self, *cams):
        self.pipeline._apply_camera_config_update({"cameras": list(cams)})

    def rollups(self):
        return self.pipeline.local_buffer.get_unexported_rollups(limit=50)

    def test_source_change_restarts_camera_with_fresh_state(self):
        self.load(camera())
        old_ctx = self.pipeline.camera_contexts["cam_a"]
        old_ctx["tracked_ids_today"].update({1, 2, 3})

        self.reload(camera(source="data/sample_videos/b.mp4"))

        new_ctx = self.pipeline.camera_contexts["cam_a"]
        self.assertIsNot(new_ctx, old_ctx)
        self.assertEqual(new_ctx["reader"].source, "data/sample_videos/b.mp4")
        self.assertEqual(new_ctx["tracked_ids_today"], set())
        self.assertIsNot(new_ctx["tracker"], old_ctx["tracker"])
        self.assertEqual(len(self.rollups()), 1)  # the old scene's partial interval was flushed, not lost

    def test_source_change_starts_new_reader_only_when_running(self):
        self.load(camera())
        with patch.object(StreamReader, "start") as start, patch.object(StreamReader, "stop") as stop:
            self.pipeline.running = True
            self.reload(camera(source="data/sample_videos/b.mp4"))
            start.assert_called_once()
            stop.assert_called_once()

    def test_fps_change_also_restarts_reader(self):
        self.load(camera())
        old_reader = self.pipeline.camera_contexts["cam_a"]["reader"]
        self.reload(camera(fps_target=5))
        new_reader = self.pipeline.camera_contexts["cam_a"]["reader"]
        self.assertIsNot(new_reader, old_reader)
        self.assertEqual(new_reader.fps_target, 5)

    def test_unrelated_edit_does_not_rebuild_camera(self):
        self.load(camera(tripwires=[TRIPWIRE]), camera("cam_b"))
        ctx = self.pipeline.camera_contexts["cam_a"]
        reader, tripwire = ctx["reader"], ctx["tripwires"][0]
        tripwire.in_count = 4

        # only cam_b changes; cam_a (same file, same calibration) must be left running untouched
        self.reload(camera(tripwires=[TRIPWIRE]), camera("cam_b", source="data/sample_videos/c.mp4"))

        self.assertIs(self.pipeline.camera_contexts["cam_a"]["reader"], reader)
        self.assertIs(self.pipeline.camera_contexts["cam_a"]["tripwires"][0], tripwire)
        self.assertEqual(tripwire.in_count, 4)

    def test_calibration_change_keeps_reader_and_swaps_analytics(self):
        self.load(camera())
        reader = self.pipeline.camera_contexts["cam_a"]["reader"]

        self.reload(camera(tripwires=[TRIPWIRE], zones=[QUEUE]))

        ctx = self.pipeline.camera_contexts["cam_a"]
        self.assertIs(ctx["reader"], reader)
        self.assertEqual(len(ctx["tripwires"]), 1)
        self.assertEqual(len(ctx["queues"]), 1)   # queue zone became a QueueAnalyzer, not a plain Zone
        self.assertEqual(len(ctx["zones"]), 0)

    def test_calibration_reload_never_produces_negative_deltas(self):
        # Regression: replacing Tripwire objects (counters restart at 0) without resetting
        # last_in_count made the next rollup's delta negative.
        self.load(camera(tripwires=[TRIPWIRE]))
        ctx = self.pipeline.camera_contexts["cam_a"]
        ctx["tripwires"][0].in_count = 7
        self.pipeline._generate_and_save_rollup("cam_a", ctx, time.time())   # baseline: last_in_count = 7
        ctx["tripwires"][0].in_count = 9                                     # 2 more before the reload

        self.reload(camera(tripwires=[TRIPWIRE, {**TRIPWIRE, "id": "door2"}]))
        ctx = self.pipeline.camera_contexts["cam_a"]
        ctx["tripwires"][0].in_count = 1
        self.pipeline._generate_and_save_rollup("cam_a", ctx, time.time())

        counts = [r["in_count"] for r in self.rollups()]
        self.assertTrue(all(c >= 0 for c in counts), counts)
        self.assertEqual(counts, [7, 2, 1])   # nothing lost across the reload: 7, then the flushed 2, then 1

    def test_camera_added_and_removed(self):
        self.load(camera())
        self.reload(camera(), camera("cam_b", source="rtsp://10.0.0.5/s"))
        self.assertEqual(set(self.pipeline.camera_contexts), {"cam_a", "cam_b"})
        self.assertEqual(self.pipeline.camera_contexts["cam_b"]["reader"].source, "rtsp://10.0.0.5/s")

        self.reload(camera("cam_b", source="rtsp://10.0.0.5/s"))
        self.assertEqual(set(self.pipeline.camera_contexts), {"cam_b"})


if __name__ == "__main__":
    unittest.main()
